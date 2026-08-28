import { describe, expect, it } from "vitest";
import {
  AssessmentStatus,
  ConfidenceLevel,
  EvidenceSource,
  GoalCategory,
  GoalPriority,
  GoalStatus,
  MatchResult,
  MatchStatus,
  SkillCategory,
  SkillLevel,
  Trend,
  VideoJobStatus,
  VideoJobType,
  VideoStatus,
  VideoType,
} from "@/generated/prisma/client";
import {
  assessmentStatusLabel,
  confidenceLabel,
  confidenceTone,
  evidenceSourceLabel,
  goalCategoryLabel,
  goalPriorityLabel,
  goalStatusLabel,
  matchResultLabel,
  matchResultTone,
  matchStatusLabel,
  skillCategoryLabel,
  skillLevelLabel,
  trendLabel,
  trendTone,
  videoJobStatusLabel,
  videoJobStatusTone,
  videoJobTypeLabel,
  videoStatusExplanation,
  videoStatusLabel,
  videoStatusTone,
  videoTypeLabel,
} from "@/lib/labels";

// The UI never falls back to the raw enum key for a value the schema defines — every value
// must have an explicit human label. This test fails loudly the moment a new enum value is
// added to schema.prisma without updating labels.ts, instead of silently rendering "SOME_ENUM_KEY"
// in the product.
function expectCompleteMap<T extends string>(enumObj: Record<string, T>, map: Record<T, unknown>) {
  for (const value of Object.values(enumObj)) {
    expect(map, `missing label for "${value}"`).toHaveProperty(value);
  }
}

describe("label maps cover every enum value", () => {
  it("ConfidenceLevel", () => {
    expectCompleteMap(ConfidenceLevel, confidenceLabel);
    expectCompleteMap(ConfidenceLevel, confidenceTone);
  });

  it("SkillLevel", () => {
    expectCompleteMap(SkillLevel, skillLevelLabel);
  });

  it("Trend", () => {
    expectCompleteMap(Trend, trendLabel);
    expectCompleteMap(Trend, trendTone);
  });

  it("AssessmentStatus", () => {
    expectCompleteMap(AssessmentStatus, assessmentStatusLabel);
  });

  it("SkillCategory", () => {
    expectCompleteMap(SkillCategory, skillCategoryLabel);
  });

  it("GoalCategory / GoalPriority / GoalStatus", () => {
    expectCompleteMap(GoalCategory, goalCategoryLabel);
    expectCompleteMap(GoalPriority, goalPriorityLabel);
    expectCompleteMap(GoalStatus, goalStatusLabel);
  });

  it("VideoType", () => {
    expectCompleteMap(VideoType, videoTypeLabel);
  });

  it("VideoStatus", () => {
    expectCompleteMap(VideoStatus, videoStatusLabel);
    expectCompleteMap(VideoStatus, videoStatusTone);
    expectCompleteMap(VideoStatus, videoStatusExplanation);
  });

  it("MatchResult / MatchStatus", () => {
    expectCompleteMap(MatchResult, matchResultLabel);
    expectCompleteMap(MatchResult, matchResultTone);
    expectCompleteMap(MatchStatus, matchStatusLabel);
  });

  it("VideoJobType / VideoJobStatus", () => {
    expectCompleteMap(VideoJobType, videoJobTypeLabel);
    expectCompleteMap(VideoJobStatus, videoJobStatusLabel);
    expectCompleteMap(VideoJobStatus, videoJobStatusTone);
  });

  it("EvidenceSource", () => {
    expectCompleteMap(EvidenceSource, evidenceSourceLabel);
  });
});
