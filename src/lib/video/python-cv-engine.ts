import type { ConfidenceLevel } from "@/generated/prisma/client";
import { getVideoStorageProvider } from "@/lib/video/storage";
import type {
  CVAnalysisEngine,
  CVAnalysisInput,
  CVAnalysisResult,
  CVCalibrationStatus,
  CVCourtCalibration,
  CVPlayerDetectionPoint,
  CVPlayerIdentity,
  CVPlayerTrack,
  CVProcessingMetadata,
  CVQualityAssessment,
  CVQualityStatus,
  CVTrackingGap,
} from "@/lib/video/cv-engine";

// ---------------------------------------------------------------------------
// Calls the Python cv-service (see cv-service/) over HTTP — the first real
// CVAnalysisEngine implementation, replacing NullCvEngine (M5). See
// docs/CV_ARCHITECTURE.md for why CV runs as a separate Python service
// rather than in Node, and for the single-host shared-filesystem assumption
// this relies on: both processes must see the video at the same absolute
// path, exactly like ffprobe already requires in job-runner.ts.
//
// KNOWN LIMITATION (see docs/CV_ARCHITECTURE.md "Known limitations"):
// job-runner.ts calls CVAnalysisEngine.analyze() inline, in the same
// request that triggered analysis — exactly like NullCvEngine did in M4.
// That was honest in M4 because NullCvEngine resolved instantly; a real
// model pass over real video can take tens of seconds to minutes, which is
// too slow for an inline HTTP request in a real deployment. This is the
// trigger condition job-runner.ts's own module comment predicted ("The
// moment a real step becomes slow ... it moves behind a real queue").
// Moving analysis invocation behind an actual queue is deliberately out of
// scope for M5 — no queue infrastructure exists in this stack, and building
// one is a bigger architectural decision than a CV milestone should make
// unilaterally. Treat this as a documented, pre-existing scaling limit
// inherited from the M4 job-runner design, not something M5 fixed. The
// request-level timeout below turns "the service hangs" into an honest
// "failed" result instead of hanging the whole HTTP request forever, which
// is the most this milestone should responsibly do about it.
// ---------------------------------------------------------------------------

// ---- Wire types: exact mirror of cv-service/app/schemas.py ---------------
// snake_case on purpose — this is literally what FastAPI/pydantic serializes
// over HTTP (no camelCase alias generator is configured service-side). Kept
// private to this module; everything else in the app only ever sees the
// camelCase CV* types from cv-engine.ts.

interface WireVideoInfo {
  width: number | null;
  height: number | null;
  fps: number | null;
  frame_count: number | null;
  duration_seconds: number | null;
  codec: string | null;
}

interface WireQualityAssessment {
  status: CVQualityStatus;
  reasons: string[];
  metrics: Record<string, unknown>;
}

interface WireBBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface WireDetection {
  timestamp_seconds: number;
  bbox: WireBBox;
  score: number;
  confidence: ConfidenceLevel;
  court_x: number | null;
  court_y: number | null;
}

interface WireTrackingGap {
  start_seconds: number;
  end_seconds: number;
  reason: string;
}

interface WirePlayerTrack {
  track_id: string;
  identity: CVPlayerIdentity;
  identity_source: "HEURISTIC" | "USER_CONFIRMED";
  confidence: ConfidenceLevel;
  detections: WireDetection[];
  gaps: WireTrackingGap[];
}

interface WireCourtCalibration {
  status: CVCalibrationStatus;
  confidence: ConfidenceLevel | null;
  homography: number[][] | null;
  court_corners_px: [number, number][] | null;
  source_frame_timestamps: number[];
  warnings: string[];
}

interface WireProcessingMetadata {
  engine_name: string;
  engine_version: string;
  model_versions: Record<string, string>;
  sampling_fps: number;
  frames_sampled: number;
  processing_seconds: number;
  config: Record<string, unknown>;
  video_checksum_sha256: string | null;
}

// Exported (types only, no runtime cost) so python-cv-engine.test.ts can
// build well-typed fixture response bodies for mapWireResult.
export interface WireAnalysisResult {
  status: "completed" | "failed" | "unavailable";
  message: string | null;
  video: WireVideoInfo;
  quality: WireQualityAssessment;
  calibration: WireCourtCalibration;
  tracks: WirePlayerTrack[];
  warnings: string[];
  processing_metadata: WireProcessingMetadata;
}

const FALLBACK_ENGINE_NAME = "python-cv-service";
const FALLBACK_ENGINE_VERSION = "unknown";
const DEFAULT_TIMEOUT_MS = 10 * 60 * 1000;
const DEFAULT_SAMPLING_FPS = 2.0;
const DEFAULT_MAX_SAMPLED_FRAMES = 600;

export class PythonCvEngine implements CVAnalysisEngine {
  readonly name = FALLBACK_ENGINE_NAME;
  // This integration's own request/response contract version — distinct
  // from the running service's engine_version (reported per-analysis in
  // processing_metadata once a call succeeds).
  readonly version = "client-1";

  constructor(
    private readonly baseUrl: string,
    private readonly internalToken?: string,
    private readonly timeoutMs: number = DEFAULT_TIMEOUT_MS,
  ) {}

