import math

import cv2
import numpy as np
import pytest

from app.court import _find_quad_in_frame, _order_corners, calibrate_court, video_point_to_court
from app.preprocessing import SampledFrame


def _draw_trapezoid_court(corners: list[tuple[int, int]], size=(720, 1280)) -> np.ndarray:
    frame = np.full((*size, 3), (40, 110, 40), dtype=np.uint8)
    pts = np.array(corners, dtype=np.int32)
    cv2.polylines(frame, [pts], isClosed=True, color=(255, 255, 255), thickness=4)
    return frame


KNOWN_CORNERS = [(360, 120), (920, 120), (1100, 620), (180, 620)]  # TL, TR, BR, BL


class TestOrderCorners:
    def test_orders_a_shuffled_quadrilateral_correctly(self):
        shuffled = np.array([KNOWN_CORNERS[2], KNOWN_CORNERS[0], KNOWN_CORNERS[3], KNOWN_CORNERS[1]], dtype=np.float32)
        ordered = _order_corners(shuffled)
        np.testing.assert_allclose(ordered, np.array(KNOWN_CORNERS, dtype=np.float32))


class TestFindQuadInFrame:
    def test_finds_a_clean_trapezoid_within_small_pixel_error(self):
        frame = _draw_trapezoid_court(KNOWN_CORNERS)
        result = _find_quad_in_frame(frame)
        assert result is not None
        corners, _ = result
        errors = np.linalg.norm(corners - np.array(KNOWN_CORNERS, dtype=np.float32), axis=1)
        assert errors.max() < 15, f"corner errors too large: {errors}"

    def test_returns_none_for_a_blank_frame(self):
        frame = np.full((720, 1280, 3), (40, 110, 40), dtype=np.uint8)
        assert _find_quad_in_frame(frame) is None

    def test_returns_none_for_pure_noise(self):
        rng = np.random.default_rng(42)
        frame = rng.integers(0, 255, size=(720, 1280, 3), dtype=np.uint8)
        # Noise can coincidentally produce short line fragments but should
        # essentially never produce a stable, correctly-sized quadrilateral.
        result = _find_quad_in_frame(frame)
        if result is not None:
            corners, _ = result
            area = cv2.contourArea(corners)
            assert not (720 * 1280 * 0.05 <= area <= 720 * 1280 * 0.97)


class TestCalibrateCourt:
    def test_success_on_consistent_clean_frames(self):
        frames = [SampledFrame(timestamp_seconds=i * 0.5, frame=_draw_trapezoid_court(KNOWN_CORNERS)) for i in range(8)]
        result = calibrate_court(frames)
        assert result.status == "SUCCESS"
        assert result.confidence == "MODERATE"  # capped — see app/court.py docstring
        assert result.homography is not None
        assert len(result.homography) == 3

    def test_confidence_is_never_above_moderate(self):
        # Even with perfect agreement across many frames, confidence must
        # stay capped — see docs/CV_ARCHITECTURE.md "Acceptance thresholds".
        frames = [SampledFrame(timestamp_seconds=i * 0.1, frame=_draw_trapezoid_court(KNOWN_CORNERS)) for i in range(20)]
        result = calibrate_court(frames)
        assert result.confidence in (None, "VERY_LOW", "LOW", "MODERATE")

    def test_not_attempted_on_no_frames(self):
        result = calibrate_court([])
        assert result.status == "NOT_ATTEMPTED"

    def test_failed_on_frames_with_no_court(self):
        blank = np.full((720, 1280, 3), (40, 110, 40), dtype=np.uint8)
        frames = [SampledFrame(timestamp_seconds=i * 0.5, frame=blank) for i in range(5)]
        result = calibrate_court(frames)
        assert result.status == "FAILED"
        assert result.confidence is None
        assert result.homography is None
        assert len(result.warnings) > 0

    def test_low_confidence_when_frames_disagree(self):
        # Different courts in different frames — no honest single calibration.
        alt_corners = [(50, 50), (200, 50), (250, 300), (10, 300)]
        frames = []
        for i in range(8):
            corners = KNOWN_CORNERS if i % 2 == 0 else alt_corners
            frames.append(SampledFrame(timestamp_seconds=i * 0.5, frame=_draw_trapezoid_court(corners)))
        result = calibrate_court(frames)
        assert result.status in ("LOW_CONFIDENCE", "PARTIAL", "FAILED")


class TestVideoPointToCourt:
    def test_maps_a_known_corner_close_to_its_real_world_position(self):
        frames = [SampledFrame(timestamp_seconds=0, frame=_draw_trapezoid_court(KNOWN_CORNERS))]
        calib = calibrate_court(frames * 8)
        assert calib.homography is not None
        # Top-left court corner should map close to (0, 0) meters.
        mapped = video_point_to_court(calib.homography, KNOWN_CORNERS[0][0], KNOWN_CORNERS[0][1])
        assert mapped is not None
        assert math.hypot(mapped[0] - 0.0, mapped[1] - 0.0) < 0.5

    def test_returns_none_for_a_point_far_outside_the_court(self):
        frames = [SampledFrame(timestamp_seconds=0, frame=_draw_trapezoid_court(KNOWN_CORNERS))]
        calib = calibrate_court(frames * 8)
        assert calib.homography is not None
        mapped = video_point_to_court(calib.homography, -5000, -5000)
        assert mapped is None
