import { createHmac, timingSafeEqual } from "node:crypto";
import { DEFAULT_STREAM_URL_TTL_SECONDS } from "@/lib/video/constants";

// Short-lived, HMAC-signed access to a private video, always via this app's
// own /api/videos/[videoId]/stream route — never a permanent public URL, per
// spec section 4/18/33. The route itself re-checks session ownership on top
// of a valid token (defense in depth: a leaked-but-unexpired token alone is
// not sufficient if the requester's own session doesn't own the video).

function getSigningSecret(): string {
  const secret = process.env.AUTH_SECRET;
  if (!secret) {
    throw new Error("AUTH_SECRET must be set to sign video access tokens.");
  }
  return secret;
}

function sign(payload: string): string {
  return createHmac("sha256", getSigningSecret()).update(payload).digest("hex");
}

export function createVideoAccessToken(
  videoId: string,
  expiresInSeconds: number = DEFAULT_STREAM_URL_TTL_SECONDS,
): string {
  const expiresAt = Math.floor(Date.now() / 1000) + expiresInSeconds;
  const signature = sign(`${videoId}.${expiresAt}`);
  return `${expiresAt}.${signature}`;
}

export function verifyVideoAccessToken(videoId: string, token: string | null | undefined): boolean {
  if (!token) return false;
  const [expiresAtRaw, signature] = token.split(".");
  if (!expiresAtRaw || !signature) return false;

  const expiresAt = Number(expiresAtRaw);
  if (!Number.isFinite(expiresAt) || expiresAt < Math.floor(Date.now() / 1000)) return false;

  const expectedSignature = sign(`${videoId}.${expiresAt}`);
  const provided = Buffer.from(signature);
  const expected = Buffer.from(expectedSignature);
  if (provided.length !== expected.length) return false;
  return timingSafeEqual(provided, expected);
}

/** Builds a fresh, short-lived streaming URL for a video the caller has already verified ownership of. */
export function buildVideoStreamUrl(videoId: string, expiresInSeconds: number = DEFAULT_STREAM_URL_TTL_SECONDS): string {
  const token = createVideoAccessToken(videoId, expiresInSeconds);
  return `/api/videos/${videoId}/stream?token=${token}`;
}
