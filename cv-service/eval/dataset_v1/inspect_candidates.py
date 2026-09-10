"""Measure candidate footage and classify it for M5.5 suitability.

Everything here is measured from actual decoded frames. Page titles and provider
descriptions are never inputs to a verdict.

Deliberate design choice -- the triage detectors below (OpenCV HOG person detector,
Hough-transform court-line evidence) are NOT the M5 detectors. Selecting evaluation
clips with the same detector M5.5 is about to grade would bias the validation toward
footage M5 already happens to handle. These are independent, weaker proxies used only
to triage, and their weakness is why a low score routes to MANUAL_REVIEW rather than
REJECT.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

from .sources import dataset_root, ensure_layout

ACCEPT = "ACCEPT"
MANUAL_REVIEW = "MANUAL_REVIEW"
REJECT = "REJECT"

CONTACT_SHEET_COLUMNS = 5
CONTACT_SHEET_ROWS = 4
CONTACT_SHEET_TILE_WIDTH = 400
# HOG's default people detector uses a 64x128 window, so a player needs roughly 128px of
# height before it can fire. A sideline badminton player occupies maybe 15-30% of frame
# height, which at 640px-wide analysis frames leaves them far too small. 960px plus the
# upscaling sweep below keeps players in range down to ~15% of frame height.
ANALYSIS_FRAME_WIDTH = 960
CUT_SAMPLE_FPS = 4.0
CUT_CHI2_THRESHOLD = 0.45
MIN_SEGMENT_SECONDS = 5.0
DETECTION_SCALES = (1.0, 1.5, 2.0)
DETECTION_MIN_CONFIDENCE = 0.6


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    """Container/stream facts via ffprobe, plus size and content hash."""
    raw = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,avg_frame_rate,codec_name,nb_frames,pix_fmt",
            "-show_entries", "format=duration,size,format_name,bit_rate",
            "-of", "json", str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    payload = json.loads(raw.stdout)
    stream = (payload.get("streams") or [{}])[0]
    fmt = payload.get("format") or {}

    def ratio(value: str | None) -> float | None:
        if not value or "/" not in value:
            return None
        num, den = value.split("/", 1)
        return round(float(num) / float(den), 4) if float(den) else None

    return {
        "filename": path.name,
        "sha256": sha256_of(path),
        "file_size_bytes": path.stat().st_size,
        "width": stream.get("width"),
        "height": stream.get("height"),
        "resolution": f"{stream.get('width')}x{stream.get('height')}",
        "fps": ratio(stream.get("avg_frame_rate")) or ratio(stream.get("r_frame_rate")),
        "duration_seconds": round(float(fmt["duration"]), 3) if fmt.get("duration") else None,
        "codec": stream.get("codec_name"),
        "pixel_format": stream.get("pix_fmt"),
        "container": fmt.get("format_name"),
        "bit_rate": int(fmt["bit_rate"]) if fmt.get("bit_rate") else None,
    }


def _person_detector():
    if not hasattr(cv2, "HOGDescriptor"):
        raise RuntimeError(
            f"cv2 {cv2.__version__} has no HOGDescriptor: OpenCV 5 removed the legacy "
            "objdetect detectors. Install the pinned 4.x line "
            "(pip install 'opencv-python==4.10.0.84'). Person counts are refused rather "
            "than degraded, because a silently weaker detector would produce misleading "
            "ACCEPT/REJECT verdicts."
        )
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    return hog


def _detect_people(hog, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Multi-scale HOG person detection, merged with non-max suppression.

    Measured on scikit-image's public-domain astronaut photo, single-scale HOG fired at
    1.0x and 2.0x but found nothing at 1.5x -- it is sharply scale-brittle. Sweeping a
    few input scales and merging recovers detections a single pass drops. It is still a
    weak detector, which is why zero detections never triggers a REJECT.
    """
    boxes: list[list[int]] = []
    scores: list[float] = []
    for scale in DETECTION_SCALES:
        image = frame if scale == 1.0 else cv2.resize(frame, None, fx=scale, fy=scale)
        found, weights = hog.detectMultiScale(image, winStride=(8, 8), padding=(8, 8), scale=1.05)
        for box, weight in zip(found, weights):
            confidence = float(np.ravel(weight)[0])
            if confidence < DETECTION_MIN_CONFIDENCE:
                continue
            boxes.append([int(v / scale) for v in box])
            scores.append(confidence)

    if not boxes:
        return []
    keep = cv2.dnn.NMSBoxes(boxes, scores, DETECTION_MIN_CONFIDENCE, 0.4)
    return [tuple(boxes[i]) for i in np.ravel(keep)] if len(keep) else []


