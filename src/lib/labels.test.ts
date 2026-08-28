import { describe, expect, it } from "vitest";
import {
  AssessmentStatus,
  ConfidenceLevel,
  GoalCategory,
  GoalPriority,
  GoalStatus,
  SkillCategory,
  SkillLevel,
  Trend,
} from "@/generated/prisma/client";
import {
  assessmentStatusLabel,
  confidenceLabel,
  confidenceTone,
  goalCategoryLabel,
  goalPriorityLabel,
  goalStatusLabel,
  skillCategoryLabel,
  skillLevelLabel,
  trendLabel,
  trendTone,
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
});
