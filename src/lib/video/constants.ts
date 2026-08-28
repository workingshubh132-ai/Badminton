// Every limit here is intentionally conservative and documented rather than
// arbitrary — see docs/VIDEO_INTELLIGENCE.md "Known limitations" for the
// reasoning (a full 60-90 minute match at phone bitrates can exceed this;
// chunked/resumable upload is a follow-up, not solved here).
export const MAX_VIDEO_UPLOAD_BYTES = Number(
  process.env.MAX_VIDEO_UPLOAD_BYTES ?? 750 * 1024 * 1024, // 750 MB
);

export const MAX_PROCESSING_ATTEMPTS = 3;

// Coarse client-declared Content-Type allowlist, checked before any bytes are
// written to disk. This is a fast reject for obviously-wrong uploads, not the
// real validation — actual format verification happens via magic-byte
// sniffing in lib/video/magic-bytes.ts after the file is on disk, because a
// client can lie about Content-Type.
export const ALLOWED_CLIENT_MIME_PREFIXES = ["video/"];

export const DEFAULT_STREAM_URL_TTL_SECONDS = 600; // 10 minutes
