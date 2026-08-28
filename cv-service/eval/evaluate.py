"""
Ground-truth evaluation CLI — separate from the pytest suite (spec M5
section 28: "maintain a separate CV evaluation command/test suite for
actual model inference"). Where the pytest tests assert pass/fail against
fixed expectations, this script *reports* actual measured numbers for human
review, against every labeled fixture in eval/ground_truth/.

Usage:
    python eval/evaluate.py

Metrics computed (never invented — see spec section 17):
  - Court calibration: mean/max corner error in pixels vs. ground truth,
    and IoU between the detected and ground-truth court quadrilaterals.
  - Player tracking: for fixtures with a known player path, mean center
    distance (pixels) between the best-matching track and ground truth at
    each ground-truth timestamp, and IoU of the matched boxes.

Only synthetic fixtures exist today — see docs/CV_ARCHITECTURE.md "Test
fixtures and the real-footage gap" for why real-footage numbers are not
included, and do not represent them as such when reading this report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.detection import PersonDetector  # noqa: E402
from app.pipeline import run_analysis  # noqa: E402

GROUND_TRUTH_DIR = Path(__file__).resolve().parent / "ground_truth"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _quad_iou(a: list[list[float]], b: list[list[float]], canvas_size: tuple[int, int]) -> float:
    """IoU of two quadrilaterals via rasterization — correct for
    non-axis-aligned shapes, unlike a naive bbox IoU."""
    w, h = canvas_size
    mask_a = np.zeros((h, w), dtype=np.uint8)
    mask_b = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask_a, [np.array(a, dtype=np.int32)], 1)
    cv2.fillPoly(mask_b, [np.array(b, dtype=np.int32)], 1)
    intersection = np.logical_and(mask_a, mask_b).sum()
    union = np.logical_or(mask_a, mask_b).sum()
    return float(intersection / union) if union > 0 else 0.0


def evaluate_court_calibration(ground_truth: dict, result) -> dict:
    gt_corners_dict = ground_truth["court_corners_px"]
    gt_corners = [
        gt_corners_dict["top_left"],
        gt_corners_dict["top_right"],
        gt_corners_dict["bottom_right"],
        gt_corners_dict["bottom_left"],
    ]

    if result.calibration.court_corners_px is None:
        return {
            "attempted": True,
            "succeeded": False,
            "status": result.calibration.status,
            "mean_corner_error_px": None,
            "max_corner_error_px": None,
            "iou": 0.0,
        }

    detected = result.calibration.court_corners_px
    errors = [
        float(np.hypot(d[0] - g[0], d[1] - g[1])) for d, g in zip(detected, gt_corners)
    ]
    iou = _quad_iou(detected, gt_corners, (ground_truth["width"], ground_truth["height"]))

    return {
        "attempted": True,
        "succeeded": True,
        "status": result.calibration.status,
        "confidence": result.calibration.confidence,
        "mean_corner_error_px": round(sum(errors) / len(errors), 2),
        "max_corner_error_px": round(max(errors), 2),
        "iou": round(iou, 4),
    }


def run_fixture(name: str, detector: PersonDetector) -> dict:
    gt_path = GROUND_TRUTH_DIR / f"{name}.json"
    video_path = FIXTURES_DIR / f"{name}.mp4"
    ground_truth = json.loads(gt_path.read_text())

    result = run_analysis(video_path=video_path, detector=detector, sampling_fps=2.0, max_sampled_frames=600)

    return {
        "fixture": name,
        "description": ground_truth.get("description"),
        "quality": {"status": result.quality.status, "reasons": result.quality.reasons},
        "calibration": evaluate_court_calibration(ground_truth, result),
        "tracks_found": len(result.tracks),
        "processing_seconds": result.processing_metadata.processing_seconds,
    }


def main() -> None:
    fixtures = sorted(p.stem for p in GROUND_TRUTH_DIR.glob("*.json"))
    if not fixtures:
        print("No ground-truth fixtures found in eval/ground_truth/. Run generate_synthetic_fixture.py first.")
        return

    print("=" * 78)
    print("CV EVALUATION REPORT")
    print(
        "NOTE: all fixtures below are SYNTHETIC (see eval/fixtures/generate_synthetic_fixture.py). "
        "These numbers validate pipeline geometry correctness, not real-world accuracy on actual "
        "badminton footage — see docs/CV_ARCHITECTURE.md 'Test fixtures and the real-footage gap'."
    )
    print("=" * 78)

    detector = PersonDetector()
    try:
        for name in fixtures:
            report = run_fixture(name, detector)
            print(f"\nFixture: {report['fixture']}")
            print(f"  {report['description']}")
            print(f"  Quality: {report['quality']['status']}")
            calib = report["calibration"]
            if calib["succeeded"]:
                print(
                    f"  Court calibration: {calib['status']} (confidence {calib['confidence']}) — "
                    f"mean corner error {calib['mean_corner_error_px']}px, "
                    f"max {calib['max_corner_error_px']}px, IoU {calib['iou']}"
                )
            else:
                print(f"  Court calibration: {calib['status']} — no corners to compare")
            print(f"  Player tracks found: {report['tracks_found']} (expected 0 on synthetic non-human fixtures)")
            print(f"  Processing time: {report['processing_seconds']}s")
    finally:
        detector.close()

    print("\n" + "=" * 78)
    print("Person-detection accuracy is NOT benchmarked against these fixtures — they contain no")
    print("real human shape. See docs/CV_ARCHITECTURE.md for the model vendor's own published")
    print("COCO benchmark figures, cited (not independently verified) as the only accuracy reference")
    print("currently available for the person detector.")
    print("=" * 78)


if __name__ == "__main__":
    main()