def _court_line_evidence(gray: np.ndarray) -> dict:
    """Weak proxy for 'a marked court is visible': long straight lines on a flat floor."""
    height, width = gray.shape
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=80,
        minLineLength=int(0.15 * width),
        maxLineGap=12,
    )
    if lines is None:
        return {"long_line_count": 0, "orientation_spread_deg": 0.0, "score": 0.0}

    angles = []
    for x1, y1, x2, y2 in lines[:, 0]:
        angles.append(abs(np.degrees(np.arctan2(y2 - y1, x2 - x1))) % 180.0)

    count = len(angles)
    spread = float(np.percentile(angles, 90) - np.percentile(angles, 10)) if count > 1 else 0.0
    # Court markings give many long lines across at least two distinct orientations.
    score = min(1.0, count / 25.0) * (0.5 + 0.5 * min(1.0, spread / 40.0))
    return {
        "long_line_count": count,
        "orientation_spread_deg": round(spread, 1),
        "score": round(float(score), 3),
    }


def _luminance(gray: np.ndarray) -> dict:
    return {
        "mean": round(float(gray.mean()), 1),
        "std": round(float(gray.std()), 1),
        "crushed_pct": round(float((gray < 16).mean() * 100), 2),
        "clipped_pct": round(float((gray > 240).mean() * 100), 2),
    }


def _detect_cuts(capture: cv2.VideoCapture, fps: float, duration: float) -> list[float]:
    """Timestamps of likely shot boundaries, from HSV histogram distance."""
    step = max(1, int(round(fps / CUT_SAMPLE_FPS)))
    cuts: list[float] = []
    previous = None
    index = 0
    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
    while True:
        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = capture.read()
        if not ok:
            break
        small = cv2.resize(frame, (160, 90))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        if previous is not None:
            distance = cv2.compareHist(previous, hist, cv2.HISTCMP_BHATTACHARYYA)
            if distance > CUT_CHI2_THRESHOLD:
                cuts.append(round(index / fps, 2))
        previous = hist
        index += step
        if index / fps > duration:
            break
    return cuts


def _segments_from_cuts(cuts: list[float], duration: float) -> list[dict]:
    boundaries = [0.0, *cuts, duration]
    segments = []
    for start, end in zip(boundaries, boundaries[1:]):
        if end - start >= MIN_SEGMENT_SECONDS:
            segments.append(
                {"start": round(start, 2), "end": round(end, 2), "duration": round(end - start, 2)}
            )
    return segments


