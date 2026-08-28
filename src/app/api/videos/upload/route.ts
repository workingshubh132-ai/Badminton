import { NextRequest, NextResponse } from "next/server";
import { Readable } from "node:stream";
import { auth } from "@/auth";
import { db } from "@/lib/db";
import { getVideoStorageProvider, VideoTooLargeError } from "@/lib/video/storage";
import { runProcessingPipeline } from "@/lib/video/job-runner";
import { setVideoStatus } from "@/lib/video/transition";
import { MAX_VIDEO_UPLOAD_BYTES } from "@/lib/video/constants";
import { videoUploadMetaSchema } from "@/lib/validation";

// Node runtime required: this streams the request body straight to disk via
// Node's fs/stream APIs (see lib/video/storage.ts), which the edge runtime
// cannot do. Next.js 16 defaults Route Handlers to Node already; explicit
// for clarity given how much this route depends on it.
export const runtime = "nodejs";

function extensionFromFilename(filename: string): string {
  const match = /\.[a-zA-Z0-9]+$/.exec(filename);
  return match ? match[0].toLowerCase() : ".bin";
}

export async function POST(request: NextRequest) {
  const session = await auth();
  if (!session?.user) {
    return NextResponse.json({ error: "You must be logged in to upload video." }, { status: 401 });
  }

  const athlete = await db.athlete.findUnique({ where: { userId: session.user.id } });
  if (!athlete) {
    return NextResponse.json(
      { error: "Complete your athlete profile before uploading video." },
      { status: 409 },
    );
  }

  const params = request.nextUrl.searchParams;
  const parsedMeta = videoUploadMetaSchema.safeParse({
    videoType: params.get("videoType"),
    matchId: params.get("matchId") ?? "",
    originalFilename: params.get("originalFilename") ?? "",
    clientMimeType: params.get("clientMimeType") ?? "",
  });
  if (!parsedMeta.success) {
    return NextResponse.json(
      { error: "Missing or invalid upload metadata.", details: parsedMeta.error.flatten().fieldErrors },
      { status: 400 },
    );
  }
  const { videoType, matchId, originalFilename, clientMimeType } = parsedMeta.data;

  if (matchId) {
    const match = await db.match.findFirst({ where: { id: matchId, athleteId: athlete.id } });
    if (!match) {
      return NextResponse.json({ error: "Match not found." }, { status: 404 });
    }
  }

  const contentLengthHeader = request.headers.get("content-length");
  if (contentLengthHeader) {
    const contentLength = Number(contentLengthHeader);
    if (Number.isFinite(contentLength) && contentLength > MAX_VIDEO_UPLOAD_BYTES) {
      return NextResponse.json(
        { error: `This file exceeds the ${Math.round(MAX_VIDEO_UPLOAD_BYTES / (1024 * 1024))} MB per-video limit.` },
        { status: 413 },
      );
    }
    if (contentLength === 0) {
      return NextResponse.json({ error: "The uploaded file is empty." }, { status: 400 });
    }
  }

  if (!request.body) {
    return NextResponse.json({ error: "No file data received." }, { status: 400 });
  }

  const storage = getVideoStorageProvider();
  const { storageKey } = await storage.createUploadTarget({
    athleteId: athlete.id,
    extension: extensionFromFilename(originalFilename),
  });

  const video = await db.video.create({
    data: {
      athleteId: athlete.id,
      matchId,
      videoType,
      status: "UPLOADING",
      originalFilename,
      clientMimeType,
      uploadedByUserId: session.user.id,
      storageKey,
    },
  });

  try {
    const nodeStream = Readable.fromWeb(request.body as unknown as import("node:stream/web").ReadableStream);
    const { byteSize, sha256 } = await storage.upload(storageKey, nodeStream, {
      maxBytes: MAX_VIDEO_UPLOAD_BYTES,
    });

    await setVideoStatus(video, "UPLOADED", { byteSize, checksumSha256: sha256 });
  } catch (error) {
    const isTooLarge = error instanceof VideoTooLargeError;
    await setVideoStatus(video, "FAILED", {
      failureReason: isTooLarge
        ? `This file exceeds the ${Math.round(MAX_VIDEO_UPLOAD_BYTES / (1024 * 1024))} MB per-video limit.`
        : "The upload was interrupted before it finished.",
    });
    return NextResponse.json(
      { error: isTooLarge ? "File too large." : "Upload failed.", videoId: video.id },
      { status: isTooLarge ? 413 : 500 },
    );
  }

  try {
    await runProcessingPipeline(video.id);
  } catch (error) {
    // The pipeline itself is responsible for recording failures on the
    // Video/VideoJob rows; a thrown error here means something unexpected
    // broke outside that — still respond usefully rather than a bare 500.
    return NextResponse.json(
      {
        error: "Video uploaded, but processing could not start.",
        detail: error instanceof Error ? error.message : String(error),
        videoId: video.id,
      },
      { status: 202 },
    );
  }

  const finalVideo = await db.video.findUniqueOrThrow({ where: { id: video.id } });
  return NextResponse.json({
    videoId: finalVideo.id,
    status: finalVideo.status,
    invalidReason: finalVideo.invalidReason,
    failureReason: finalVideo.failureReason,
  });
}
