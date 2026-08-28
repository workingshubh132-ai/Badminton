import type {
  AssessmentStatus,
  CalibrationStatus,
  ConfidenceLevel,
  EvidenceSource,
  GoalCategory,
  GoalPriority,
  GoalStatus,
  MatchResult,
  MatchStatus,
  PlayerIdentity,
  QualityStatus,
  SkillCategory,
  SkillLevel,
  Trend,
  VideoJobStatus,
  VideoJobType,
  VideoStatus,
  VideoType,
} from "@/generated/prisma/client";

export const confidenceLabel: Record<ConfidenceLevel, string> = {
  VERY_LOW: "Very low confidence",
  LOW: "Low confidence",
  MODERATE: "Moderate confidence",
  HIGH: "High confidence",
  VERY_HIGH: "Very high confidence",
};

export const confidenceTone: Record<ConfidenceLevel, "danger" | "warning" | "neutral" | "info" | "success"> = {
  VERY_LOW: "danger",
  LOW: "warning",
  MODERATE: "neutral",
  HIGH: "info",
  VERY_HIGH: "success",
};

export const skillLevelLabel: Record<SkillLevel, string> = {
  EMERGING: "Emerging",
  DEVELOPING: "Developing",
  SOLID: "Solid",
  STRONG: "Strong",
  ADVANCED: "Advanced",
};

export const trendLabel: Record<Trend, string> = {
  IMPROVING: "Improving",
  STABLE: "Stable",
  DECLINING: "Declining",
  UNKNOWN: "Trend unknown",
};

export const trendTone: Record<Trend, "success" | "neutral" | "danger" | "warning"> = {
  IMPROVING: "success",
  STABLE: "neutral",
  DECLINING: "danger",
  UNKNOWN: "warning",
};

export const assessmentStatusLabel: Record<AssessmentStatus, string> = {
  PROVISIONAL: "Provisional",
  CONFIRMED: "Confirmed",
};

export const skillCategoryLabel: Record<SkillCategory, string> = {
  TECHNICAL: "Technical",
  MOVEMENT: "Movement",
  TACTICAL: "Tactical",
  PHYSICAL: "Physical",
  MENTAL: "Mental / Competitive",
};

export const goalCategoryLabel: Record<GoalCategory, string> = {
  TECHNICAL: "Technical",
  MOVEMENT: "Movement",
  TACTICAL: "Tactical",
  PHYSICAL: "Physical",
  MENTAL: "Mental",
  COMPETITION: "Competition",
};

export const goalPriorityLabel: Record<GoalPriority, string> = {
  LOW: "Low priority",
  MEDIUM: "Medium priority",
  HIGH: "High priority",
};

export const goalStatusLabel: Record<GoalStatus, string> = {
  ACTIVE: "Active",
  ACHIEVED: "Achieved",
  ABANDONED: "Abandoned",
};

export const competitiveLevelLabel: Record<string, string> = {
  BEGINNER: "Beginner",
  INTERMEDIATE: "Intermediate",
  CLUB_COMPETITIVE: "Club competitive",
  DISTRICT_OR_STATE_COMPETITIVE: "District / State competitive",
  NATIONAL_COMPETITIVE: "National competitive",
  INTERNATIONAL_ASPIRANT: "International aspirant",
};

export const videoTypeLabel: Record<VideoType, string> = {
  MATCH: "Match",
  TRAINING: "Training",
  TECHNIQUE: "Technique",
  OTHER: "Other",
};

// Copy mirrors spec section 15 ("Analysis Status Experience") — every
// status must be understandable and, where nothing has happened yet, must
// say so honestly rather than implying progress.
export const videoStatusLabel: Record<VideoStatus, string> = {
  UPLOAD_PENDING: "Upload starting…",
  UPLOADING: "Uploading…",
  UPLOADED: "Uploaded — video is safely stored",
  VALIDATING: "Checking video format and quality…",
  VALID: "Valid",
  INVALID: "Invalid — could not be processed",
  PROCESSING: "Extracting video details…",
  READY_FOR_ANALYSIS: "Ready for analysis",
  ANALYZING: "Analysis in progress…",
  ANALYZED: "Analysis complete",
  FAILED: "Something went wrong processing this video",
  DELETED: "Deleted",
};