def analyse(path: Path, metadata: dict, samples: int = 24) -> dict:
    """Decode frames and measure everything the classifier needs."""
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"OpenCV could not open {path}")

    fps = metadata.get("fps") or capture.get(cv2.CAP_PROP_FPS) or 30.0
    duration = metadata.get("duration_seconds") or 0.0
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) or int(fps * duration)
    hog = _person_detector()

    indices = np.linspace(0, max(total_frames - 2, 0), num=samples, dtype=int)
    per_frame: list[dict] = []
    motion_px: list[float] = []

    for frame_index in indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
        ok, frame = capture.read()
        if not ok:
            continue
        scale = ANALYSIS_FRAME_WIDTH / frame.shape[1]
        small = cv2.resize(frame, (ANALYSIS_FRAME_WIDTH, int(frame.shape[0] * scale)))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        boxes = _detect_people(hog, small)
        separation = None
        if len(boxes) >= 2:
            widest = sorted(boxes, key=lambda b: b[2] * b[3], reverse=True)[:2]
            centres = [b[0] + b[2] / 2 for b in widest]
            separation = round(abs(centres[0] - centres[1]) / small.shape[1], 3)

        per_frame.append({
            "frame_index": int(frame_index),
            "timestamp": round(float(frame_index) / fps, 2),
            "person_count": len(boxes),
            "person_boxes": boxes,
            "player_separation_norm": separation,
            "court": _court_line_evidence(gray),
            "luminance": _luminance(gray),
        })

        # Global camera translation between this frame and the very next one.
        ok_next, frame_next = capture.read()
        if ok_next:
            a = cv2.cvtColor(cv2.resize(frame, (320, 180)), cv2.COLOR_BGR2GRAY).astype(np.float32)
            b = cv2.cvtColor(
                cv2.resize(frame_next, (320, 180)), cv2.COLOR_BGR2GRAY
            ).astype(np.float32)
            (dx, dy), _ = cv2.phaseCorrelate(a, b)
            motion_px.append(float(np.hypot(dx, dy)))

    cuts = _detect_cuts(capture, fps, duration)
    capture.release()

    counts = [f["person_count"] for f in per_frame]
    separations = [f["player_separation_norm"] for f in per_frame if f["player_separation_norm"]]
    court_scores = [f["court"]["score"] for f in per_frame]
    means = [f["luminance"]["mean"] for f in per_frame]
    clipped = [f["luminance"]["clipped_pct"] for f in per_frame]
    crushed = [f["luminance"]["crushed_pct"] for f in per_frame]

    segments = _segments_from_cuts(cuts, duration)
    for segment in segments:
        inside = [f for f in per_frame if segment["start"] <= f["timestamp"] < segment["end"]]
        two_plus = [f for f in inside if f["person_count"] >= 2]
        segment["sampled_frames"] = len(inside)
        segment["two_player_frame_pct"] = (
            round(100.0 * len(two_plus) / len(inside), 1) if inside else 0.0
        )

    return {
        "sampled_frames": len(per_frame),
        "shot_cuts_detected": cuts,
        "continuous_segments": segments,
        "longest_segment_seconds": max((s["duration"] for s in segments), default=0.0),
        "persons": {
            "median_per_frame": float(np.median(counts)) if counts else 0.0,
            "max_per_frame": int(max(counts)) if counts else 0,
            "frames_with_1plus_pct": round(100.0 * sum(c >= 1 for c in counts) / len(counts), 1)
            if counts else 0.0,
            "frames_with_2plus_pct": round(100.0 * sum(c >= 2 for c in counts) / len(counts), 1)
            if counts else 0.0,
            "frames_with_4plus_pct": round(100.0 * sum(c >= 4 for c in counts) / len(counts), 1)
            if counts else 0.0,
        },
        "player_separation_norm_median": round(float(np.median(separations)), 3)
        if separations else None,
        "court_line_evidence_median": round(float(np.median(court_scores)), 3)
        if court_scores else 0.0,
        "camera_motion_px_median": round(float(np.median(motion_px)), 2) if motion_px else None,
        "camera_motion_px_p90": round(float(np.percentile(motion_px, 90)), 2) if motion_px else None,
        "luminance": {
            "mean_of_means": round(float(np.mean(means)), 1) if means else 0.0,
            "max_clipped_pct": round(float(max(clipped)), 2) if clipped else 0.0,
            "max_crushed_pct": round(float(max(crushed)), 2) if crushed else 0.0,
        },
        "per_frame": per_frame,
    }


