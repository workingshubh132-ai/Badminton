"""
The CV output contract (spec M5 section 14). Every field here is either a
real, computed value or an honest null/empty — nothing is a placeholder.
Keep this extensible: pose/shuttle/racket/shot/movement/rally are future
optional sections, never forced into today's shape.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ConfidenceLevel = Literal["VERY_LOW", "LOW", "MODERATE", "HIGH", "VERY_HIGH"]
QualityStatus = Literal["GOOD", "ACCEPTABLE", "POOR", "UNUSABLE"]
CalibrationStatus = Literal["NOT_ATTEMPTED", "SUCCESS", "PARTIAL", "FAILED", "LOW_CONFIDENCE"]
PlayerIdentity = Literal["ATHLETE", "OPPONENT", "UNKNOWN"]
EngineStatus = Literal["completed", "failed", "unavailable"]


class VideoInfo(BaseModel):
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    frame_count: Optional[int] = None
    duration_seconds: Optional[float] = None
    codec: Optional[str] = None


class QualityAssessment(BaseModel):
    status: QualityStatus
    reasons: list[str] = Field(default_factory=list)
    # Every value here is something actually measured — see app/quality.py.
    metrics: dict = Field(default_factory=dict)


class BBox(BaseModel):
    """Normalized 0-1 image-space box, resolution-independent."""

    x: float
    y: float
    width: float
    height: float


class Detection(BaseModel):
    timestamp_seconds: float
    bbox: BBox
    score: float
    confidence: ConfidenceLevel
    # Real-world court meters for this detection's bbox *centre* (spec M5
    # section 11's documented proxy — not the feet/contact point), populated
    # only when a homography was actually available for this run. Null,
    # never guessed, when calibration didn't succeed.
    court_x: Optional[float] = None
    court_y: Optional[float] = None


class TrackingGap(BaseModel):
    start_seconds: float
    end_seconds: float
    reason: str


class PlayerTrack(BaseModel):
    track_id: str
    # Identity is never guessed server-side — see app/tracking.py. Every
    # track starts UNKNOWN; a human confirms ATHLETE/OPPONENT in the UI.
    identity: PlayerIdentity = "UNKNOWN"
    identity_source: Literal["HEURISTIC", "USER_CONFIRMED"] = "HEURISTIC"
    confidence: ConfidenceLevel
    detections: list[Detection]
    gaps: list[TrackingGap] = Field(default_factory=list)


class CourtCalibration(BaseModel):
    status: CalibrationStatus
    confidence: Optional[ConfidenceLevel] = None
    # 3x3 homography mapping video-pixel court corners to real-world court
    # meters (0,0)-(6.1,13.4), doubles boundary. Only set on SUCCESS/PARTIAL.
    homography: Optional[list[list[float]]] = None
    # The 4 detected corners in video-pixel space, in the same order used to
    # compute the homography (top-left, top-right, bottom-right, bottom-left).
    court_corners_px: Optional[list[list[float]]] = None
    source_frame_timestamps: list[float] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProcessingMetadata(BaseModel):
    engine_name: str
    engine_version: str
    model_versions: dict[str, str] = Field(default_factory=dict)
    sampling_fps: float
    frames_sampled: int
    processing_seconds: float
    config: dict = Field(default_factory=dict)
    video_checksum_sha256: Optional[str] = None


class AnalysisResult(BaseModel):
    status: EngineStatus
    message: Optional[str] = None
    video: VideoInfo
    quality: QualityAssessment
    calibration: CourtCalibration
    tracks: list[PlayerTrack] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    processing_metadata: ProcessingMetadata


class AnalyzeRequest(BaseModel):
    video_id: str
    # Absolute path on the shared local filesystem — see
    # docs/CV_ARCHITECTURE.md "Deployment" for why this is a documented
    # single-host assumption, not a multi-host-ready design.
    video_path: str
    sampling_fps: float = 2.0
    max_sampled_frames: int = 600
