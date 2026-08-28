"""
Person detection via MediaPipe Tasks ObjectDetector + EfficientDet-Lite0
(COCO-pretrained, "person" class only). See docs/CV_ARCHITECTURE.md "Model
selection" for why this model was chosen (license, size, CPU speed,
accuracy trade-off) over alternatives.

The detector is loaded once per process (model load is the expensive part;
inference itself is ~90ms/frame on a 4-CPU sandbox in verified testing) and
reused across every frame in a video.
"""

from __future__ import annotations

from dataclasses import dataclass

import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from app.config import PERSON_DETECTION_SCORE_THRESHOLD, PERSON_DETECTOR_MODEL_PATH
from app.schemas import ConfidenceLevel


@dataclass
class RawDetection:
    x_px: float
    y_px: float
    width_px: float
    height_px: float
    score: float


def score_to_confidence(score: float) -> ConfidenceLevel:
    # A direct, documented mapping from the model's own score — not an
    # independent judgment. See docs/CV_ARCHITECTURE.md "Confidence model".
    if score >= 0.75:
        return "HIGH"
    if score >= 0.55:
        return "MODERATE"
    if score >= PERSON_DETECTION_SCORE_THRESHOLD:
        return "LOW"
    return "VERY_LOW"


class PersonDetector:
    def __init__(self) -> None:
        if not PERSON_DETECTOR_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Person-detection model not found at {PERSON_DETECTOR_MODEL_PATH}. "
                "See cv-service/README.md 'Setup' to download it."
            )
        base_options = mp_python.BaseOptions(model_asset_path=str(PERSON_DETECTOR_MODEL_PATH))
        options = mp_vision.ObjectDetectorOptions(
            base_options=base_options,
            score_threshold=PERSON_DETECTION_SCORE_THRESHOLD,
            category_allowlist=["person"],
            max_results=10,
        )
        self._detector = mp_vision.ObjectDetector.create_from_options(options)

    def detect(self, frame_bgr: np.ndarray) -> list[RawDetection]:
        # MediaPipe expects RGB; OpenCV decodes BGR.
        rgb = frame_bgr[:, :, ::-1]
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        result = self._detector.detect(mp_image)
        detections: list[RawDetection] = []
        for d in result.detections:
            if not d.categories:
                continue
            category = d.categories[0]
            if category.category_name != "person":
                continue
            bb = d.bounding_box
            detections.append(
                RawDetection(
                    x_px=float(bb.origin_x),
                    y_px=float(bb.origin_y),
                    width_px=float(bb.width),
                    height_px=float(bb.height),
                    score=float(category.score),
                )
            )
        return detections

    def close(self) -> None:
        self._detector.close()
