"""
Real-footage evaluation runner for M5.5.

Takes annotated clips and runs the M5 pipeline against them, computing
accuracy metrics and generating visual overlays for manual inspection.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

from app.detection import PersonDetector
from app.pipeline import run_analysis
from .dataset import DatasetManager
PARTICIPANT_MATCH_IOU_THRESHOLD = 0.3
# Annotated frames and M5's sampled frames rarely land on the same instant.
PARTICIPANT_MATCH_TIME_TOLERANCE_S = 0.75

from .schemas import (
    ValidationKind,
    ParticipantStatus,
    ParticipantAccuracy,
    AnnotationMetadata,
    ClipEvaluationResult,
    CourtAccuracy,
    DetectionAccuracy,
    FailureRecord,
    FailureSeverity,
    FrameAnnotation,
    QualityAssessmentAccuracy,
    TrackingAccuracy,
)


class RealFootageEvaluator:
    """Evaluates M5 pipeline against real badminton footage."""

    def __init__(self, dataset_dir: str | Path = "cv-service/eval/datasets"):
        self.dataset = DatasetManager(dataset_dir)
        self.detector = PersonDetector()

    def close(self) -> None:
        """Clean up resources."""
        self.detector.close()

    def _quad_iou(self, a: list[list[float]], b: list[list[float]], canvas_size: tuple[int, int]) -> float:
        """IoU of two quadrilaterals via rasterization."""
        w, h = canvas_size
        mask_a = np.zeros((h, w), dtype=np.uint8)
        mask_b = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask_a, [np.array(a, dtype=np.int32)], 1)
        cv2.fillPoly(mask_b, [np.array(b, dtype=np.int32)], 1)
        intersection = np.logical_and(mask_a, mask_b).sum()
        union = np.logical_or(mask_a, mask_b).sum()
        return float(intersection / union) if union > 0 else 0.0

    def _bbox_iou(self, box1: tuple, box2: tuple) -> float:
        """IoU of two axis-aligned bboxes: (x1, y1, x2, y2)."""
        x1_a, y1_a, x2_a, y2_a = box1
        x1_b, y1_b, x2_b, y2_b = box2

        inter_x1 = max(x1_a, x1_b)
        inter_y1 = max(y1_a, y1_b)
        inter_x2 = min(x2_a, x2_b)
        inter_y2 = min(y2_a, y2_b)

        if inter_x1 >= inter_x2 or inter_y1 >= inter_y2:
            return 0.0

        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        area_a = (x2_a - x1_a) * (y2_a - y1_a)
        area_b = (x2_b - x1_b) * (y2_b - y1_b)
        union_area = area_a + area_b - inter_area

        return inter_area / union_area if union_area > 0 else 0.0

    def evaluate_clip(self, clip_id: str, sampling_fps: float = 2.0) -> ClipEvaluationResult:
        """
        Evaluate a single annotated clip.

        Args:
            clip_id: Clip to evaluate
            sampling_fps: Frame sampling rate for M5 processing

        Returns:
            ClipEvaluationResult with all metrics
        """
        # Load annotation
        annotation_data = self.dataset.load_annotation(clip_id)
        if not annotation_data:
            raise ValueError(f"No annotation found for clip {clip_id}")

        annotation = AnnotationMetadata(**annotation_data)

        # Run M5 pipeline
        clip_path = self.dataset.get_clip_path(clip_id)
        import time
        start_time = time.time()
        m5_result = run_analysis(
            video_path=clip_path,
            detector=self.detector,
            sampling_fps=sampling_fps,
            max_sampled_frames=600,
        )
        processing_seconds = time.time() - start_time

        # Evaluate court calibration
        court_accuracy = self._evaluate_court(annotation, m5_result)

        # Evaluate detection
        detection_accuracy = self._evaluate_detection(annotation, m5_result)

        # Evaluate tracking
        tracking_accuracy = self._evaluate_tracking(annotation, m5_result)

        # Evaluate quality
        quality_accuracy = self._evaluate_quality(annotation, m5_result)

        # Evaluate participant classification (M5.5.1) against annotated status.
        participant_accuracy = self._evaluate_participants(annotation, m5_result)

        # Collect failures
        failures = self._identify_failures(annotation, m5_result, court_accuracy, detection_accuracy)

        # Whether this counts as real-world validation is a property of the
        # source video's provenance, never of the evaluation run. Anything we
        # cannot confirm is real is reported as synthetic.
        clip_metadata = self.dataset.inventory["clips"].get(clip_id, {})
        source_video_id = clip_metadata.get("source_video_id", "")
        video_metadata = self.dataset.get_video_metadata(source_video_id) or {}
        validation_kind = ValidationKind(
            video_metadata.get("validation_kind", ValidationKind.SYNTHETIC.value)
        )

        result = ClipEvaluationResult(
            clip_id=clip_id,
            source_video_id=source_video_id,
            processing_seconds=processing_seconds,
            court_accuracy=court_accuracy,
            detection_accuracy=detection_accuracy,
            tracking_accuracy=tracking_accuracy,
            quality_accuracy=quality_accuracy,
            participant_accuracy=participant_accuracy,
            validation_kind=validation_kind,
        )

        # Save evaluation
        self.dataset.save_evaluation(clip_id, result.model_dump(mode="json"))

        return result

    def _evaluate_court(self, annotation: AnnotationMetadata, m5_result: Any) -> CourtAccuracy:
        """Evaluate court calibration accuracy."""
        # Find frames with annotated court
        frames_with_court = [f for f in annotation.frames if f.court_corners is not None]

        if not frames_with_court:
            return CourtAccuracy(
                attempted=m5_result.calibration.status != "unavailable",
                succeeded=False,
                status=m5_result.calibration.status,
            )

        if m5_result.calibration.court_corners_px is None:
            return CourtAccuracy(
                attempted=True,
                succeeded=False,
                status=m5_result.calibration.status,
                confidence=m5_result.calibration.confidence,
            )

        # Compute corner errors across frames with annotated court
        all_corner_errors = []
        all_ious = []

        for frame in frames_with_court:
            gt_corners = [
                frame.court_corners.top_left,
                frame.court_corners.top_right,
                frame.court_corners.bottom_right,
                frame.court_corners.bottom_left,
            ]

            detected = m5_result.calibration.court_corners_px
            errors = [
                float(np.hypot(d[0] - g[0], d[1] - g[1]))
                for d, g in zip(detected, gt_corners)
            ]
            all_corner_errors.extend(errors)

            # This is a simplification: use single detected court for all frames
            # In a real scenario, per-frame calibration could vary
            iou = self._quad_iou(
                detected,
                gt_corners,
                (1280, 720),  # Placeholder; use actual frame dimensions
            )
            all_ious.append(iou)

        mean_error = sum(all_corner_errors) / len(all_corner_errors) if all_corner_errors else None
        max_error = max(all_corner_errors) if all_corner_errors else None
        mean_iou = sum(all_ious) / len(all_ious) if all_ious else None

        return CourtAccuracy(
            attempted=True,
            succeeded=True,
            status=m5_result.calibration.status,
            confidence=m5_result.calibration.confidence,
            mean_corner_error_px=mean_error,
            max_corner_error_px=max_error,
            corner_errors_px=all_corner_errors[:10],  # Store first 10 for reference
            iou_with_ground_truth=mean_iou,
            homography_succeeded=m5_result.calibration.homography is not None,
        )

    def _evaluate_detection(self, annotation: AnnotationMetadata, m5_result: Any) -> DetectionAccuracy:
        """Evaluate player detection accuracy."""
        # Count total annotated players across frames
        total_gt_players = sum(len(f.players) for f in annotation.frames)
        total_detected = sum(len(t.detections) for t in m5_result.tracks)

        if total_gt_players == 0:
            return DetectionAccuracy(
                ground_truth_count=0,
                detected_count=total_detected,
                true_positives=0,
                false_positives=total_detected,
                false_negatives=0,
                precision=0.0 if total_detected > 0 else None,
                recall=None,
            )

        # Simplified: count detections vs annotations
        # Full implementation would match detections frame-by-frame
        tp = min(total_gt_players, total_detected)
        fp = max(0, total_detected - total_gt_players)
        fn = max(0, total_gt_players - total_detected)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        return DetectionAccuracy(
            ground_truth_count=total_gt_players,
            detected_count=total_detected,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            mean_iou=None,  # Would require per-frame bbox matching
        )

    def _evaluate_participants(
        self, annotation: AnnotationMetadata, m5_result: Any
    ) -> Optional[ParticipantAccuracy]:
        """Score M5's participant classification against annotated ground truth.

        Each annotated person is matched to an M5 detection spatially (best IoU at
        the nearest sampled timestamp), and the two participant verdicts compared.

        People the annotator left UNKNOWN are excluded from precision/recall: a
        human who could not tell is not ground truth for either answer. M5's own
        UNKNOWNs are kept, counted as neither TP nor FP, and surfaced separately
        as unresolved_rate -- treating "I don't know" as a wrong answer would
        reward a classifier that guesses.
        """
        annotated = [
            (frame, player)
            for frame in annotation.frames
            for player in frame.players
        ]
        if not annotated:
            return None
        if all(p.participant == ParticipantStatus.UNKNOWN for _, p in annotated):
            # No resolved labels anywhere: nothing to score against.
            return None

        gt_participants = sum(1 for _, p in annotated if p.participant == ParticipantStatus.PARTICIPANT)
        gt_non = sum(1 for _, p in annotated if p.participant == ParticipantStatus.NON_PARTICIPANT)
        gt_unknown = sum(1 for _, p in annotated if p.participant == ParticipantStatus.UNKNOWN)

        tp = fp = fn = 0
        predicted_participant = predicted_non = predicted_unknown = 0
        scored = 0
        false_participants = 0

        for frame, player in annotated:
            if player.participant == ParticipantStatus.UNKNOWN:
                continue
            scored += 1
            predicted = self._match_track_status(frame, player, m5_result)

            if predicted == "PARTICIPANT":
                predicted_participant += 1
            elif predicted == "NON_PARTICIPANT":
                predicted_non += 1
            else:
                predicted_unknown += 1

            if player.participant == ParticipantStatus.PARTICIPANT:
                if predicted == "PARTICIPANT":
                    tp += 1
                elif predicted == "NON_PARTICIPANT":
                    fn += 1
            else:  # annotated NON_PARTICIPANT
                if predicted == "PARTICIPANT":
                    fp += 1
                    false_participants += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else None
        recall = tp / (tp + fn) if (tp + fn) > 0 else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and (precision + recall) > 0
            else None
        )

        return ParticipantAccuracy(
            annotated_participants=gt_participants,
            annotated_non_participants=gt_non,
            annotated_unknown=gt_unknown,
            predicted_participants=predicted_participant,
            predicted_non_participants=predicted_non,
            predicted_unknown=predicted_unknown,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1=f1,
            false_participant_rate=(false_participants / gt_non) if gt_non else None,
            unresolved_rate=(predicted_unknown / scored) if scored else None,
            scored_people=scored,
        )

    def _match_track_status(self, frame, player, m5_result: Any) -> str:
        """Participant status M5 assigned to whichever track best overlaps this
        annotated person. Returns UNKNOWN when nothing matches well enough --
        an unmatched person is unresolved, not a bystander."""
        gt_box = (player.bbox.x1, player.bbox.y1, player.bbox.x2, player.bbox.y2)
        best_iou, best_status = 0.0, "UNKNOWN"

        for track in m5_result.tracks:
            if not track.detections:
                continue
            nearest = min(
                track.detections,
                key=lambda d: abs(d.timestamp_seconds - frame.timestamp_seconds),
            )
            if abs(nearest.timestamp_seconds - frame.timestamp_seconds) > PARTICIPANT_MATCH_TIME_TOLERANCE_S:
                continue
            candidate = (
                nearest.bbox.x,
                nearest.bbox.y,
                nearest.bbox.x + nearest.bbox.width,
                nearest.bbox.y + nearest.bbox.height,
            )
            iou = self._bbox_iou(gt_box, candidate)
            if iou > best_iou:
                best_iou = iou
                best_status = (
                    track.participant.status if track.participant is not None else "UNKNOWN"
                )

        return best_status if best_iou >= PARTICIPANT_MATCH_IOU_THRESHOLD else "UNKNOWN"

    def _evaluate_tracking(self, annotation: AnnotationMetadata, m5_result: Any) -> TrackingAccuracy:
        """Evaluate player tracking accuracy."""
        return TrackingAccuracy(
            tracks_found=len(m5_result.tracks),
            mean_track_length=sum(len(t.detections) for t in m5_result.tracks) / len(m5_result.tracks)
            if m5_result.tracks
            else 0.0,
            identity_consistency=None,  # Would require frame-by-frame identity comparison
            identity_switches=0,  # Requires tracking ID continuity analysis
        )

    def _evaluate_quality(self, annotation: AnnotationMetadata, m5_result: Any) -> QualityAssessmentAccuracy:
        """Evaluate video quality classification accuracy."""
        # Compare M5's quality classification with annotated frame quality
        m5_status = m5_result.quality.status

        # Map M5 status to annotation quality categories
        m5_to_quality = {
            "GOOD": "good",
            "ACCEPTABLE": "acceptable",
            "POOR": "poor",
            "UNUSABLE": "unusable",
        }
        m5_quality_category = m5_to_quality.get(m5_status, "poor")

        # Count matches
        total_annotated = len(annotation.frames)
        if total_annotated == 0:
            return QualityAssessmentAccuracy(
                correct_classifications=0,
                total_frames=0,
                accuracy=None,
            )

        # Simplified: all frames get M5's single quality classification
        # Real implementation: per-frame quality prediction
        correct = sum(1 for f in annotation.frames if f.quality.value == m5_quality_category)

        return QualityAssessmentAccuracy(
            correct_classifications=correct,
            total_frames=total_annotated,
            accuracy=correct / total_annotated if total_annotated > 0 else 0.0,
        )

    def _identify_failures(
        self,
        annotation: AnnotationMetadata,
        m5_result: Any,
        court_accuracy: CourtAccuracy,
        detection_accuracy: DetectionAccuracy,
    ) -> list[FailureRecord]:
        """Identify important failures during evaluation."""
        failures = []

        # Court detection failure
        if not court_accuracy.succeeded and court_accuracy.attempted:
            failures.append(
                FailureRecord(
                    timestamp_in_clip_seconds=0.0,
                    component="COURT_DETECTION",
                    description="Court calibration failed",
                    likely_cause="Could not find clear court boundaries",
                    severity=FailureSeverity.HIGH,
                    affected_frames=len(annotation.frames),
                )
            )

        # Detection miss
        if detection_accuracy.false_negatives > 0:
            failures.append(
                FailureRecord(
                    timestamp_in_clip_seconds=0.0,
                    component="PLAYER_DETECTION",
                    description=f"Missed {detection_accuracy.false_negatives} players",
                    likely_cause="Person detector confidence below threshold",
                    severity=FailureSeverity.MEDIUM if detection_accuracy.false_negatives == 1 else FailureSeverity.HIGH,
                    affected_frames=detection_accuracy.false_negatives,
                )
            )

        # False positives
        if detection_accuracy.false_positives > 0:
            failures.append(
                FailureRecord(
                    timestamp_in_clip_seconds=0.0,
                    component="PLAYER_DETECTION",
                    description=f"Generated {detection_accuracy.false_positives} false detections",
                    likely_cause="Background elements misclassified as persons",
                    severity=FailureSeverity.LOW,
                    affected_frames=detection_accuracy.false_positives,
                )
            )

        return failures


def main() -> None:
    """CLI for evaluating annotated clips."""
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate an annotated clip against M5 pipeline.")
    parser.add_argument("clip_id", help="Clip ID to evaluate")
    parser.add_argument(
        "--dataset-dir",
        default="cv-service/eval/datasets",
        help="Dataset root directory",
    )
    parser.add_argument(
        "--sampling-fps",
        type=float,
        default=2.0,
        help="Frame sampling rate for M5 processing",
    )

    args = parser.parse_args()

    evaluator = RealFootageEvaluator(args.dataset_dir)
    try:
        print(f"Evaluating clip: {args.clip_id}")
        result = evaluator.evaluate_clip(args.clip_id, sampling_fps=args.sampling_fps)

        print(f"\n{'=' * 70}")
        print(f"EVALUATION RESULT: {args.clip_id}")
        print(f"{'=' * 70}")
        print(f"Processing time: {result.processing_seconds:.2f}s")

        print(f"\nCourt Calibration:")
        print(f"  Attempted: {result.court_accuracy.attempted}")
        print(f"  Succeeded: {result.court_accuracy.succeeded}")
        if result.court_accuracy.mean_corner_error_px is not None:
            print(f"  Mean corner error: {result.court_accuracy.mean_corner_error_px:.2f}px")
            print(f"  Max corner error: {result.court_accuracy.max_corner_error_px:.2f}px")
            print(f"  IoU: {result.court_accuracy.iou_with_ground_truth:.4f}")

        print(f"\nPlayer Detection:")
        print(f"  Ground truth: {result.detection_accuracy.ground_truth_count}")
        print(f"  Detected: {result.detection_accuracy.detected_count}")
        print(f"  Precision: {result.detection_accuracy.precision:.2%}")
        print(f"  Recall: {result.detection_accuracy.recall:.2%}")

        print(f"\nPlayer Tracking:")
        print(f"  Tracks found: {result.tracking_accuracy.tracks_found}")
        print(f"  Mean track length: {result.tracking_accuracy.mean_track_length:.1f} frames")

        if result.participant_accuracy:
            pa = result.participant_accuracy

            def pct(value):
                return "n/a" if value is None else f"{value:.2%}"

            print(f"\nParticipant Classification:")
            print(f"  Annotated: {pa.annotated_participants} participant(s), "
                  f"{pa.annotated_non_participants} bystander(s), {pa.annotated_unknown} unknown")
            print(f"  Precision: {pct(pa.precision)}   Recall: {pct(pa.recall)}")
            print(f"  False-participant rate: {pct(pa.false_participant_rate)}")
            print(f"  Unresolved rate:        {pct(pa.unresolved_rate)}")
        else:
            print(f"\nParticipant Classification: not scored "
                  f"(annotation carries no resolved participant labels)")

        print(f"\nValidation kind: {result.validation_kind.value.upper()}")
        if result.validation_kind.value == "synthetic":
            print(f"  Machinery verification only — NOT real-world validation.")

        print(f"\nQuality Assessment:")
        print(f"  Accuracy: {result.quality_accuracy.accuracy:.2%}")
        print(f"  ({result.quality_accuracy.correct_classifications}/{result.quality_accuracy.total_frames} correct)")

        print(f"\n{'=' * 70}")
        print(f"Evaluation saved.")
        print(f"{'=' * 70}")
    finally:
        evaluator.close()


if __name__ == "__main__":
    main()
