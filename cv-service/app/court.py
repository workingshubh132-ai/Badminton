"""
Classical (non-learned) badminton court boundary detection and calibration.

Method: Canny edges -> probabilistic Hough line transform -> separate lines
into near-horizontal / near-vertical groups -> take the outermost strong
clusters as the four boundary lines -> intersect them for corner points ->
homography from those corners to real-world court meters.

This is a deliberately explainable heuristic, not a trained model — there is
no labeled badminton-court dataset available to train one, and a classical
approach fails in a legible way ("no lines found") rather than as a silent
black box. See docs/CV_ARCHITECTURE.md "Court detection" for the honest
account of when this is expected to work and when it is not: it is
correctness-tested against a synthetic, high-contrast rendered court (see
eval/), and UNVALIDATED against real, textured, unevenly-lit phone footage
of an actual badminton court. Expect LOW_CONFIDENCE or FAILED on real
recordings until this is replaced or supplemented by a learned detector.

Confidence is capped at MODERATE for this reason — see
docs/CV_ARCHITECTURE.md "Acceptance thresholds".
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

from app.config import COURT_LENGTH_M, COURT_WIDTH_M
from app.preprocessing import SampledFrame
from app.schemas import CourtCalibration

# Real-world court corners, in the fixed order (top-left, top-right,
# bottom-right, bottom-left) that court_corners_px must also follow.
_COURT_CORNERS_M = np.array(
    [[0.0, 0.0], [COURT_WIDTH_M, 0.0], [COURT_WIDTH_M, COURT_LENGTH_M], [0.0, COURT_LENGTH_M]],
    dtype=np.float32,
)

_MIN_LINE_LENGTH_FRACTION = 0.15
_MIN_QUAD_AREA_FRACTION = 0.05
_MAX_QUAD_AREA_FRACTION = 0.97
_CORNER_AGREEMENT_TOLERANCE_FRACTION = 0.08  # of frame diagonal


@dataclass
class _Line:
    x1: float
    y1: float
    x2: float
    y2: float


def _detect_lines(frame: np.ndarray) -> list[_Line]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    h, w = gray.shape
    min_length = int(min(h, w) * _MIN_LINE_LENGTH_FRACTION)
    raw = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=60, minLineLength=min_length, maxLineGap=20
    )
    if raw is None:
        return []
    # OpenCV has returned this as either (N, 1, 4) or (N, 4) across versions
    # (verified (N, 4) on opencv-contrib-python 5.0.0.93, the pinned
    # version) — reshape defensively so either shape works.
    return [_Line(*coords) for coords in raw.reshape(-1, 4)]


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Standard, well-known ordering: top-left has the smallest x+y sum,
    bottom-right the largest; top-right has the smallest x-y difference,
    bottom-left the largest. Robust to rotation/perspective, not just
    axis-aligned rectangles."""
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).flatten()
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def _find_quad_in_frame(frame: np.ndarray) -> tuple[np.ndarray, list[str]] | None:
    """
    Returns 4 corner points (px, TL/TR/BR/BL order) or None.

    Method: take the endpoints of every detected boundary-length line
    segment, compute their convex hull, and approximate that hull down to a
    quadrilateral. This is deliberately NOT "classify lines as
    horizontal/vertical then take the extremes" — that approach breaks under
    real camera perspective, where a court's side lines are diagonal, not
    vertical, and can be confused with genuinely-vertical internal lines
    (e.g. a center service line). The convex hull of all boundary-length
    line endpoints has the actual court corners as its extreme points
    regardless of perspective angle, as long as no internal line extends
    beyond the outer boundary — true for a real court by construction
    (service/center lines are always inside the boundary).
    """
    h, w = frame.shape[:2]
    lines = _detect_lines(frame)
    if len(lines) < 4:
        return None

    points = np.array(
        [[ln.x1, ln.y1] for ln in lines] + [[ln.x2, ln.y2] for ln in lines],
        dtype=np.float32,
    )
    hull = cv2.convexHull(points)
    if hull is None or len(hull) < 4:
        return None

    perimeter = cv2.arcLength(hull, closed=True)
    quad = None
    for epsilon_fraction in (0.01, 0.02, 0.03, 0.05, 0.08, 0.12):
        approx = cv2.approxPolyDP(hull, epsilon_fraction * perimeter, closed=True)
        if len(approx) == 4:
            quad = approx.reshape(4, 2).astype(np.float32)
            break
    if quad is None:
        return None

    corners = _order_corners(quad)
    if not np.all(np.isfinite(corners)):
        return None

    area = cv2.contourArea(corners)
    frame_area = w * h
    if not (frame_area * _MIN_QUAD_AREA_FRACTION <= area <= frame_area * _MAX_QUAD_AREA_FRACTION):
        return None
    if not cv2.isContourConvex(corners.astype(np.int32).reshape(-1, 1, 2)):
        return None

    return corners, []


