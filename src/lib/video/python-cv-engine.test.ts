import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { WireAnalysisResult } from "@/lib/video/python-cv-engine";

vi.mock("@/lib/video/storage", () => ({
  getVideoStorageProvider: () => ({
    getLocalFilesystemPath: (storageKey: string) => `/fake/storage/videos/${storageKey}`,
  }),
}));

const BASE_INPUT = {
  video: {
    id: "video_1",
    storageKey: "athlete_1/abc.mp4",
    durationSeconds: 10,
    width: 1280,
    height: 720,
  },
  athleteId: "athlete_1",
};

function completeWireResult(overrides: Partial<WireAnalysisResult> = {}): WireAnalysisResult {
  return {
    status: "completed",
    message: null,
    video: { width: 1280, height: 720, fps: 24, frame_count: 240, duration_seconds: 10, codec: "h264" },
    quality: {
      status: "GOOD",
      reasons: ["No quality issues detected in sampled frames."],
      metrics: { resolution: "1280x720", fps: 24, duration_seconds: 10, decode_failure_ratio: 0, sampled_frame_count: 20, blank_frame_ratio: 0 },
    },
    calibration: {
      status: "SUCCESS",
      confidence: "MODERATE",
      homography: [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
      ],
      court_corners_px: [
        [360, 120],
        [920, 120],
        [1100, 620],
        [180, 620],
      ],
      source_frame_timestamps: [0, 0.5, 1],
      warnings: [],
    },
    tracks: [
      {
        track_id: "550e8400-e29b-41d4-a716-446655440000",
        identity: "UNKNOWN",
        identity_source: "HEURISTIC",
        confidence: "MODERATE",
        detections: [
          {
            timestamp_seconds: 0.5,
            bbox: { x: 0.4, y: 0.3, width: 0.05, height: 0.15 },
            score: 0.7,
            confidence: "MODERATE",
            court_x: 3.05,
            court_y: 6.7,
          },
        ],
        gaps: [{ start_seconds: 1.0, end_seconds: 1.5, reason: "Not reliably detected (occlusion, motion blur, or left frame)." }],
      },
    ],
    warnings: [],
    processing_metadata: {
      engine_name: "badminton-cv-service",
      engine_version: "0.1.0",
      model_versions: { person_detector: "efficientdet_lite0-float32-1" },
      sampling_fps: 2.0,
      frames_sampled: 20,
      processing_seconds: 1.2,
      config: {},
      video_checksum_sha256: "a".repeat(64),
    },
    ...overrides,
  };
}

describe("mapWireResult", () => {
  it("translates a completed result field-for-field into the camelCase CV* shape", async () => {
    const { mapWireResult } = await import("@/lib/video/python-cv-engine");
    const result = mapWireResult(completeWireResult());

    expect(result.status).toBe("completed");
    expect(result.engineName).toBe("badminton-cv-service");
    expect(result.engineVersion).toBe("0.1.0");

    expect(result.quality).toEqual({
      status: "GOOD",
      reasons: ["No quality issues detected in sampled frames."],
      measuredWidth: 1280,
      measuredHeight: 720,
      measuredFrameRate: 24,
      measuredDurationSeconds: 10,
      framesSampled: 20,
      blankFrameRatio: 0,
      decodeFailureRatio: 0,
    });

    expect(result.courtCalibration).toEqual({
      status: "SUCCESS",
      confidence: "MODERATE",
      courtCornersPx: [
        [360, 120],
        [920, 120],
        [1100, 620],
        [180, 620],
      ],
      homography: [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
      ],
      sourceFrameTimestamps: [0, 0.5, 1],
      warnings: [],
    });

    expect(result.playerTracks).toHaveLength(1);
    expect(result.playerTracks?.[0]).toEqual({
      engineTrackId: "550e8400-e29b-41d4-a716-446655440000",
      identity: "UNKNOWN",
      identitySource: "HEURISTIC",
      confidence: "MODERATE",
      detections: [
        {
          timestampSeconds: 0.5,
          x: 0.4,
          y: 0.3,
          width: 0.05,
          height: 0.15,
          confidence: "MODERATE",
          courtX: 3.05,
          courtY: 6.7,
        },
      ],
      gaps: [{ startSeconds: 1.0, endSeconds: 1.5, reason: "Not reliably detected (occlusion, motion blur, or left frame)." }],
    });

    expect(result.processingMetadata).toEqual({
      modelVersions: { person_detector: "efficientdet_lite0-float32-1" },
      samplingFps: 2.0,
      framesSampled: 20,
      processingSeconds: 1.2,
      config: {},
      videoChecksumSha256: "a".repeat(64),
    });

    // M5 never writes Rally/Event rows — shot/rally intelligence is out of scope.
    expect(result.events).toEqual([]);
  });

  it("never fabricates court coordinates for a detection without them", async () => {
    const { mapWireResult } = await import("@/lib/video/python-cv-engine");
    const wire = completeWireResult();
    wire.tracks[0].detections[0].court_x = null;
    wire.tracks[0].detections[0].court_y = null;

    const result = mapWireResult(wire);
    expect(result.playerTracks?.[0].detections[0].courtX).toBeNull();
    expect(result.playerTracks?.[0].detections[0].courtY).toBeNull();
  });

  it("passes through a null calibration (FAILED) rather than inventing corners", async () => {
    const { mapWireResult } = await import("@/lib/video/python-cv-engine");
    const wire = completeWireResult({
      calibration: {
        status: "FAILED",
        confidence: null,
        homography: null,
        court_corners_px: null,
        source_frame_timestamps: [0, 0.5],
        warnings: ["No usable court boundary found in any sampled frame."],
      },
    });

    const result = mapWireResult(wire);
    expect(result.courtCalibration?.status).toBe("FAILED");
    expect(result.courtCalibration?.homography).toBeNull();
    expect(result.courtCalibration?.courtCornersPx).toBeNull();
  });
});