def classify(metadata: dict, measurements: dict) -> dict:
    """Verdict from measured evidence.

    REJECT is reserved for hard technical facts (resolution, duration, no continuous
    segment, no people anywhere). Weak scores from the deliberately-weak triage
    detectors route to MANUAL_REVIEW so a human decides from the contact sheet.
    """
    reject: list[str] = []
    review: list[str] = []
    accept: list[str] = []

    height = metadata.get("height") or 0
    duration = metadata.get("duration_seconds") or 0.0
    persons = measurements["persons"]
    longest = measurements["longest_segment_seconds"]
    motion = measurements.get("camera_motion_px_median")
    court = measurements["court_line_evidence_median"]
    luminance = measurements["luminance"]

    if height < 480:
        reject.append(f"vertical resolution {height}px is below the 480px floor for CV work")
    elif height >= 720:
        accept.append(f"resolution {metadata['resolution']} is adequate")
    else:
        review.append(f"resolution {metadata['resolution']} is marginal (480-719px)")

    if duration < MIN_SEGMENT_SECONDS:
        reject.append(f"duration {duration}s is shorter than one usable clip")
    if longest < MIN_SEGMENT_SECONDS:
        reject.append(f"no continuous segment reaches {MIN_SEGMENT_SECONDS}s between cuts")
    elif longest >= 10.0:
        accept.append(f"longest uninterrupted segment is {longest}s")
    else:
        review.append(f"longest uninterrupted segment is only {longest}s")

    if persons["frames_with_1plus_pct"] == 0.0:
        # Never a REJECT: the HOG triage detector is scale-brittle enough to return zero
        # on frames that plainly contain people, so this has to go to a human.
        review.append(
            "no person detected in any sampled frame -- this alone does not disqualify the "
            "footage, because the triage detector misses people at some scales; open the "
            "contact sheet and confirm by eye"
        )
    elif persons["frames_with_2plus_pct"] >= 60.0:
        accept.append(f"two or more people in {persons['frames_with_2plus_pct']}% of sampled frames")
    else:
        review.append(
            f"two or more people in only {persons['frames_with_2plus_pct']}% of sampled frames "
            "(HOG triage detector under-counts occluded/crouching players -- verify on the "
            "contact sheet)"
        )

    if court >= 0.45:
        accept.append(f"court-line evidence {court} indicates visible court markings")
    else:
        review.append(f"court-line evidence {court} is weak -- confirm court visibility by eye")

    if motion is None:
        review.append("camera motion could not be measured")
    elif motion <= 2.0:
        accept.append(f"camera is stable (median inter-frame translation {motion}px)")
    elif motion <= 6.0:
        review.append(f"camera drifts or pans (median inter-frame translation {motion}px)")
    else:
        review.append(f"camera is unstable/handheld (median inter-frame translation {motion}px)")

    if 40.0 <= luminance["mean_of_means"] <= 220.0 and luminance["max_clipped_pct"] < 10.0:
        accept.append(f"lighting is workable (mean luma {luminance['mean_of_means']})")
    else:
        review.append(
            f"lighting is difficult (mean luma {luminance['mean_of_means']}, "
            f"max clipped {luminance['max_clipped_pct']}%)"
        )

    if persons["frames_with_4plus_pct"] >= 40.0:
        likely_format = "doubles"
    elif persons["frames_with_2plus_pct"] >= 50.0:
        likely_format = "singles"
    else:
        likely_format = "unknown"

    if reject:
        verdict = REJECT
    elif review:
        verdict = MANUAL_REVIEW
    else:
        verdict = ACCEPT

    best = sorted(
        [s for s in measurements["continuous_segments"] if s["duration"] >= MIN_SEGMENT_SECONDS],
        key=lambda s: (s["two_player_frame_pct"], s["duration"]),
        reverse=True,
    )[:3]

    return {
        "verdict": verdict,
        "likely_format": likely_format,
        "reject_reasons": reject,
        "review_reasons": review,
        "supporting_evidence": accept,
        "best_candidate_segments": best,
    }


