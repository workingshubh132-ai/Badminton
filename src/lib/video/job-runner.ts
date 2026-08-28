import { db } from "@/lib/db";
import { getVideoStorageProvider } from "@/lib/video/storage";
import { detectContainerFormat } from "@/lib/video/magic-bytes";
import { probeVideoFile } from "@/lib/video/probe";
import { getCvEngine } from "@/lib/video/cv-engine";
import { setVideoStatus } from "@/lib/video/transition";
import { MAX_PROCESSING_ATTEMPTS, MAX_VIDEO_UPLOAD_BYTES } from "@/lib/video/constants";
import { Prisma } from "@/generated/prisma/client";
import type { Video } from "@/generated/prisma/client";

// ---------------------------------------------------------------------------
// Local job runner — the documented stand-in for a real background worker.
//
// `runProcessingPipeline` and `runAnalysisPipeline` are called inline, in the
// same request that triggered them (upload finalize, or a retry/re-analyze
// server action) — never behind an arbitrary setTimeout, and never
// fabricating a result. That's honest today because every step is genuinely
// fast: magic-byte sniffing reads ~64 bytes, ffprobe reads container headers
// (not the whole file), and the only CV engine wired up (NullCvEngine)
// resolves instantly. Nothing here blocks on video *decoding*.
//
// The moment a real step becomes slow (e.g. an actual CV pass, or frame-level
// QC), it moves behind a real queue — and the schema/interfaces already
// support that with zero changes: `VideoJob` rows are queue-shaped (status,
// progress, attempt, retry), and every stage already goes through the exact
// function a worker would call (`runProcessingPipeline(videoId)` /
// `runAnalysisPipeline(videoId)`). Swapping "call it inline" for "enqueue a
// message that calls it" is the entire migration.
// ---------------------------------------------------------------------------

