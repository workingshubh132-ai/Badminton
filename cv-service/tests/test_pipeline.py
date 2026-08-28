import math
from pathlib import Path

import pytest

from app.court import calibrate_court
from app.pipeline import _enrich_with_court_coords, run_analysis
from app.preprocessing import SampledFrame
from app.schemas import BBox, Detection, PlayerTrack
from tests.test_court import KNOWN_CORNERS, _draw_trapezoid_court

FIXTURE = Path(__file__).resolve().parent.parent / "eval" / "fixtures" / "synthetic_court_01.mp4"

FRAME_W, FRAME_H = 1280, 720


class TestEnrichWithCourtCoords:
    """Fast, no-model unit test for the homography -> track enrichment step
    added in M5 (spec section 11's "plus court X/Y where calibration is
    reliable"). Uses the same known trapezoid corners as test_court.py so
    the projected court coordinates have a known-correct answer."""

    @classmethod
    @pytest.fixture(scope="class")
    def homography(cls):
        frames = [SampledFrame(timestamp_seconds=0, frame=_draw_trapezoid_court(KNOWN_CORNERS))] * 8
        calib = calibrate_court(frames)
        assert calib.homography is not None
        return calib.homography

    def test_bbox_centre_at_known_corner_maps_close_to_real_world_origin(self, homography):
        # A tiny bbox centred exactly on the known top-left court corner.
        cx, cy = KNOWN_CORNERS[0]
        bbox = BBox(x=(cx - 1) / FRAME_W, y=(cy - 1) / FRAME_H, width=2 / FRAME_W, height=2 / FRAME_H)
        det = Detection(timestamp_seconds=0.0, bbox=bbox, score=0.9, confidence="HIGH")
        track = PlayerTrack(track_id="t1", confidence="HIGH", detections=[det])

        enriched = _enrich_with_court_coords(track, homography, FRAME_W, FRAME_H)

        result_det = enriched.detections[0]
        assert result_det.court_x is not None and result_det.court_y is not None
        assert math.hypot(result_det.court_x - 0.0, result_det.court_y - 0.0) < 0.5

    def test_detection_far_off_court_stays_none_not_fabricated(self, homography):
        bbox = BBox(x=-4.0, y=-4.0, width=0.01, height=0.01)  # far outside the frame/court
        det = Detection(timestamp_seconds=0.0, bbox=bbox, score=0.9, confidence="HIGH")
        track = PlayerTrack(track_id="t1", confidence="HIGH", detections=[det])

        enriched = _enrich_with_court_coords(track, homography, FRAME_W, FRAME_H)

        assert enriched.detections[0].court_x is None
        assert enriched.detections[0].court_y is None

    def test_does_not_mutate_the_original_track(self, homography):
        bbox = BBox(x=0.4, y=0.4, width=0.05, height=0.1)
        det = Detection(timestamp_seconds=0.0, bbox=bbox, score=0.9, confidence="HIGH")
        track = PlayerTrack(track_id="t1", confidence="HIGH", detections=[det])

        _enrich_with_court_coords(track, homography, FRAME_W, FRAME_H)

        assert track.detections[0].court_x is None


@pytest.mark.integration
class TestRunAnalysisAgainstSyntheticFixture:
    """See eval/fixtures/generate_synthetic_fixture.py's docstring for
    exactly what this fixture does and does not validate — it is a
    non-photorealistic, clearly-labeled synthetic scene used to prove the
    pipeline's *geometry* (calibration math, tracking math) is implemented
    correctly, not to measure real-world accuracy."""

    @classmethod
    @pytest.fixture(scope="class")
    def result(cls, person_detector):
        if not FIXTURE.exists():
            pytest.skip(
                f"{FIXTURE} not generated — run "
                "`python eval/fixtures/generate_synthetic_fixture.py` first."
            )
        return run_analysis(
            video_path=FIXTURE,
            detector=person_detector,
            sampling_fps=2.0,
            max_sampled_frames=600,
        )

    def test_completes_without_error(self, result):
        assert result.status == "completed"

    def test_quality_is_good_for_this_clean_synthetic_video(self, result):
        assert result.quality.status == "GOOD"

    def test_court_calibration_succeeds_with_known_corners_close_to_ground_truth(self, result):
        assert result.calibration.status == "SUCCESS"
        assert result.calibration.confidence == "MODERATE"  # capped, see app/court.py
        assert result.calibration.homography is not None

    def test_no_person_tracks_since_fixture_has_no_real_human_shape(self, result):
        # Documented and expected — see module docstring. A real detector
        # correctly does NOT fire on a solid rectangle; this asserts that
        # honest behavior rather than a fabricated detection.
        assert result.tracks == []

    def test_processing_metadata_is_real_and_complete(self, result):
        meta = result.processing_metadata
        assert meta.frames_sampled > 0
        assert meta.processing_seconds > 0
        assert meta.video_checksum_sha256 and len(meta.video_checksum_sha256) == 64
        assert meta.model_versions.get("person_detector")
