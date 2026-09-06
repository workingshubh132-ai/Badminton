"""
Dataset and annotation schemas for M5.5 real-footage validation.

M5.5 evaluates the existing M5 perception pipeline on real badminton footage.
This module defines the schema for videos, clips, annotations, and evaluation results.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class LicenseType(str, Enum):
    """License status for dataset videos."""

    LICENSED = "licensed"  # we have explicit permission to use/retain
    REFERENCE = "reference"  # elite/research footage, reference only, not distributable


class VideoQuality(str, Enum):
    """Frame-level quality assessment during annotation."""

    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNUSABLE = "unusable"


class PlayerIdentity(str, Enum):
    """Player identity labels in annotations."""

    ATHLETE = "athlete"
    OPPONENT = "opponent"
    UNKNOWN = "unknown"


class ComponentStatus(str, Enum):
    """M5.5 readiness classification for each component."""

    PRODUCTION_READY = "production_ready"
    VALIDATION_READY = "validation_ready"
    NEEDS_IMPROVEMENT = "needs_improvement"
    UNRELIABLE = "unreliable"


class FailureSeverity(str, Enum):
    """Failure severity for analysis."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============================================================================
# DATASET INVENTORY
# ============================================================================


class VideoMetadata(BaseModel):
    """Metadata about a source video."""

    video_id: str = Field(..., description="Unique identifier for this video")
    filename: str = Field(..., description="Original filename")
    license: LicenseType = Field(..., description="License type (LICENSED or REFERENCE)")
    source_url: Optional[str] = Field(
        None, description="URL where video was sourced (for reference)"
    )
    source_description: Optional[str] = Field(None, description="How/where video was obtained")
    camera_description: Optional[str] = Field(None, description="Camera type/view angle")
    players_named: Optional[list[str]] = Field(
        None, description="Known player names (if identifiable)"
    )
    duration_seconds: float = Field(..., description="Total video duration in seconds")
    width: int = Field(..., description="Frame width in pixels")
    height: int = Field(..., description="Frame height in pixels")
    fps: float = Field(..., description="Frames per second")
    codec: Optional[str] = Field(None, description="Video codec")
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(None, description="Annotator notes")


