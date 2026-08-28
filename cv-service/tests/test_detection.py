import numpy as np
import pytest

from app.config import PERSON_DETECTION_SCORE_THRESHOLD
from app.detection import score_to_confidence


class TestScoreToConfidence:
    def test_boundaries(self):
        assert score_to_confidence(0.9) == "HIGH"
        assert score_to_confidence(0.75) == "HIGH"
        assert score_to_confidence(0.6) == "MODERATE"
        assert score_to_confidence(0.55) == "MODERATE"
        assert score_to_confidence(0.4) == "LOW"
        assert score_to_confidence(PERSON_DETECTION_SCORE_THRESHOLD) == "LOW"
        assert score_to_confidence(0.1) == "VERY_LOW"

    def test_monotonic(self):
        scores = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        levels = ["VERY_LOW", "LOW", "MODERATE", "HIGH", "VERY_HIGH"]
        results = [score_to_confidence(s) for s in scores]
        ranks = [levels.index(r) for r in results]
        assert ranks == sorted(ranks)


@pytest.mark.integration
class TestPersonDetectorRealInference:
    """Uses a real, legitimately-licensed test image (NASA public-domain
    'astronaut' photo, bundled in the versioned scikit-image package — see
    docs/CV_ARCHITECTURE.md 'Test fixtures and the real-footage gap' for why
    this, and not a scraped web image or a synthetic shape, is used here).
    Skipped if scikit-image isn't installed (it's a dev/eval-only
    dependency, never required by the running service)."""

    def test_detects_a_person_in_a_real_photo(self, person_detector):
        skimage_data = pytest.importorskip("skimage.data")
        img_rgb = skimage_data.astronaut()
        img_bgr = img_rgb[:, :, ::-1].copy()
        detections = person_detector.detect(np.ascontiguousarray(img_bgr))
        assert len(detections) >= 1
        best = max(detections, key=lambda d: d.score)
        assert best.score > 0.5
        # The astronaut fills most of the 512x512 frame — a sane bounding
        # box should cover a large fraction of it, not a tiny false-positive
        # sliver.
        assert best.width_px > 100
        assert best.height_px > 200

    def test_detects_nothing_in_a_blank_frame(self, person_detector):
        blank = np.full((480, 640, 3), 128, dtype=np.uint8)
        detections = person_detector.detect(blank)
        assert detections == []
