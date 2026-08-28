import type { ConfidenceLevel, EventCategory, ShotType } from "@/generated/prisma/client";
import { PythonCvEngine } from "@/lib/video/python-cv-engine";

// The implementation-agnostic boundary a real computer-vision engine (M5+)
// plugs into. Nothing in this codebase should ever synthesize a shot
// detection, a court position, or a confidence score outside an
// implementation of this interface — see docs/VIDEO_INTELLIGENCE.md "CV
// engine interface" for the full contract and spec section 25 ("do not
// overbuild") for why NullCvEngine below is the only implementation today.

export interface CVAnalysisInput {
  video: {
    id: string;
    storageKey: string;
    durationSeconds: number | null;
    width: number | null;
    height: number | null;
  };
  athleteId: string;
}

export interface CVDetectedEvent {
  category: EventCategory;
  shotType?: ShotType;
  timestampSeconds: number;
  confidence: ConfidenceLevel;
  courtX?: number;
  courtY?: number;
  metadata?: Record<string, unknown>;
}

// M5 additions below: court calibration, quality assessment, and player
// tracking. These are deliberately a separate shape from CVDetectedEvent
// (which targets the M7+ Rally/Event tables) rather than being forced into
// events — a court calibration or a player trajectory is not a shot/rally
// event, and cv-service/app/schemas.py's own AnalysisResult keeps them as
// siblings for the same reason. Every field mirrors the Python service's
// wire format (see cv-service/app/schemas.py) so the mapping in
// PythonCvEngine.analyze is a direct field-for-field translation, not a
// reinterpretation.

export type CVQualityStatus = "GOOD" | "ACCEPTABLE" | "POOR" | "UNUSABLE";
export type CVCalibrationStatus = "NOT_ATTEMPTED" | "SUCCESS" | "PARTIAL" | "FAILED" | "LOW_CONFIDENCE";
export type CVPlayerIdentity = "ATHLETE" | "OPPONENT" | "UNKNOWN";

export interface CVQualityAssessment {
  status: CVQualityStatus;
  reasons: string[];
  measuredWidth: number | null;
  measuredHeight: number | null;
  measuredFrameRate: number | null;
  measuredDurationSeconds: number | null;
  framesSampled: number;
  blankFrameRatio: number | null;
  decodeFailureRatio: number | null;
}

export interface CVCourtCalibration {
  status: CVCalibrationStatus;
  confidence: ConfidenceLevel | null;
  /** [[x,y],[x,y],[x,y],[x,y]] video-pixel space, TL/TR/BR/BL order. */
  courtCornersPx: [number, number][] | null;
  /** 3x3 homography, video px -> court metres. */
  homography: number[][] | null;
  sourceFrameTimestamps: number[];
  warnings: string[];
}

export interface CVTrackingGap {
  startSeconds: number;
  endSeconds: number;
  reason: string;
}

export interface CVPlayerDetectionPoint {
  timestampSeconds: number;
  /** Normalized 0-1 image-space bbox — resolution independent. */
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: ConfidenceLevel;
  /** Real-world court metres for the bbox centre; null unless calibration succeeded. */
  courtX?: number | null;
  courtY?: number | null;
}

export interface CVPlayerTrack {
  /** The engine's own track id (a UUID) — unique within one analysis run only. */
  engineTrackId: string;
  identity: CVPlayerIdentity;
  identitySource: "HEURISTIC" | "USER_CONFIRMED";
  confidence: ConfidenceLevel;
  detections: CVPlayerDetectionPoint[];
  gaps: CVTrackingGap[];
}

export interface CVProcessingMetadata {
  modelVersions: Record<string, string>;
  samplingFps: number;
  framesSampled: number;
  processingSeconds: number;
  config: Record<string, unknown>;
  videoChecksumSha256: string | null;
}

export interface CVAnalysisResult {
  /**
   * "completed" — the engine ran and (possibly empty) `events` is a real
   * result. "unavailable" — no engine capable of this work is configured;
   * this is the honest, expected state today, not an error. "failed" — an
   * engine was configured and attempted the work but broke.
   */
  status: "completed" | "unavailable" | "failed";
  events: CVDetectedEvent[];
  /** Present whenever status is "completed" — see NullCvEngine vs. PythonCvEngine. */
  quality?: CVQualityAssessment;
  courtCalibration?: CVCourtCalibration;
  playerTracks?: CVPlayerTrack[];
  processingMetadata?: CVProcessingMetadata;
  warnings: string[];
  message?: string;
  engineName: string;
  engineVersion: string;
}

export interface CVAnalysisEngine {
  readonly name: string;
  readonly version: string;
  analyze(input: CVAnalysisInput): Promise<CVAnalysisResult>;
}

/**
 * The only engine wired up today. It does no video processing at all — it
 * honestly reports that no real engine exists yet, per the product's
 * "insufficient evidence" > "confident-sounding answer" rule (spec section
 * 27). Every real analysis pipeline stage (job creation, status transitions,
 * event-writing) already runs for real against this engine; only the
 * detection logic itself is unbuilt.
 */
export class NullCvEngine implements CVAnalysisEngine {
  readonly name = "null-cv-engine";
  readonly version = "0.0.0";

  async analyze(): Promise<CVAnalysisResult> {
    return {
      status: "unavailable",
      events: [],
      warnings: [],
      message:
        "No computer-vision analysis engine is configured yet. Upload, storage, and validation for this video are complete, and it will be analyzed automatically as soon as a real engine is available.",
      engineName: this.name,
      engineVersion: this.version,
    };
  }
}

/**
 * Returns PythonCvEngine when CV_SERVICE_URL is configured (see
 * docs/CV_ARCHITECTURE.md "Deployment" for running cv-service locally),
 * otherwise NullCvEngine — the same "unavailable, not fabricated" fallback
 * M4 shipped with. CI and any environment that hasn't started cv-service
 * get NullCvEngine automatically; nothing breaks by omission.
 */
export function getCvEngine(): CVAnalysisEngine {
  const baseUrl = process.env.CV_SERVICE_URL;
  if (!baseUrl) {
    return new NullCvEngine();
  }
  return new PythonCvEngine(baseUrl, process.env.CV_SERVICE_TOKEN);
}
