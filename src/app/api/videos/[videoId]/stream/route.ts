import { NextRequest, NextResponse } from "next/server";
import { Readable } from "node:stream";
import { auth } from "@/auth";
import { db } from "@/lib/db";
import { getVideoStorageProvider } from "@/lib/video/storage";
import { verifyVideoAccessToken } from "@/lib/video/access";

export const runtime = "nodejs";

const FORMAT_MIME_TYPES: Record<string, string> = {
  mp4: "video/mp4",
  quicktime: "video/quicktime",
  "webm-or-mkv": "video/webm",
  avi: "video/x-msvideo",
};

function parseRangeHeader(rangeHeader: string | null, totalBytes: number): { start: number; end: number } | null {
  if (!rangeHeader?.startsWith("bytes=")) return null;
  const [startStr, endStr] = rangeHeader.replace("bytes=", "").split("-");
  const start = startStr ? Number(startStr) : 0;
  const end = endStr ? Number(endStr) : totalBytes - 1;
  if (!Number.isFinite(start) || !Number.isFinite(end) || start > end || start < 0 || end >= totalBytes) {
    return null;
  }
  return { start, end };
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ videoId: string }> }) {
  const { videoId } = await params;
  const token = request.nextUrl.searchParams.get("token");

  // Defense in depth: a valid signed token AND an active session that
  // actually owns this video are both required. A leaked-but-unexpired
  // token alone is not enough — see lib/video/access.ts.
  if (!verifyVideoAccessToken(videoId, token)) {
    return NextResponse.json({ error: "This link has expired or is invalid." }, { status: 403 });
  }

  const session = await auth();
  if (!session?.user) {
    return NextResponse.json({ error: "You must be logged in to view this video." }, { status: 401 });
  }

  const athlete = await db.athlete.findUnique({ where: { userId: session.user.id } });
  const video = athlete
    ? await db.video.findFirst({ where: { id: videoId, athleteId: athlete.id, deletedAt: null } })
    : null;
  if (!video) {
    return NextResponse.json({ error: "Video not found." }, { status: 404 });
  }

  const storage = getVideoStorageProvider();
  if (!(await storage.exists(video.storageKey))) {
    return NextResponse.json({ error: "This video's file is not available." }, { status: 404 });
  }

  const { totalBytes } = await storage.retrieve(video.storageKey);
  const range = parseRangeHeader(request.headers.get("range"), totalBytes);
  const mimeType =
    video.clientMimeType && video.clientMimeType.startsWith("video/")
      ? video.clientMimeType
      : (FORMAT_MIME_TYPES[video.detectedFormat ?? ""] ?? "application/octet-stream");

  const { stream } = await storage.retrieve(video.storageKey, range ?? undefined);
  const webStream = Readable.toWeb(stream) as unknown as ReadableStream<Uint8Array>;

  const headers = new Headers({
    "Content-Type": mimeType,
    "Accept-Ranges": "bytes",
    "Cache-Control": "private, max-age=0, no-store",
  });

  if (range) {
    headers.set("Content-Range", `bytes ${range.start}-${range.end}/${totalBytes}`);
    headers.set("Content-Length", String(range.end - range.start + 1));
    return new NextResponse(webStream, { status: 206, headers });
  }

  headers.set("Content-Length", String(totalBytes));
  return new NextResponse(webStream, { status: 200, headers });
}
