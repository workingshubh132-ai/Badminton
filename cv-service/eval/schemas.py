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
    """Licence handling status for dataset videos.

    These are handling rules, not legal conclusions. LICENSE_REVIEW_REQUIRED is
    the default everywhere: a licence nobody has read is not a permissive one,
    and free-to-download is not the same as cleared for use.
    """

    LICENSED = "licensed"  # a human read the terms and they permit our use
    REFERENCE = "reference"  # terms read; reference/evaluation only, not distributable
    LICENSE_REVIEW_REQUIRED = "license_review_required"  # terms not read or unclear


class MatchFormatLabel(str, Enum):
    """Known match format for a source video, when it is known at all."""

    SINGLES = "singles"
    DOUBLES = "doubles"
    UNKNOWN = "unknown"


class VideoQuality(str, Enum):
    """Frame-level quality assessment during annotation."""

    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNUSABLE = "unusable"


class ParticipantStatus(str, Enum):
    """Whether an annotated person is playing on this court.

    Mirrors app.schemas.ParticipantStatus so ground truth and M5 output use one
    vocabulary. Orthogonal to PlayerIdentity: participation says "is this person
    playing", identity says "which player is this".
    """

    PARTICIPANT = "participant"
    NON_PARTICIPANT = "non_participant"
    UNKNOWN = "unknown"


class ValidationKind(str, Enum):
    """What a set of evidence actually validates.

    SYNTHETIC results come from rendered fixtures and prove only that the
    machinery computes what it claims. They are never evidence of real-world
    accuracy, and the report must never merge the two.
    """

    SYNTHETIC = "synthetic"
    REAL_WORLD = "real_world"


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

    # --- M5.5.2 manifest fields ---
    # Defaults are deliberately the conservative answer to every question, so a
    # forgotten flag under-claims rather than over-claims.
    validation_kind: ValidationKind = Field(
        default=ValidationKind.SYNTHETIC,
        description=(
            "Whether evaluating this video constitutes real-world validation. Defaults to "
            "SYNTHETIC so footage only counts as real-world when someone explicitly says so."
        ),
    )
    license_terms_url: Optional[str] = Field(
        None, description="Where the applicable licence text actually lives"
    )
    license_verified_by: Optional[str] = Field(
        None, description="Who read the licence terms. Null means nobody has."
    )
    provenance: Optional[str] = Field(
        None, description="Where this footage came from and how it was obtained"
    )
    has_burned_in_overlays: Optional[bool] = Field(
        None,
        description=(
            "True if graphics are rendered into the pixels (pose skeletons, drawn court "
            "lines, scoreboards). Such footage corrupts court evaluation. None = not checked."
        ),
    )
    match_format: MatchFormatLabel = Field(
        default=MatchFormatLabel.UNKNOWN,
        description="Known format of the recorded match, if known",
    )


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
    """An annotated person in a frame.

    A person, not necessarily a player: spectators and officials are annotated
    too, marked NON_PARTICIPANT, so participant classification can be scored
    against them.
    """

    identity: PlayerIdentity = Field(..., description="athlete | opponent | unknown")
    bbox: BoundingBox = Field(..., description="Normalized bounding box")
    # Defaults to UNKNOWN so an annotator who genuinely cannot tell is not
    # forced into a guess, and so annotations written before this field existed
    # load as "not stated" rather than silently becoming participants.
    participant: ParticipantStatus = Field(
        default=ParticipantStatus.UNKNOWN,
        description="participant | non_participant | unknown",
    )
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


class ParticipantAccuracy(BaseModel):
    """How well M5 separated court participants from bystanders.

    Scored only against people the annotator actually resolved. Annotated
    UNKNOWNs are excluded from precision/recall rather than counted as errors:
    a human who could not tell is not ground truth for either answer.
    """

    annotated_participants: int = Field(..., description="Ground-truth participants")
    annotated_non_participants: int = Field(..., description="Ground-truth bystanders")
    annotated_unknown: int = Field(default=0, description="Annotator could not resolve")

    predicted_participants: int = Field(..., description="M5 called these participants")
    predicted_non_participants: int = Field(...)
    predicted_unknown: int = Field(default=0, description="M5 could not resolve")

    true_positives: int = Field(..., description="Participant, correctly called participant")
    false_positives: int = Field(..., description="Bystander wrongly called a participant")
    false_negatives: int = Field(..., description="Participant wrongly called a bystander")

    precision: Optional[float] = Field(None, ge=0, le=1)
    recall: Optional[float] = Field(None, ge=0, le=1)
    f1: Optional[float] = Field(None, ge=0, le=1)

    # The safety-critical number: of annotated bystanders, the fraction M5
    # promoted to participants. A spectator treated as a player corrupts every
    # downstream inference, so this is tracked separately from precision.
    false_participant_rate: Optional[float] = Field(
        None, ge=0, le=1, description="Bystanders wrongly called participants / all bystanders"
    )
    # Of all resolvable people, the fraction M5 left UNKNOWN. High values mean
    # the classifier is safe but not yet useful.
    unresolved_rate: Optional[float] = Field(
        None, ge=0, le=1, description="M5 UNKNOWN / people the annotator resolved"
    )
    scored_people: int = Field(default=0, description="People contributing to precision/recall")


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
    participant_accuracy: Optional[ParticipantAccuracy] = Field(
        None, description="None when the annotation carries no participant labels"
    )
    # Carried from the source video's licence/provenance record. Determines
    # which half of the report this result may appear in.
    validation_kind: ValidationKind = Field(
        default=ValidationKind.SYNTHETIC,
        description="Whether this evaluated real footage or a rendered fixture",
    )
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
    # Kept for backward compatibility: every clip, both kinds.
    clips_evaluated: list[ClipEvaluationResult] = Field(...)
    # The two kinds of evidence, never merged. Component readiness and the
    # decision gate below are derived from real_world_clips ONLY -- synthetic
    # fixtures prove the machinery computes, never that M5 is accurate.
    real_world_clips: list[ClipEvaluationResult] = Field(default_factory=list)
    synthetic_clips: list[ClipEvaluationResult] = Field(default_factory=list)
    has_real_world_evidence: bool = Field(
        default=False, description="False means no readiness claim is supportable"
    )
    failures: list[FailureRecord] = Field(default_factory=list)
    participant_readiness: Optional[ComponentReadiness] = Field(None)
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
