import { describe, expect, it, beforeAll } from "vitest";

beforeAll(() => {
  process.env.AUTH_SECRET = process.env.AUTH_SECRET ?? "test-secret-for-vitest-only";
});

describe("video access tokens", () => {
  it("a freshly created token verifies for the same videoId", async () => {
    const { createVideoAccessToken, verifyVideoAccessToken } = await import("@/lib/video/access");
    const token = createVideoAccessToken("video_123", 60);
    expect(verifyVideoAccessToken("video_123", token)).toBe(true);
  });

  it("rejects a token created for a different videoId", async () => {
    const { createVideoAccessToken, verifyVideoAccessToken } = await import("@/lib/video/access");
    const token = createVideoAccessToken("video_123", 60);
    expect(verifyVideoAccessToken("video_456", token)).toBe(false);
  });

  it("rejects an expired token", async () => {
    const { createVideoAccessToken, verifyVideoAccessToken } = await import("@/lib/video/access");
    const token = createVideoAccessToken("video_123", -1); // already expired
    expect(verifyVideoAccessToken("video_123", token)).toBe(false);
  });

  it("rejects a tampered signature", async () => {
    const { createVideoAccessToken, verifyVideoAccessToken } = await import("@/lib/video/access");
    const token = createVideoAccessToken("video_123", 60);
    const [exp] = token.split(".");
    const tampered = `${exp}.0000000000000000000000000000000000000000000000000000000000000000`;
    expect(verifyVideoAccessToken("video_123", tampered)).toBe(false);
  });

  it("rejects malformed tokens", async () => {
    const { verifyVideoAccessToken } = await import("@/lib/video/access");
    expect(verifyVideoAccessToken("video_123", null)).toBe(false);
    expect(verifyVideoAccessToken("video_123", "")).toBe(false);
    expect(verifyVideoAccessToken("video_123", "not-a-real-token")).toBe(false);
    expect(verifyVideoAccessToken("video_123", "123")).toBe(false);
  });

  it("buildVideoStreamUrl points at the app's own stream route with a token", async () => {
    const { buildVideoStreamUrl } = await import("@/lib/video/access");
    const url = buildVideoStreamUrl("video_123", 60);
    expect(url).toMatch(/^\/api\/videos\/video_123\/stream\?token=/);
  });
});
