import type { VideoStatus } from "@/generated/prisma/client";

// The authoritative Video status transition table. Every write to
// Video.status in this codebase must go through assertValidVideoStatusTransition
// first — see lib/video/job-runner.ts. Documented per transition below;
// see docs/VIDEO_INTELLIGENCE.md "Video lifecycle" for the narrative version.
const TRANSITIONS: Record<VideoStatus, VideoStatus[]> = {
  // Row created; no bytes received yet.
  UPLOAD_PENDING: ["UPLOADING", "FAILED", "DELETED"],
  // Bytes actively streaming to storage.
  UPLOADING: ["UPLOADED", "FAILED", "DELETED"],
  // All bytes received and written to storage.
  UPLOADED: ["VALIDATING", "DELETED"],
  // Running magic-byte / size checks.
  VALIDATING: ["VALID", "INVALID", "DELETED"],
  // Passed validation; about to extract metadata.
  VALID: ["PROCESSING", "DELETED"],
  // Failed validation — not fixable in place; the only way out is deletion
  // (and re-upload as a new Video).
  INVALID: ["DELETED"],
  // Extracting duration/dimensions/etc. INVALID here means the prober
  // determined the file isn't actually a decodable video despite passing
  // the magic-byte check (e.g. truncated upload); FAILED means something
  // unexpected broke (e.g. a disk I/O error) and is retryable.
  PROCESSING: ["READY_FOR_ANALYSIS", "INVALID", "FAILED", "DELETED"],
  // Valid, processed, and eligible for CV analysis.
  READY_FOR_ANALYSIS: ["ANALYZING", "DELETED"],
  // A CV analysis job is running. It always resolves back to
  // READY_FOR_ANALYSIS (job came back UNAVAILABLE or FAILED — the video
  // itself is fine, only the analysis attempt didn't produce a result) or
  // forward to ANALYZED (job SUCCEEDED). See lib/video/job-runner.ts.
  ANALYZING: ["ANALYZED", "READY_FOR_ANALYSIS", "DELETED"],
  // A CV analysis job completed successfully. Re-analysis (e.g. with an
  // improved engine) is allowed.
  ANALYZED: ["ANALYZING", "DELETED"],
  // The ingest pipeline (upload/validation/processing) broke. Retryable —
  // FAILED -> VALIDATING re-enters the pipeline against the same stored
  // bytes — or deletable.
  FAILED: ["VALIDATING", "DELETED"],
  // Terminal. Soft-deleted videos never transition again.
  DELETED: [],
};

export class InvalidVideoStatusTransitionError extends Error {
  constructor(
    public readonly from: VideoStatus,
    public readonly to: VideoStatus,
  ) {
    super(`Cannot transition video status from ${from} to ${to}.`);
    this.name = "InvalidVideoStatusTransitionError";
  }
}

export function canTransitionVideoStatus(from: VideoStatus, to: VideoStatus): boolean {
  return TRANSITIONS[from]?.includes(to) ?? false;
}

export function assertValidVideoStatusTransition(from: VideoStatus, to: VideoStatus): void {
  if (!canTransitionVideoStatus(from, to)) {
    throw new InvalidVideoStatusTransitionError(from, to);
  }
}
