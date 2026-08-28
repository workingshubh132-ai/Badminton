"""
Generates a SYNTHETIC test video: a rendered badminton court (known-exact
corner coordinates) with a simple moving rectangle standing in for a player.

THIS IS NOT REAL FOOTAGE OF A REAL COURT OR A REAL PERSON. It exists to
validate that the court-calibration GEOMETRY (line detection, homography)
and tracking GEOMETRY (IoU association, gap handling) are implemented
correctly against known ground truth — see docs/CV_ARCHITECTURE.md "Test
fixtures and the real-footage gap" for why this is the honest scope of what
this fixture can validate, and what it cannot (real footage is textured,
unevenly lit, and has a real human shape a real detector was trained on;
this fixture has none of that, so it says nothing about real-world court-
detection or person-detection accuracy).

Usage: python eval/fixtures/generate_synthetic_fixture.py
Writes eval/fixtures/synthetic_court_01.mp4 and the matching ground-truth
JSON to eval/ground_truth/synthetic_court_01.json.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

FIXTURE_DIR = Path(__file__).resolve().parent
GROUND_TRUTH_DIR = FIXTURE_DIR.parent / "ground_truth"

WIDTH, HEIGHT = 1280, 720
FPS = 24
DURATION_SECONDS = 5
FRAME_COUNT = FPS * DURATION_SECONDS

# Known-exact court corners in pixel space (TL, TR, BR, BL), representing a
# mild elevated-angle camera view (far end of the court narrower than the
# near end) — chosen by hand, not derived from a real 3D projection.
COURT_CORNERS_PX = [(360, 120), (920, 120), (1100, 620), (180, 620)]

BACKGROUND_COLOR = (40, 110, 40)  # a plausible court-surface green, BGR
LINE_COLOR = (255, 255, 255)
LINE_THICKNESS = 4

# A simple filled rectangle standing in for "a player" — moves along a
# fixed, known path across the court. Explicitly NOT human-shaped; see
# module docstring for why a real person detector is not expected to fire
# on this reliably (and that's fine — it's not what this fixture tests).
PLAYER_SIZE_PX = (60, 140)
PLAYER_COLOR = (30, 30, 200)


def _lerp(a: tuple[float, float], b: tuple[float, float], t: float) -> tuple[float, float]:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _draw_court(frame: np.ndarray) -> None:
    frame[:] = BACKGROUND_COLOR
    pts = np.array(COURT_CORNERS_PX, dtype=np.int32)
    cv2.polylines(frame, [pts], isClosed=True, color=LINE_COLOR, thickness=LINE_THICKNESS)
    # A center service line, for visual plausibility only (not used as a
    # ground-truth signal by the calibration algorithm).
    mid_top = _lerp(COURT_CORNERS_PX[0], COURT_CORNERS_PX[1], 0.5)
    mid_bottom = _lerp(COURT_CORNERS_PX[3], COURT_CORNERS_PX[2], 0.5)
    cv2.line(
        frame,
        (int(mid_top[0]), int(mid_top[1])),
        (int(mid_bottom[0]), int(mid_bottom[1])),
        LINE_COLOR,
        LINE_THICKNESS // 2,
    )


def _player_position(frame_index: int) -> tuple[int, int]:
    """Known ground-truth path: sweeps from left service area to right
    baseline and back, so tracking gets continuous motion to follow."""
    t = (frame_index / FRAME_COUNT) % 1.0
    path_t = abs(((t * 2) % 2) - 1)  # 0 -> 1 -> 0 triangle wave
    start = _lerp(COURT_CORNERS_PX[3], COURT_CORNERS_PX[0], 0.6)
    end = _lerp(COURT_CORNERS_PX[2], COURT_CORNERS_PX[1], 0.6)
    x, y = _lerp(start, end, path_t)
    return int(x), int(y)


def generate() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    player_positions = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(FRAME_COUNT):
            frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
            _draw_court(frame)
            px, py = _player_position(i)
            half_w, half_h = PLAYER_SIZE_PX[0] // 2, PLAYER_SIZE_PX[1] // 2
            cv2.rectangle(frame, (px - half_w, py - half_h), (px + half_w, py + half_h), PLAYER_COLOR, -1)
            player_positions.append(
                {
                    "frame_index": i,
                    "timestamp_seconds": round(i / FPS, 4),
                    "bbox_px": [px - half_w, py - half_h, PLAYER_SIZE_PX[0], PLAYER_SIZE_PX[1]],
                }
            )
            cv2.imwrite(str(tmp_path / f"frame_{i:05d}.png"), frame)

        output_path = FIXTURE_DIR / "synthetic_court_01.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(FPS),
                "-i",
                str(tmp_path / "frame_%05d.png"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )

    ground_truth = {
        "fixture": "synthetic_court_01",
        "description": (
            "Synthetic, non-photorealistic rendered court with a solid-rectangle player proxy. "
            "See module docstring / docs/CV_ARCHITECTURE.md for exactly what this does and does not validate."
        ),
        "width": WIDTH,
        "height": HEIGHT,
        "fps": FPS,
        "duration_seconds": DURATION_SECONDS,
        "court_corners_px": {
            "top_left": list(COURT_CORNERS_PX[0]),
            "top_right": list(COURT_CORNERS_PX[1]),
            "bottom_right": list(COURT_CORNERS_PX[2]),
            "bottom_left": list(COURT_CORNERS_PX[3]),
        },
        "player_positions": player_positions,
    }
    with open(GROUND_TRUTH_DIR / "synthetic_court_01.json", "w") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"Wrote {output_path}")
    print(f"Wrote {GROUND_TRUTH_DIR / 'synthetic_court_01.json'}")


if __name__ == "__main__":
    generate()