// Longer, honest explanation shown on the video detail page — see spec
// section 15's worked examples ("Video is safely stored.", "CV analysis is
// not yet available for this video.").
export const videoStatusExplanation: Record<VideoStatus, string> = {
  UPLOAD_PENDING: "Preparing to receive this video.",
  UPLOADING: "Your video is uploading. Keep this page open.",
  UPLOADED: "Video is safely stored and about to be checked.",
  VALIDATING: "Checking that this file is a readable video and within size limits.",
  VALID: "Passed format checks.",
  INVALID: "This file could not be processed. Delete it and try re-uploading — often re-exporting as MP4 (H.264) fixes it.",
  PROCESSING: "Extracting duration, dimensions, and other details from the video.",
  READY_FOR_ANALYSIS: "Video is ready for computer-vision analysis.",
  ANALYZING: "Checking whether computer-vision analysis can run on this video.",
  ANALYZED: "A computer-vision analysis pass has completed for this video.",
  FAILED: "Something went wrong while processing this video. This is often temporary — retry, or delete and re-upload.",
  DELETED: "This video has been deleted.",
};

export const videoStatusTone: Record<VideoStatus, "neutral" | "success" | "warning" | "danger" | "info" | "accent"> = {
  UPLOAD_PENDING: "neutral",
  UPLOADING: "info",
  UPLOADED: "info",
  VALIDATING: "info",
  VALID: "info",
  INVALID: "danger",
  PROCESSING: "info",
  READY_FOR_ANALYSIS: "accent",
  ANALYZING: "info",
  ANALYZED: "success",
  FAILED: "danger",
  DELETED: "neutral",
};

export const matchResultLabel: Record<MatchResult, string> = {
  WIN: "Win",
  LOSS: "Loss",
  UNKNOWN: "Unknown",
};

export const matchResultTone: Record<MatchResult, "success" | "danger" | "neutral"> = {
  WIN: "success",
  LOSS: "danger",
  UNKNOWN: "neutral",
};

export const matchStatusLabel: Record<MatchStatus, string> = {
  UNPROCESSED: "Not yet analyzed",
  PROCESSING: "Analysis in progress",
  PARTIALLY_PROCESSED: "Partially analyzed",
  PROCESSED: "Analyzed",
};

export const videoJobTypeLabel: Record<VideoJobType, string> = {
  PROCESSING: "Processing",
  CV_ANALYSIS: "CV analysis",
};

export const videoJobStatusLabel: Record<VideoJobStatus, string> = {
  PENDING: "Pending",
  RUNNING: "Running",
  SUCCEEDED: "Succeeded",
  FAILED: "Failed",
  UNAVAILABLE: "Unavailable",
};

export const videoJobStatusTone: Record<VideoJobStatus, "neutral" | "success" | "warning" | "danger" | "info"> = {
  PENDING: "neutral",
  RUNNING: "info",
  SUCCEEDED: "success",
  FAILED: "danger",
  UNAVAILABLE: "warning",
};

export const evidenceSourceLabel: Record<EvidenceSource, string> = {
  PLAYER: "You",
  COACH: "Coach",
  CV_SYSTEM: "Computer vision",
  AI_SYSTEM: "AI analysis",
};

// M5: computer-vision quality/calibration/identity — copy stays literal
// about what was (or wasn't) measured; never implies more certainty than
// cv-service actually reported. See docs/CV_ARCHITECTURE.md.
export const qualityStatusLabel: Record<QualityStatus, string> = {
  GOOD: "Good",
  ACCEPTABLE: "Acceptable",
  POOR: "Poor",
  UNUSABLE: "Unusable",
};

export const qualityStatusTone: Record<QualityStatus, "success" | "neutral" | "warning" | "danger"> = {
  GOOD: "success",
  ACCEPTABLE: "neutral",
  POOR: "warning",
  UNUSABLE: "danger",
};

export const calibrationStatusLabel: Record<CalibrationStatus, string> = {
  NOT_ATTEMPTED: "Not attempted",
  SUCCESS: "Court detected",
  PARTIAL: "Partially detected",
  FAILED: "Court not detected",
  LOW_CONFIDENCE: "Detected — low confidence",
};

export const calibrationStatusTone: Record<CalibrationStatus, "success" | "neutral" | "warning" | "danger"> = {
  NOT_ATTEMPTED: "neutral",
  SUCCESS: "success",
  PARTIAL: "warning",
  FAILED: "danger",
  LOW_CONFIDENCE: "warning",
};

export const playerIdentityLabel: Record<PlayerIdentity, string> = {
  ATHLETE: "You",
  OPPONENT: "Opponent",
  UNKNOWN: "Not yet identified",
};