def contact_sheet(path: Path, measurements: dict, destination: Path, annotated: bool) -> Path:
    """Grid of representative frames, optionally showing what the triage detectors saw."""
    capture = cv2.VideoCapture(str(path))
    frames = measurements["per_frame"]
    wanted = CONTACT_SHEET_COLUMNS * CONTACT_SHEET_ROWS
    picks = [frames[i] for i in np.linspace(0, len(frames) - 1, num=min(wanted, len(frames)), dtype=int)]

    tiles = []
    for record in picks:
        capture.set(cv2.CAP_PROP_POS_FRAMES, record["frame_index"])
        ok, frame = capture.read()
        if not ok:
            continue
        scale = ANALYSIS_FRAME_WIDTH / frame.shape[1]
        view = cv2.resize(frame, (ANALYSIS_FRAME_WIDTH, int(frame.shape[0] * scale)))

        if annotated:
            for x, y, w, h in record["person_boxes"]:
                cv2.rectangle(view, (x, y), (x + w, y + h), (0, 220, 0), 2)
            cv2.putText(
                view, f"people={record['person_count']} court={record['court']['score']}",
                (8, view.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1,
                cv2.LINE_AA,
            )

        tile_height = int(CONTACT_SHEET_TILE_WIDTH * view.shape[0] / view.shape[1])
        tile = cv2.resize(view, (CONTACT_SHEET_TILE_WIDTH, tile_height))
        cv2.rectangle(tile, (0, 0), (110, 20), (0, 0, 0), -1)
        cv2.putText(
            tile, f"t={record['timestamp']}s", (5, 15),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA,
        )
        tiles.append(tile)
    capture.release()

    if not tiles:
        raise RuntimeError(f"no frames could be decoded from {path}")

    blank = np.zeros_like(tiles[0])
    rows = []
    for start in range(0, len(tiles), CONTACT_SHEET_COLUMNS):
        row = tiles[start : start + CONTACT_SHEET_COLUMNS]
        row += [blank] * (CONTACT_SHEET_COLUMNS - len(row))
        rows.append(np.hstack(row))
    sheet = np.vstack(rows)

    banner = np.zeros((34, sheet.shape[1], 3), dtype=np.uint8)
    label = f"{path.name}  ({'annotated: triage detections' if annotated else 'raw frames'})"
    cv2.putText(banner, label, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

    destination.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destination), np.vstack([banner, sheet]), [cv2.IMWRITE_JPEG_QUALITY, 88])
    return destination


def export_frames(path: Path, measurements: dict, destination_dir: Path, count: int = 8) -> list[Path]:
    capture = cv2.VideoCapture(str(path))
    frames = measurements["per_frame"]
    picks = [frames[i] for i in np.linspace(0, len(frames) - 1, num=min(count, len(frames)), dtype=int)]
    destination_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for record in picks:
        capture.set(cv2.CAP_PROP_POS_FRAMES, record["frame_index"])
        ok, frame = capture.read()
        if not ok:
            continue
        out = destination_dir / f"t{record['timestamp']:07.2f}s.jpg"
        cv2.imwrite(str(out), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        written.append(out)
    capture.release()
    return written


def inspect_file(path: Path, root: Path) -> dict:
    print(f"\n[{path.name}] probing")
    metadata = probe(path)
    print(f"  {metadata['resolution']} @ {metadata['fps']}fps, {metadata['duration_seconds']}s, "
          f"{metadata['codec']}, {metadata['file_size_bytes']:,} bytes")
    print(f"  sha256 {metadata['sha256']}")

    print("  analysing frames")
    measurements = analyse(path, metadata)
    verdict = classify(metadata, measurements)
    print(f"  verdict {verdict['verdict']} (likely {verdict['likely_format']})")

    stem = path.stem
    contact_sheet(path, measurements, root / "contact_sheets" / f"{stem}.jpg", annotated=False)
    contact_sheet(path, measurements, root / "contact_sheets" / f"{stem}_annotated.jpg", annotated=True)
    export_frames(path, measurements, root / "frames" / stem)

    record = {"metadata": metadata, "measurements": measurements, "classification": verdict}
    (root / "metadata" / f"{stem}.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (root / "analysis" / f"{stem}.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def inspect_all(root: str | Path | None = None) -> list[dict]:
    dataset = dataset_root(root)
    ensure_layout(dataset)
    videos = sorted(
        p for p in (dataset / "incoming").iterdir()
        if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}
    ) if (dataset / "incoming").exists() else []

    if not videos:
        print(f"No video files in {dataset / 'incoming'} -- nothing to inspect.")
        return []

    return [inspect_file(video, dataset) for video in videos]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Inspect and classify dataset v1 candidates.")
    parser.add_argument("--dataset-dir", default=None)
    args = parser.parse_args()
    inspect_all(args.dataset_dir)
    return 0
