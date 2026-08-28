import { describe, expect, it } from "vitest";
import {
  assessmentSchema,
  goalSchema,
  loginSchema,
  matchSchema,
  signupSchema,
  subjectEvidenceSchema,
  videoUploadMetaSchema,
} from "@/lib/validation";

describe("signupSchema", () => {
  it("accepts a valid signup", () => {
    const result = signupSchema.safeParse({
      name: "Jamie Player",
      email: "Jamie@Example.com",
      password: "correcthorsebattery",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      // Email is normalized to lowercase so lookups are case-insensitive.
      expect(result.data.email).toBe("jamie@example.com");
    }
  });

  it("rejects a password under 8 characters", () => {
    const result = signupSchema.safeParse({
      name: "Jamie Player",
      email: "jamie@example.com",
      password: "short1",
    });
    expect(result.success).toBe(false);
  });

  it("rejects an invalid email", () => {
    const result = signupSchema.safeParse({
      name: "Jamie Player",
      email: "not-an-email",
      password: "correcthorsebattery",
    });
    expect(result.success).toBe(false);
  });
});

describe("loginSchema", () => {
  it("requires a non-empty password but does not enforce a minimum length", () => {
    // Login must not reject a legacy short password — only signup enforces the minimum.
    expect(loginSchema.safeParse({ email: "a@b.com", password: "x" }).success).toBe(true);
    expect(loginSchema.safeParse({ email: "a@b.com", password: "" }).success).toBe(false);
  });
});

describe("goalSchema", () => {
  it("requires a title of at least 3 characters", () => {
    expect(
      goalSchema.safeParse({ title: "ab", category: "TECHNICAL", priority: "MEDIUM" }).success,
    ).toBe(false);
    expect(
      goalSchema.safeParse({ title: "Fix backhand", category: "TECHNICAL", priority: "MEDIUM" })
        .success,
    ).toBe(true);
  });

  it("rejects an unknown category", () => {
    const result = goalSchema.safeParse({
      title: "Fix backhand",
      category: "NOT_A_REAL_CATEGORY",
      priority: "MEDIUM",
    });
    expect(result.success).toBe(false);
  });
});

describe("assessmentSchema", () => {
  const base = {
    skillId: "skill_1",
    level: "DEVELOPING",
    confidence: "LOW",
    trend: "UNKNOWN",
    evidenceType: "SELF_NOTE",
  };

  it("rejects a bare rating with no real reasoning or evidence", () => {
    // This is the schema-level enforcement of "every assessment must store evidence" —
    // short/placeholder text should not be accepted as a substitute for an explanation.
    const result = assessmentSchema.safeParse({
      ...base,
      summary: "weak",
      evidenceDescription: "bad",
    });
    expect(result.success).toBe(false);
  });

  it("accepts a properly justified assessment", () => {
    const result = assessmentSchema.safeParse({
      ...base,
      summary: "Smash gets read easily because preparation is slow and telegraphed.",
      evidenceDescription: "Opponent blocked 4 of 5 smashes in the Aug 20 match by reading early.",
    });
    expect(result.success).toBe(true);
  });

  it("rejects an unknown confidence level", () => {
    const result = assessmentSchema.safeParse({
      ...base,
      confidence: "SUPER_DUPER_HIGH",
      summary: "Smash gets read easily because preparation is slow and telegraphed.",
      evidenceDescription: "Opponent blocked 4 of 5 smashes in the Aug 20 match by reading early.",
    });
    expect(result.success).toBe(false);
  });
});

describe("matchSchema", () => {
  it("accepts a minimal match with just a date and result", () => {
    const result = matchSchema.safeParse({ playedAt: "2026-08-20", result: "WIN" });
    expect(result.success).toBe(true);
  });

  it("requires a playedAt date", () => {
    const result = matchSchema.safeParse({ result: "WIN" });
    expect(result.success).toBe(false);
  });

  it("rejects an unknown result value", () => {
    const result = matchSchema.safeParse({ playedAt: "2026-08-20", result: "DRAW" });
    expect(result.success).toBe(false);
  });
});

describe("videoUploadMetaSchema", () => {
  it("accepts MATCH/TRAINING/TECHNIQUE/OTHER video types", () => {
    for (const videoType of ["MATCH", "TRAINING", "TECHNIQUE", "OTHER"]) {
      const result = videoUploadMetaSchema.safeParse({ videoType, originalFilename: "clip.mp4" });
      expect(result.success).toBe(true);
    }
  });

  it("rejects an unknown video type", () => {
    const result = videoUploadMetaSchema.safeParse({ videoType: "HIGHLIGHT_REEL", originalFilename: "clip.mp4" });
    expect(result.success).toBe(false);
  });

  it("requires a non-empty filename", () => {
    const result = videoUploadMetaSchema.safeParse({ videoType: "MATCH", originalFilename: "" });
    expect(result.success).toBe(false);
  });
});

describe("subjectEvidenceSchema", () => {
  it("accepts evidence with an optional numeric timestamp", () => {
    const result = subjectEvidenceSchema.safeParse({
      evidenceType: "VIDEO_REVIEW",
      evidenceDescription: "At 1:32 I completely lost my split-step before the smash.",
      timestampSeconds: "92.5",
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.timestampSeconds).toBe(92.5);
  });

  it("accepts evidence with no timestamp", () => {
    const result = subjectEvidenceSchema.safeParse({
      evidenceType: "SELF_NOTE",
      evidenceDescription: "Consistently rushing the third shot after serving short.",
      timestampSeconds: "",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a negative timestamp", () => {
    const result = subjectEvidenceSchema.safeParse({
      evidenceType: "VIDEO_REVIEW",
      evidenceDescription: "At 1:32 I completely lost my split-step before the smash.",
      timestampSeconds: "-5",
    });
    expect(result.success).toBe(false);
  });
});