function formatBytes(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb.toFixed(0)} MB`;
}

/**
 * Entry point after upload bytes are fully written (status UPLOADED), or as
 * a retry after a pipeline failure (status FAILED). Runs validation and
 * metadata extraction, then auto-chains into runAnalysisPipeline once the
 * video reaches READY_FOR_ANALYSIS.
 */
export async function runProcessingPipeline(videoId: string): Promise<void> {
  let video = await db.video.findUniqueOrThrow({ where: { id: videoId } });

  if (video.status === "FAILED") {
    const priorAttempts = await db.videoJob.count({ where: { videoId, type: "PROCESSING" } });
    if (priorAttempts >= MAX_PROCESSING_ATTEMPTS) {
      throw new Error(
        `This video has failed processing ${priorAttempts} times and will not be retried automatically. Delete it and re-upload.`,
      );
    }
  }
  video = await setVideoStatus(video, "VALIDATING");

  const attemptNumber = (await db.videoJob.count({ where: { videoId, type: "PROCESSING" } })) + 1;
  const job = await db.videoJob.create({
    data: {
      videoId,
      type: "PROCESSING",
      status: "RUNNING",
      startedAt: new Date(),
      attempt: attemptNumber,
      maxAttempts: MAX_PROCESSING_ATTEMPTS,
    },
  });

  const storage = getVideoStorageProvider();

  // --- Validation: size + magic-byte format check -------------------------
  const { stream, totalBytes } = await storage.retrieve(video.storageKey, { start: 0, end: 63 });
  const head = await new Promise<Buffer>((resolve, reject) => {
    const chunks: Buffer[] = [];
    stream.on("data", (chunk: Buffer) => chunks.push(chunk));
    stream.on("end", () => resolve(Buffer.concat(chunks)));
    stream.on("error", reject);
  });

  if (totalBytes === 0) {
    await failValidation(video, job.id, "The uploaded file is empty.");
    return;
  }
  if (totalBytes > MAX_VIDEO_UPLOAD_BYTES) {
    await failValidation(
      video,
      job.id,
      `This file is ${formatBytes(totalBytes)}, which exceeds the ${formatBytes(MAX_VIDEO_UPLOAD_BYTES)} per-video limit.`,
    );
    return;
  }

  const detected = detectContainerFormat(head);
  if (!detected) {
    await failValidation(
      video,
      job.id,
      "Video could not be processed because its format is unsupported. Try exporting as MP4 (H.264) and re-uploading.",
    );
    return;
  }

  video = await setVideoStatus(video, "VALID", { detectedFormat: detected.format });
  video = await setVideoStatus(video, "PROCESSING");

  // --- Metadata extraction (best-effort; never fabricated) -----------------
  const absolutePath = resolveLocalPathForProbe(video.storageKey);
  const probeResult = await probeVideoFile(absolutePath);

  if (!probeResult.ok && probeResult.reason === "probe_failed") {
    // ffprobe ran and determined this isn't a decodable video, despite
    // passing the magic-byte check (e.g. a truncated upload). That's a real
    // defect in the file, not a tooling gap.
    video = await setVideoStatus(video, "INVALID", { invalidReason: probeResult.detail });
    await db.videoJob.update({
      where: { id: job.id },
      data: { status: "FAILED", errorMessage: probeResult.detail, finishedAt: new Date(), progressPercent: 100 },
    });
    return;
  }

  const metadata =
    probeResult.ok
      ? {
          durationSeconds: probeResult.data.durationSeconds,
          width: probeResult.data.width,
          height: probeResult.data.height,
          frameRate: probeResult.data.frameRate,
          orientation: deriveOrientation(probeResult.data.width, probeResult.data.height),
        }
      : ({} as Record<string, never>);

  video = await setVideoStatus(video, "READY_FOR_ANALYSIS", metadata);
  await db.videoJob.update({
    where: { id: job.id },
    data: {
      status: "SUCCEEDED",
      finishedAt: new Date(),
      progressPercent: 100,
      engineName: "ffprobe-metadata-extractor",
      errorMessage: !probeResult.ok
        ? `Metadata not extracted: ${probeResult.detail}` // informational, not a failure
        : null,
    },
  });

  await runAnalysisPipeline(videoId);
}

async function failValidation(video: Video, jobId: string, reason: string): Promise<void> {
  await setVideoStatus(video, "INVALID", { invalidReason: reason });
  await db.videoJob.update({
    where: { id: jobId },
    data: { status: "FAILED", errorMessage: reason, finishedAt: new Date(), progressPercent: 100 },
  });
}

function deriveOrientation(
  width: number | null,
  height: number | null,
): "LANDSCAPE" | "PORTRAIT" | "SQUARE" | undefined {
  if (width == null || height == null) return undefined;
  if (width === height) return "SQUARE";
  return width > height ? "LANDSCAPE" : "PORTRAIT";
}

// ffprobe needs a real path, not a stream. VideoStorageProvider.getLocalFilesystemPath
// exposes one when the backend is local disk; a future non-local storage
// provider returning null here would mean downloading to a temp file before
// probing instead (not implemented — no non-local provider exists yet).
function resolveLocalPathForProbe(storageKey: string): string {
  const localPath = getVideoStorageProvider().getLocalFilesystemPath(storageKey);
  if (!localPath) {
    throw new Error("This storage backend does not expose a local filesystem path for ffprobe.");
  }
  return localPath;
}

/**
 * Runs (or re-runs) CV analysis for a video that is READY_FOR_ANALYSIS or
 * ANALYZED. Always resolves the video back to READY_FOR_ANALYSIS (engine
 * unavailable or failed) or forward to ANALYZED (engine completed) — never
 * leaves it stuck in ANALYZING, and never moves it to the ingest-pipeline
 * FAILED status (see docs/VIDEO_INTELLIGENCE.md "Video lifecycle").
 */
export async function runAnalysisPipeline(videoId: string): Promise<void> {
  const video = await db.video.findUniqueOrThrow({ where: { id: videoId } });
  const analyzing = await setVideoStatus(video, "ANALYZING");

  const attemptNumber = (await db.videoJob.count({ where: { videoId, type: "CV_ANALYSIS" } })) + 1;
  const job = await db.videoJob.create({
    data: { videoId, type: "CV_ANALYSIS", status: "RUNNING", startedAt: new Date(), attempt: attemptNumber },
  });

  const engine = getCvEngine();
  const result = await engine.analyze({
    video: {
      id: video.id,
      storageKey: video.storageKey,
      durationSeconds: video.durationSeconds,
      width: video.width,
      height: video.height,
    },
    athleteId: video.athleteId,
  });

  if (result.status === "completed") {
    // Video status transitions first, matching the pre-existing ordering
    // (see the FAILED/UNAVAILABLE branch below, unchanged): if this throws
    // on an invalid transition, nothing else has been written yet. The CV
    // result rows and the job's SUCCEEDED status are then written together
    // as one atomic transaction below — either the whole result
    // (quality/calibration/tracks/events/job status) lands together, or
    // none of it does, so a mid-write crash never leaves a job marked
    // SUCCEEDED without the rows that back it.
    await setVideoStatus(analyzing, "ANALYZED");

    const writes: Prisma.PrismaPromise<unknown>[] = [];

    if (result.events.length > 0) {
      writes.push(
        db.event.createMany({
          data: result.events.map((event) => ({
            videoId: video.id,
            source: "CV_ANALYSIS" as const,
            category: event.category,
            shotType: event.shotType,
            timestampSeconds: event.timestampSeconds,
            confidence: event.confidence,
            courtX: event.courtX,
            courtY: event.courtY,
            metadata: event.metadata as Prisma.InputJsonValue | undefined,
          })),
        }),
      );
    }

    if (result.quality) {
      writes.push(
        db.videoQualityAssessment.create({
          data: {
            videoId: video.id,
            videoJobId: job.id,
            status: result.quality.status,
            reasons: result.quality.reasons,
            measuredWidth: result.quality.measuredWidth,
            measuredHeight: result.quality.measuredHeight,
            measuredFrameRate: result.quality.measuredFrameRate,
            measuredDurationSeconds: result.quality.measuredDurationSeconds,
            framesSampled: result.quality.framesSampled,
            blankFrameRatio: result.quality.blankFrameRatio,
            decodeFailureRatio: result.quality.decodeFailureRatio,
          },
        }),
      );
    }

    if (result.courtCalibration) {
      const calibration = result.courtCalibration;
      writes.push(
        db.courtCalibration.create({
          data: {
            videoId: video.id,
            videoJobId: job.id,
            status: calibration.status,
            confidence: calibration.confidence,
            courtCornersPx: jsonOrDbNull(calibration.courtCornersPx),
            homography: jsonOrDbNull(calibration.homography),
            sourceFrameTimestamps: calibration.sourceFrameTimestamps,
            warnings: calibration.warnings,
          },
        }),
      );
    }

    if (result.playerTracks && result.playerTracks.length > 0) {
      writes.push(
        db.playerTrack.createMany({
          data: result.playerTracks.map((track) => ({
            videoId: video.id,
            videoJobId: job.id,
            engineTrackId: track.engineTrackId,
            identity: track.identity,
            identitySource: track.identitySource,
            confidence: track.confidence,
            startTimestampSeconds: track.detections[0]?.timestampSeconds ?? 0,
            endTimestampSeconds: track.detections[track.detections.length - 1]?.timestampSeconds ?? 0,
            detections: track.detections as unknown as Prisma.InputJsonValue,
            gaps: track.gaps as unknown as Prisma.InputJsonValue,
          })),
        }),
      );
    }

    writes.push(
      db.videoJob.update({
        where: { id: job.id },
        data: {
          status: "SUCCEEDED",
          finishedAt: new Date(),
          progressPercent: 100,
          engineName: result.engineName,
          engineVersion: result.engineVersion,
          resultMetadata: result.processingMetadata
            ? (result.processingMetadata as unknown as Prisma.InputJsonValue)
            : undefined,
        },
      }),
    );

    await db.$transaction(writes);
    return;
  }

  await setVideoStatus(analyzing, "READY_FOR_ANALYSIS");
  await db.videoJob.update({
    where: { id: job.id },
    data: {
      status: result.status === "unavailable" ? "UNAVAILABLE" : "FAILED",
      finishedAt: new Date(),
      progressPercent: 100,
      engineName: result.engineName,
      engineVersion: result.engineVersion,
      errorMessage: result.message,
    },
  });
}

// Prisma requires an explicit sentinel to write a real SQL NULL into a
// nullable Json column — a plain JS `null` is ambiguous between "store the
// JSON literal null" and "no value" (see Prisma.JsonNull vs Prisma.DbNull).
// Court calibration data is either wholly present or wholly absent, so
// Prisma.DbNull ("no value") is always the correct one here.
function jsonOrDbNull(value: unknown): Prisma.InputJsonValue | typeof Prisma.DbNull {
  return value === null ? Prisma.DbNull : (value as Prisma.InputJsonValue);
}