class ClipMetadata(BaseModel):
    """Metadata about a clipped evaluation clip."""

    clip_id: str = Field(..., description="Unique identifier for this clip")
    source_video_id: str = Field(..., description="Parent video ID")
    start_seconds: float = Field(..., description="Clip start time in seconds")
    end_seconds: float = Field(..., description="Clip end time in seconds")
    camera_view: Optional[str] = Field(None, description="Camera angle/view for this clip")
    court_visible: bool = Field(..., description="Is court fully visible?")
    players_visible: int = Field(..., description="Number of players visible (0, 1, or 2)")
    annotation_status: str = Field(
        default="pending", description="pending | in_progress | complete"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(None, description="Clip-specific notes")


# ============================================================================
# FRAME-LEVEL ANNOTATIONS
# ============================================================================


class BoundingBox(BaseModel):
    """Normalized bounding box [x1, y1, x2, y2] in [0, 1] range."""

    x1: float = Field(..., ge=0, le=1)
    y1: float = Field(..., ge=0, le=1)
    x2: float = Field(..., ge=0, le=1)
    y2: float = Field(..., ge=0, le=1)

    def to_pixel_coords(self, width: int, height: int) -> tuple[float, float, float, float]:
        """Convert to pixel coordinates."""
        return (
            self.x1 * width,
            self.y1 * height,
            self.x2 * width,
            self.y2 * height,
        )

    @classmethod
    def from_pixels(
        cls, x1: float, y1: float, x2: float, y2: float, width: int, height: int
    ) -> BoundingBox:
        """Create from pixel coordinates."""
        return cls(x1=x1 / width, y1=y1 / height, x2=x2 / width, y2=y2 / height)


class CourtCorners(BaseModel):
    """Four court corners in normalized coordinates."""

    top_left: tuple[float, float] = Field(..., description="[x, y]")
    top_right: tuple[float, float]
    bottom_right: tuple[float, float]
    bottom_left: tuple[float, float]

    def to_pixel_coords(self, width: int, height: int) -> dict[str, tuple[float, float]]:
        """Convert all corners to pixel coordinates."""
        return {
            "top_left": (self.top_left[0] * width, self.top_left[1] * height),
            "top_right": (self.top_right[0] * width, self.top_right[1] * height),
            "bottom_right": (self.bottom_right[0] * width, self.bottom_right[1] * height),
            "bottom_left": (self.bottom_left[0] * width, self.bottom_left[1] * height),
        }

    @classmethod
    def from_pixels(
        cls,
        top_left: tuple[float, float],
        top_right: tuple[float, float],
        bottom_right: tuple[float, float],
        bottom_left: tuple[float, float],
        width: int,
        height: int,
    ) -> CourtCorners:
        """Create from pixel coordinates."""
        return cls(
            top_left=(top_left[0] / width, top_left[1] / height),
            top_right=(top_right[0] / width, top_right[1] / height),
            bottom_right=(bottom_right[0] / width, bottom_right[1] / height),
            bottom_left=(bottom_left[0] / width, bottom_left[1] / height),
        )


class PlayerAnnotation(BaseModel):
    """Annotated player in a frame."""

    identity: PlayerIdentity = Field(..., description="athlete | opponent | unknown")
    bbox: BoundingBox = Field(..., description="Normalized bounding box")
    confidence: Optional[float] = Field(
        None, ge=0, le=1, description="Annotator confidence in identity"
    )


class FrameAnnotation(BaseModel):
    """Ground-truth annotation for a single frame."""

    frame_index: int = Field(..., description="Frame number in clip (0-indexed)")
    timestamp_seconds: float = Field(..., description="Seconds from clip start")
    quality: VideoQuality = Field(..., description="Frame quality assessment")
    court_corners: Optional[CourtCorners] = Field(None, description="Court corners if visible")
    players: list[PlayerAnnotation] = Field(default_factory=list, description="Annotated players")
    annotator_notes: Optional[str] = Field(None, description="Annotator notes")


class AnnotationMetadata(BaseModel):
    """Metadata for an annotation session."""

    version: str = Field(default="1.0", description="Annotation format version")
    clip_id: str = Field(..., description="Which clip was annotated")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    annotator: Optional[str] = Field(None, description="Who annotated this")
    frames: list[FrameAnnotation] = Field(
        default_factory=list, description="Per-frame annotations"
    )


# ============================================================================
# EVALUATION RESULTS
# ============================================================================


class CourtAccuracy(BaseModel):
    """Court detection accuracy metrics."""

    attempted: bool = Field(..., description="Was court detection attempted?")
    succeeded: bool = Field(..., description="Did it find a court?")
    status: str = Field(..., description="GOOD | ACCEPTABLE | POOR | etc")
    confidence: Optional[str] = Field(None, description="Confidence level")
    mean_corner_error_px: Optional[float] = Field(None, description="Mean corner error in pixels")
    max_corner_error_px: Optional[float] = Field(None, description="Max corner error in pixels")
    corner_errors_px: list[float] = Field(
        default_factory=list, description="Per-corner errors"
    )
    iou_with_ground_truth: Optional[float] = Field(None, description="IoU vs annotated court")
    homography_succeeded: Optional[bool] = Field(
        None, description="Did homography calculation succeed?"
    )


class DetectionAccuracy(BaseModel):
    """Player detection accuracy metrics."""

    ground_truth_count: int = Field(..., description="Number of annotated players")
    detected_count: int = Field(..., description="Number detected by M5")
    true_positives: int = Field(...)
    false_positives: int = Field(...)
    false_negatives: int = Field(...)
    precision: Optional[float] = Field(None, ge=0, le=1)
    recall: Optional[float] = Field(None, ge=0, le=1)
    mean_iou: Optional[float] = Field(None, ge=0, le=1)


class TrackingAccuracy(BaseModel):
    """Player tracking accuracy metrics."""

    tracks_found: int = Field(...)
    mean_track_length: Optional[float] = Field(None)
    identity_consistency: Optional[float] = Field(None, description="% frames with correct identity")
    identity_switches: int = Field(default=0, description="Number of tracking ID switches")
    gaps_observed: int = Field(default=0, description="Number of tracking gaps")
    mean_gap_duration_frames: Optional[float] = Field(None)
    max_gap_duration_frames: Optional[int] = Field(None)


class QualityAssessmentAccuracy(BaseModel):
    """Video quality classification accuracy."""

    correct_classifications: int = Field(...)
    total_frames: int = Field(...)
    accuracy: Optional[float] = Field(None, ge=0, le=1)
    confusion_matrix: dict[str, dict[str, int]] = Field(
        default_factory=dict, description="Predicted vs actual for each quality level"
    )


class ClipEvaluationResult(BaseModel):
    """Complete evaluation result for one clip."""

    clip_id: str = Field(...)
    source_video_id: str = Field(...)
    evaluation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_seconds: float = Field(..., description="Time to run M5 pipeline")
    court_accuracy: CourtAccuracy = Field(...)
    detection_accuracy: DetectionAccuracy = Field(...)
    tracking_accuracy: TrackingAccuracy = Field(...)
    quality_accuracy: QualityAssessmentAccuracy = Field(...)
    notes: Optional[str] = Field(None)


# ============================================================================
# FAILURE ANALYSIS
# ============================================================================


class FailureRecord(BaseModel):
    """A recorded failure during evaluation."""

    timestamp_in_clip_seconds: float = Field(...)
    component: str = Field(..., description="COURT_DETECTION | PLAYER_DETECTION | TRACKING | QUALITY")
    description: str = Field(..., description="What happened")
    likely_cause: Optional[str] = Field(None)
    severity: FailureSeverity = Field(...)
    suggested_fix: Optional[str] = Field(None)
    affected_frames: int = Field(default=1)


# ============================================================================
# AGGREGATE REPORT
# ============================================================================


class ComponentReadiness(BaseModel):
    """Readiness classification for one component."""

    component: str = Field(...)
    status: ComponentStatus = Field(...)
    metric_summary: dict[str, Any] = Field(
        default_factory=dict, description="Key metrics supporting this classification"
    )
    reasoning: str = Field(..., description="Why this classification")
    critical_issues: list[str] = Field(default_factory=list)
    recommended_improvements: list[str] = Field(default_factory=list)


class EvaluationReport(BaseModel):
    """Complete M5.5 evaluation report."""

    version: str = Field(default="1.0")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    dataset_name: Optional[str] = Field(None)
    clips_evaluated: list[ClipEvaluationResult] = Field(...)
    failures: list[FailureRecord] = Field(default_factory=list)
    court_readiness: ComponentReadiness = Field(...)
    detection_readiness: ComponentReadiness = Field(...)
    tracking_readiness: ComponentReadiness = Field(...)
    quality_readiness: ComponentReadiness = Field(...)
    decision_gate: str = Field(
        ...,
        description="A | B | C | D | E | F (see M5.5 spec)",
    )
    decision_rationale: str = Field(...)
    summary_metrics: dict[str, Any] = Field(default_factory=dict)
