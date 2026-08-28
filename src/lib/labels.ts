import type {
  AssessmentStatus,
  ConfidenceLevel,
  GoalCategory,
  GoalPriority,
  GoalStatus,
  SkillCategory,
  SkillLevel,
  Trend,
} from "@/generated/prisma/client";

export const confidenceLabel: Record<ConfidenceLevel, string> = {
  VERY_LOW: "Very low confidence",
  LOW: "Low confidence",
  MODERATE: "Moderate confidence",
  HIGH: "High confidence",
  VERY_HIGH: "Very high confidence",
};

export const confidenceTone: Record<ConfidenceLevel, "danger" | "warning" | "neutral" | "info" | "success"> = {
  VERY_LOW: "danger",
  LOW: "warning",
  MODERATE: "neutral",
  HIGH: "info",
  VERY_HIGH: "success",
};

export const skillLevelLabel: Record<SkillLevel, string> = {
  EMERGING: "Emerging",
  DEVELOPING: "Developing",
  SOLID: "Solid",
  STRONG: "Strong",
  ADVANCED: "Advanced",
};

export const trendLabel: Record<Trend, string> = {
  IMPROVING: "Improving",
  STABLE: "Stable",
  DECLINING: "Declining",
  UNKNOWN: "Trend unknown",
};

export const trendTone: Record<Trend, "success" | "neutral" | "danger" | "warning"> = {
  IMPROVING: "success",
  STABLE: "neutral",
  DECLINING: "danger",
  UNKNOWN: "warning",
};

export const assessmentStatusLabel: Record<AssessmentStatus, string> = {
  PROVISIONAL: "Provisional",
  CONFIRMED: "Confirmed",
};

export const skillCategoryLabel: Record<SkillCategory, string> = {
  TECHNICAL: "Technical",
  MOVEMENT: "Movement",
  TACTICAL: "Tactical",
  PHYSICAL: "Physical",
  MENTAL: "Mental / Competitive",
};

export const goalCategoryLabel: Record<GoalCategory, string> = {
  TECHNICAL: "Technical",
  MOVEMENT: "Movement",
  TACTICAL: "Tactical",
  PHYSICAL: "Physical",
  MENTAL: "Mental",
  COMPETITION: "Competition",
};

export const goalPriorityLabel: Record<GoalPriority, string> = {
  LOW: "Low priority",
  MEDIUM: "Medium priority",
  HIGH: "High priority",
};

export const goalStatusLabel: Record<GoalStatus, string> = {
  ACTIVE: "Active",
  ACHIEVED: "Achieved",
  ABANDONED: "Abandoned",
};

export const competitiveLevelLabel: Record<string, string> = {
  BEGINNER: "Beginner",
  INTERMEDIATE: "Intermediate",
  CLUB_COMPETITIVE: "Club competitive",
  DISTRICT_OR_STATE_COMPETITIVE: "District / State competitive",
  NATIONAL_COMPETITIVE: "National competitive",
  INTERNATIONAL_ASPIRANT: "International aspirant",
};