describe("PythonCvEngine.analyze", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("returns a completed result on a successful call, using the resolved local path", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => completeWireResult(),
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    const { PythonCvEngine } = await import("@/lib/video/python-cv-engine");
    const engine = new PythonCvEngine("http://localhost:8000");
    const result = await engine.analyze(BASE_INPUT);

    expect(result.status).toBe("completed");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/analyze");
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.video_path).toBe("/fake/storage/videos/athlete_1/abc.mp4");
    expect(body.video_id).toBe("video_1");
  });

  it("sends the internal token header when configured", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => completeWireResult() });
    global.fetch = fetchMock as unknown as typeof fetch;

    const { PythonCvEngine } = await import("@/lib/video/python-cv-engine");
    const engine = new PythonCvEngine("http://localhost:8000", "secret-token");
    await engine.analyze(BASE_INPUT);

    const [, init] = fetchMock.mock.calls[0];
    const headers = (init as RequestInit).headers as Record<string, string>;
    expect(headers["X-Internal-Token"]).toBe("secret-token");
  });

  it("returns status failed, never throwing, when the service is unreachable", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED")) as unknown as typeof fetch;

    const { PythonCvEngine } = await import("@/lib/video/python-cv-engine");
    const engine = new PythonCvEngine("http://localhost:8000");
    const result = await engine.analyze(BASE_INPUT);

    expect(result.status).toBe("failed");
    expect(result.message).toMatch(/could not reach/i);
    expect(result.playerTracks).toBeUndefined();
  });

  it("returns status failed on a non-2xx response, without pretending success", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => "internal error",
    }) as unknown as typeof fetch;

    const { PythonCvEngine } = await import("@/lib/video/python-cv-engine");
    const engine = new PythonCvEngine("http://localhost:8000");
    const result = await engine.analyze(BASE_INPUT);

    expect(result.status).toBe("failed");
    expect(result.message).toMatch(/HTTP 500/);
  });

  it("aborts and returns status failed after the configured timeout", async () => {
    global.fetch = vi.fn().mockImplementation((_url: string, init: RequestInit) => {
      return new Promise((_resolve, reject) => {
        init.signal?.addEventListener("abort", () => {
          const err = new Error("aborted");
          err.name = "AbortError";
          reject(err);
        });
      });
    }) as unknown as typeof fetch;

    const { PythonCvEngine } = await import("@/lib/video/python-cv-engine");
    const engine = new PythonCvEngine("http://localhost:8000", undefined, 10); // 10ms timeout
    const result = await engine.analyze(BASE_INPUT);

    expect(result.status).toBe("failed");
    expect(result.message).toMatch(/did not respond within/i);
  });

  it("returns unavailable, not failed, when the storage backend has no local path", async () => {
    vi.doMock("@/lib/video/storage", () => ({
      getVideoStorageProvider: () => ({ getLocalFilesystemPath: () => null }),
    }));
    const fetchMock = vi.fn();
    global.fetch = fetchMock as unknown as typeof fetch;

    const { PythonCvEngine } = await import("@/lib/video/python-cv-engine");
    const engine = new PythonCvEngine("http://localhost:8000");
    const result = await engine.analyze(BASE_INPUT);

    expect(result.status).toBe("unavailable");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
