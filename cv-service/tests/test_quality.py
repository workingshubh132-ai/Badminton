import numpy as np

from app.preprocessing import SampledFrame
from app.quality import assess_quality, is_blank_frame
from app.schemas import VideoInfo


def _frame(color=(80, 140, 80), size=(720, 1280)) -> np.ndarray:
    return np.full((*size, 3), color, dtype=np.uint8)


def _textured_frame(size=(720, 1280), seed=1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 255, size=(*size, 3), dtype=np.uint8)


class TestIsBlankFrame:
    def test_solid_color_is_blank(self):
        assert is_blank_frame(_frame()) is True

    def test_textured_frame_is_not_blank(self):
        assert is_blank_frame(_textured_frame()) is False


class TestAssessQuality:
    def test_unusable_when_duration_is_missing(self):
        video = VideoInfo(width=1920, height=1080, fps=30, duration_seconds=None)
        result = assess_quality(video, [SampledFrame(0, _textured_frame())], 10)
        assert result.status == "UNUSABLE"

    def test_unusable_when_no_frames_decoded(self):
        video = VideoInfo(width=1920, height=1080, fps=30, duration_seconds=10)
        result = assess_quality(video, [], 10)
        assert result.status == "UNUSABLE"

    def test_good_for_high_resolution_high_fps_textured_video(self):
        video = VideoInfo(width=1920, height=1080, fps=30, duration_seconds=10)
        frames = [SampledFrame(i, _textured_frame(seed=i)) for i in range(10)]
        result = assess_quality(video, frames, 10)
        assert result.status == "GOOD"
        assert result.metrics["blank_frame_ratio"] == 0.0

    def test_poor_for_low_resolution(self):
        video = VideoInfo(width=320, height=240, fps=30, duration_seconds=10)
        frames = [SampledFrame(i, _textured_frame(seed=i)) for i in range(10)]
        result = assess_quality(video, frames, 10)
        assert result.status in ("POOR", "UNUSABLE")
        assert any("Resolution" in r for r in result.reasons)

    def test_flags_high_blank_frame_ratio(self):
        video = VideoInfo(width=1920, height=1080, fps=30, duration_seconds=10)
        frames = [SampledFrame(i, _frame()) for i in range(10)]  # all blank
        result = assess_quality(video, frames, 10)
        assert result.metrics["blank_frame_ratio"] == 1.0
        assert result.status in ("POOR", "UNUSABLE")

    def test_flags_decode_failures(self):
        video = VideoInfo(width=1920, height=1080, fps=30, duration_seconds=10)
        frames = [SampledFrame(i, _textured_frame(seed=i)) for i in range(3)]
        result = assess_quality(video, frames, requested_frame_count=20)
        assert result.metrics["decode_failure_ratio"] > 0.5

    def test_metrics_are_real_measured_values_not_placeholders(self):
        video = VideoInfo(width=1920, height=1080, fps=30, duration_seconds=10)
        frames = [SampledFrame(i, _textured_frame(seed=i)) for i in range(10)]
        result = assess_quality(video, frames, 10)
        assert result.metrics["resolution"] == "1920x1080"
        assert result.metrics["sampled_frame_count"] == 10
