import { createHash, randomUUID } from "node:crypto";
import { createReadStream, createWriteStream } from "node:fs";
import { mkdir, stat, unlink } from "node:fs/promises";
import path from "node:path";
import { pipeline } from "node:stream/promises";
import { Transform, type Readable } from "node:stream";

/**
 * Storage-level operations only: bytes in, bytes out, existence, deletion.
 * Deliberately does NOT include "generate temporary access URL" — that
 * responsibility lives in lib/video/access.ts and always resolves to this
 * app's own /api/videos/[videoId]/stream route, never a raw storage URL, so
 * ownership and soft-delete checks are enforced on every access regardless
 * of which provider is behind this interface. See
 * docs/VIDEO_INTELLIGENCE.md "Storage architecture" for the full reasoning.
 *
 * Swap in a real object-storage implementation (S3/R2/GCS) later by
 * implementing this interface — nothing above this layer knows or cares
 * that videos currently live on local disk.
 */
export interface VideoStorageProvider {
  /**
   * Reserves a storage key ahead of having a Video row. Takes only
   * athleteId (for a human-inspectable layout) and an extension, not a
   * videoId — the key must exist before the Video row does (createUploadTarget
   * runs first, so the row can be created with its final, unique
   * storageKey in one write instead of a create-then-update race).
   */
  createUploadTarget(input: { athleteId: string; extension: string }): Promise<{ storageKey: string }>;
  /** Streams `source` into storage, hashing as it goes. Never buffers the whole file in memory. */
  upload(storageKey: string, source: Readable, options?: { maxBytes?: number }): Promise<{ byteSize: number; sha256: string }>;
  retrieve(
    storageKey: string,
    range?: { start: number; end?: number },
  ): Promise<{ stream: Readable; totalBytes: number }>;
  exists(storageKey: string): Promise<boolean>;
  delete(storageKey: string): Promise<void>;
  /**
   * Absolute filesystem path for this key, if (and only if) this storage
   * backend is a local filesystem the current process can read directly —
   * used by anything that needs a real path rather than a stream (ffprobe,
   * and the M5 CV service's single-host shared-filesystem assumption, see
   * docs/CV_ARCHITECTURE.md "Deployment"). Returns null for a backend
   * without a shared filesystem (e.g. a future S3 provider), so callers
   * fail explicitly instead of assuming a path exists.
   */
  getLocalFilesystemPath(storageKey: string): string | null;
}

// Deliberately not overridable via env var: a dynamically-computed fs path
// here defeats Next.js's static file-tracing for serverless bundling (it
// falls back to tracing the *entire* project). Local disk is a documented
// dev-only stand-in anyway (see docs/VIDEO_INTELLIGENCE.md "Storage
// architecture") — a real deployment swaps the whole provider, not this path.
const STORAGE_ROOT = path.join(process.cwd(), "storage", "videos");

export class VideoTooLargeError extends Error {
  constructor(public readonly maxBytes: number) {
    super(`Upload exceeded the ${maxBytes}-byte limit.`);
    this.name = "VideoTooLargeError";
  }
}

export class LocalFilesystemVideoStorageProvider implements VideoStorageProvider {
  async createUploadTarget({
    athleteId,
    extension,
  }: {
    athleteId: string;
    extension: string;
  }): Promise<{ storageKey: string }> {
    // athleteId is always server-derived from the session, never client
    // input, so this key is safe by construction; resolvePath still
    // re-checks it below as defense in depth.
    const safeExtension = extension.replace(/[^a-z0-9.]/gi, "").slice(0, 10) || ".bin";
    return { storageKey: `${athleteId}/${randomUUID()}${safeExtension}` };
  }

  private resolvePath(storageKey: string): string {
    const resolved = path.resolve(STORAGE_ROOT, storageKey);
    if (resolved !== STORAGE_ROOT && !resolved.startsWith(STORAGE_ROOT + path.sep)) {
      throw new Error(`Refusing to resolve a storage key outside the storage root: ${storageKey}`);
    }
    return resolved;
  }

  async upload(
    storageKey: string,
    source: Readable,
    options?: { maxBytes?: number },
  ): Promise<{ byteSize: number; sha256: string }> {
    const absolutePath = this.resolvePath(storageKey);
    await mkdir(path.dirname(absolutePath), { recursive: true });

    const hash = createHash("sha256");
    let byteSize = 0;
    // Enforces the size limit against the bytes actually received, not a
    // client-supplied Content-Length header (which could be missing or
    // wrong) — the one place every upload's bytes truly pass through.
    const hashingTap = new Transform({
      transform(chunk: Buffer, _encoding, callback) {
        byteSize += chunk.length;
        if (options?.maxBytes && byteSize > options.maxBytes) {
          callback(new VideoTooLargeError(options.maxBytes));
          return;
        }
        hash.update(chunk);
        callback(null, chunk);
      },
    });

    try {
      await pipeline(source, hashingTap, createWriteStream(absolutePath));
    } catch (error) {
      await unlink(absolutePath).catch(() => {});
      throw error;
    }
    return { byteSize, sha256: hash.digest("hex") };
  }

  async retrieve(
    storageKey: string,
    range?: { start: number; end?: number },
  ): Promise<{ stream: Readable; totalBytes: number }> {
    const absolutePath = this.resolvePath(storageKey);
    const stats = await stat(absolutePath);
    const stream = range
      ? createReadStream(absolutePath, { start: range.start, end: range.end })
      : createReadStream(absolutePath);
    return { stream, totalBytes: stats.size };
  }

  async exists(storageKey: string): Promise<boolean> {
    try {
      await stat(this.resolvePath(storageKey));
      return true;
    } catch {
      return false;
    }
  }

  async delete(storageKey: string): Promise<void> {
    try {
      await unlink(this.resolvePath(storageKey));
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
  }

  getLocalFilesystemPath(storageKey: string): string | null {
    return this.resolvePath(storageKey);
  }
}

let cachedProvider: VideoStorageProvider | null = null;

export function getVideoStorageProvider(): VideoStorageProvider {
  if (!cachedProvider) {
    cachedProvider = new LocalFilesystemVideoStorageProvider();
  }
  return cachedProvider;
}