  async analyze(input: CVAnalysisInput): Promise<CVAnalysisResult> {
    const localPath = getVideoStorageProvider().getLocalFilesystemPath(input.video.storageKey);
    if (!localPath) {
      return {
        status: "unavailable",
        events: [],
        warnings: [],
        message:
          "The computer-vision service requires a shared local filesystem path to the video, and the current storage backend does not expose one.",
        engineName: this.name,
        engineVersion: this.version,
      };
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(this.internalToken ? { "X-Internal-Token": this.internalToken } : {}),
        },
        body: JSON.stringify({
          video_id: input.video.id,
          video_path: localPath,
          sampling_fps: DEFAULT_SAMPLING_FPS,
          max_sampled_frames: DEFAULT_MAX_SAMPLED_FRAMES,
        }),
        signal: controller.signal,
      });
    } catch (error) {
      const isAbort = error instanceof Error && error.name === "AbortError";
      return {
        status: "failed",
        events: [],
        warnings: [],
        message: isAbort
          ? `The computer-vision service did not respond within ${Math.round(this.timeoutMs / 1000)}s.`
          : `Could not reach the computer-vision service: ${error instanceof Error ? error.message : String(error)}`,
        engineName: FALLBACK_ENGINE_NAME,
        engineVersion: FALLBACK_ENGINE_VERSION,
      };
    } finally {
      clearTimeout(timeout);
    }

    if (!response.ok) {
      const detail = await response.text().catch(() => "");
      return {
        status: "failed",
        events: [],
        warnings: [],
        message: `The computer-vision service returned HTTP ${response.status}${detail ? `: ${detail.slice(0, 500)}` : ""}.`,
        engineName: FALLBACK_ENGINE_NAME,
        engineVersion: FALLBACK_ENGINE_VERSION,
      };
    }

    let wire: WireAnalysisResult;
    try {
      wire = (await response.json()) as WireAnalysisResult;
    } catch {
      return {
        status: "failed",
        events: [],
        warnings: [],
        message: "The computer-vision service returned a response that could not be parsed.",
        engineName: FALLBACK_ENGINE_NAME,
        engineVersion: FALLBACK_ENGINE_VERSION,
      };
    }

    return mapWireResult(wire);
  }
}

/** Exported for direct unit testing of the wire-format translation — see python-cv-engine.test.ts. */
export function mapWireResult(wire: WireAnalysisResult): CVAnalysisResult {
  const engineName = wire.processing_metadata?.engine_name || FALLBACK_ENGINE_NAME;
  const engineVersion = wire.processing_metadata?.engine_version || FALLBACK_ENGINE_VERSION;

  if (wire.status !== "completed") {
    // cv-service/app/pipeline.py only ever returns "completed" today (even
    // for UNUSABLE quality) — a genuine service-side exception surfaces as
    // a non-2xx response, handled in PythonCvEngine.analyze above, not as
    // status:"failed" in a 200 body. This branch exists for
    // forward-compatibility with a future engine status the service might
    // legitimately return, not because it's reachable today.
    return {
      status: wire.status,
      events: [],
      warnings: wire.warnings ?? [],
      message: wire.message ?? undefined,
      engineName,
      engineVersion,
    };
  }

  const quality: CVQualityAssessment = {
    status: wire.quality.status,
    reasons: wire.quality.reasons,
    measuredWidth: wire.video.width,
    measuredHeight: wire.video.height,
    measuredFrameRate: wire.video.fps,
    measuredDurationSeconds: wire.video.duration_seconds,
    framesSampled: wire.processing_metadata.frames_sampled,
    blankFrameRatio: numericMetric(wire.quality.metrics, "blank_frame_ratio"),
    decodeFailureRatio: numericMetric(wire.quality.metrics, "decode_failure_ratio"),
  };

  const courtCalibration: CVCourtCalibration = {
    status: wire.calibration.status,
    confidence: wire.calibration.confidence,
    courtCornersPx: wire.calibration.court_corners_px,
    homography: wire.calibration.homography,
    sourceFrameTimestamps: wire.calibration.source_frame_timestamps,
    warnings: wire.calibration.warnings,
  };

  const playerTracks: CVPlayerTrack[] = wire.tracks.map((track) => ({
    engineTrackId: track.track_id,
    identity: track.identity,
    identitySource: track.identity_source,
    confidence: track.confidence,
    detections: track.detections.map(
      (det): CVPlayerDetectionPoint => ({
        timestampSeconds: det.timestamp_seconds,
        x: det.bbox.x,
        y: det.bbox.y,
        width: det.bbox.width,
        height: det.bbox.height,
        confidence: det.confidence,
        courtX: det.court_x,
        courtY: det.court_y,
      }),
    ),
    gaps: track.gaps.map(
      (gap): CVTrackingGap => ({
        startSeconds: gap.start_seconds,
        endSeconds: gap.end_seconds,
        reason: gap.reason,
      }),
    ),
  }));

  const processingMetadata: CVProcessingMetadata = {
    modelVersions: wire.processing_metadata.model_versions,
    samplingFps: wire.processing_metadata.sampling_fps,
    framesSampled: wire.processing_metadata.frames_sampled,
    processingSeconds: wire.processing_metadata.processing_seconds,
    config: wire.processing_metadata.config,
    videoChecksumSha256: wire.processing_metadata.video_checksum_sha256,
  };

  return {
    status: "completed",
    // M5 produces no Rally/Event rows — shot classification, rally
    // reconstruction etc. are explicitly out of scope (M6+).
    events: [],
    quality,
    courtCalibration,
    playerTracks,
    processingMetadata,
    warnings: wire.warnings ?? [],
    message: wire.message ?? undefined,
    engineName,
    engineVersion,
  };
}

function numericMetric(metrics: Record<string, unknown>, key: string): number | null {
  const value = metrics[key];
  return typeof value === "number" ? value : null;
}
