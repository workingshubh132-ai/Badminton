import { afterEach, beforeEach, describe, expect, it } from "vitest";

describe("getCvEngine", () => {
  const originalUrl = process.env.CV_SERVICE_URL;

  beforeEach(() => {
    delete process.env.CV_SERVICE_URL;
  });

  afterEach(() => {
    if (originalUrl === undefined) delete process.env.CV_SERVICE_URL;
    else process.env.CV_SERVICE_URL = originalUrl;
  });

  it("falls back to NullCvEngine when CV_SERVICE_URL is not configured — the honest default", async () => {
    const { getCvEngine, NullCvEngine } = await import("@/lib/video/cv-engine");
    expect(getCvEngine()).toBeInstanceOf(NullCvEngine);
  });

  it("NullCvEngine reports status unavailable, never a fabricated result", async () => {
    const { NullCvEngine } = await import("@/lib/video/cv-engine");
    const result = await new NullCvEngine().analyze();
    expect(result.status).toBe("unavailable");
    expect(result.events).toEqual([]);
    expect(result.quality).toBeUndefined();
    expect(result.courtCalibration).toBeUndefined();
    expect(result.playerTracks).toBeUndefined();
  });

  it("returns PythonCvEngine when CV_SERVICE_URL is configured", async () => {
    process.env.CV_SERVICE_URL = "http://localhost:8000";
    const { getCvEngine } = await import("@/lib/video/cv-engine");
    const { PythonCvEngine } = await import("@/lib/video/python-cv-engine");
    expect(getCvEngine()).toBeInstanceOf(PythonCvEngine);
  });
});
