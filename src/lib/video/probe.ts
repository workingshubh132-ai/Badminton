import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export interface VideoProbeData {
  durationSeconds: number | null;
  width: number | null;
  height: number | null;
  frameRate: number | null;
}

export type VideoProbeResult =
  | { ok: true; data: VideoProbeData }
  // The prober itself isn't available on this host (e.g. ffprobe not
  // installed). Not a defect in the video — never treated as invalid.
  | { ok: false; reason: "probe_unavailable"; detail: string }
  // The prober ran but could not make sense of the file — this DOES suggest
  // the video itself is unreadable/corrupt.
  | { ok: false; reason: "probe_failed"; detail: string };

interface FfprobeStream {
  codec_type?: string;
  width?: number;
  height?: number;
  avg_frame_rate?: string;
}

interface FfprobeOutput {
  format?: { duration?: string };
  streams?: FfprobeStream[];
}

/**
 * Extracts real duration/dimensions/frame-rate via ffprobe, if it's present
 * on the host. Never fabricates a value: every field is either what ffprobe
 * actually reported, or null. See docs/VIDEO_INTELLIGENCE.md "Metadata
 * extraction" for why this is optional-but-real rather than a hard
 * dependency.
 */
export async function probeVideoFile(absolutePath: string): Promise<VideoProbeResult> {
  try {
    const { stdout } = await execFileAsync(
      "ffprobe",
      ["-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", absolutePath],
      { timeout: 30_000, maxBuffer: 10 * 1024 * 1024 },
    );

    const parsed = JSON.parse(stdout) as FfprobeOutput;
    const videoStream = (parsed.streams ?? []).find((s) => s.codec_type === "video");
    if (!videoStream) {
      return { ok: false, reason: "probe_failed", detail: "No video stream found in the file." };
    }

    const durationRaw = parsed.format?.duration;
    const durationSeconds = durationRaw && !Number.isNaN(Number(durationRaw)) ? Number(durationRaw) : null;

    let frameRate: number | null = null;
    if (videoStream.avg_frame_rate && videoStream.avg_frame_rate !== "0/0") {
      const [num, den] = videoStream.avg_frame_rate.split("/").map(Number);
      if (den) frameRate = num / den;
    }

    return {
      ok: true,
      data: {
        durationSeconds,
        width: videoStream.width ?? null,
        height: videoStream.height ?? null,
        frameRate,
      },
    };
  } catch (error) {
    const code = (error as NodeJS.ErrnoException)?.code;
    if (code === "ENOENT") {
      return { ok: false, reason: "probe_unavailable", detail: "ffprobe is not installed on this host." };
    }
    const message = error instanceof Error ? error.message : String(error);
    return { ok: false, reason: "probe_failed", detail: message };
  }
}