def calibrate_court(sampled_frames: list[SampledFrame]) -> CourtCalibration:
    if not sampled_frames:
        return CourtCalibration(status="NOT_ATTEMPTED", warnings=["No frames available to attempt calibration."])

    per_frame_results: list[tuple[float, np.ndarray]] = []
    for sf in sampled_frames:
        found = _find_quad_in_frame(sf.frame)
        if found is not None:
            corners, _ = found
            per_frame_results.append((sf.timestamp_seconds, corners))

    attempted = len(sampled_frames)
    succeeded = len(per_frame_results)

    if succeeded == 0:
        return CourtCalibration(
            status="FAILED",
            warnings=[
                f"No stable court boundary quadrilateral was found in any of {attempted} sampled frames.",
                "This classical line-detection method requires clear, high-contrast, mostly unobstructed "
                "court boundary lines — see docs/CV_ARCHITECTURE.md 'Court detection' for known limitations.",
            ],
        )

    # Cluster by proximity to the median corner set (a simple, defensible
    # temporal-consistency signal — see module docstring).
    stacked = np.stack([c for _, c in per_frame_results])
    median_corners = np.median(stacked, axis=0)
    diag = math.hypot(*stacked[0].max(axis=0))
    tolerance = diag * _CORNER_AGREEMENT_TOLERANCE_FRACTION

    agreeing = [
        (ts, c) for ts, c in per_frame_results if np.all(np.linalg.norm(c - median_corners, axis=1) < tolerance)
    ]
    agreement_ratio = len(agreeing) / attempted

    warnings = []
    if succeeded < attempted:
        warnings.append(f"Court boundary found in {succeeded}/{attempted} sampled frames.")

    if agreement_ratio < 0.3:
        return CourtCalibration(
            status="LOW_CONFIDENCE",
            confidence="VERY_LOW",
            court_corners_px=median_corners.tolist(),
            source_frame_timestamps=[ts for ts, _ in per_frame_results],
            warnings=warnings + ["Detected court boundaries were inconsistent across sampled frames."],
        )

    final_corners = np.median(np.stack([c for _, c in agreeing]), axis=0).astype(np.float32)
    homography, _ = cv2.findHomography(final_corners, _COURT_CORNERS_M)
    if homography is None:
        return CourtCalibration(
            status="FAILED",
            court_corners_px=final_corners.tolist(),
            source_frame_timestamps=[ts for ts, _ in agreeing],
            warnings=warnings + ["A court boundary was found but the homography could not be computed."],
        )

    # Confidence is deliberately capped at MODERATE — see module docstring.
    confidence = "MODERATE" if agreement_ratio >= 0.6 else "LOW"
    status = "SUCCESS" if agreement_ratio >= 0.6 else "PARTIAL"

    return CourtCalibration(
        status=status,
        confidence=confidence,
        homography=homography.tolist(),
        court_corners_px=final_corners.tolist(),
        source_frame_timestamps=[ts for ts, _ in agreeing],
        warnings=warnings,
    )


def video_point_to_court(homography: list[list[float]], x_px: float, y_px: float) -> tuple[float, float] | None:
    """Maps a video-pixel point to real-world court meters using a
    previously-computed homography. Returns None if the point projects
    outside a reasonable margin of the court (a common sign of a bad
    homography or a point that's genuinely off-court, e.g. a spectator)."""
    h = np.array(homography, dtype=np.float64)
    point = np.array([x_px, y_px, 1.0])
    mapped = h @ point
    if abs(mapped[2]) < 1e-9:
        return None
    court_x, court_y = mapped[0] / mapped[2], mapped[1] / mapped[2]
    margin = 2.0  # meters — tolerate a bit outside the lines (players do run out)
    if -margin <= court_x <= COURT_WIDTH_M + margin and -margin <= court_y <= COURT_LENGTH_M + margin:
        return float(court_x), float(court_y)
    return None
