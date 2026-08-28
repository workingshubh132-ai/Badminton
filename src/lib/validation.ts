import { z } from "zod";

export const signupSchema = z.object({
  name: z.string().trim().min(2, "Name is too short").max(100),
  email: z.email("Enter a valid email address").trim().toLowerCase(),
  password: z.string().min(8, "Password must be at least 8 characters").max(200),
});

export const loginSchema = z.object({
  email: z.email("Enter a valid email address").trim().toLowerCase(),
  password: z.string().min(1, "Password is required"),
});

const competitiveLevels = [
  "BEGINNER",
  "INTERMEDIATE",
  "CLUB_COMPETITIVE",
  "DISTRICT_OR_STATE_COMPETITIVE",
  "NATIONAL_COMPETITIVE",
  "INTERNATIONAL_ASPIRANT",
] as const;

const hands = ["LEFT", "RIGHT"] as const;

export const athleteProfileSchema = z.object({
  fullName: z.string().trim().min(2, "Name is too short").max(100),
  dateOfBirth: z.coerce.date().optional().or(z.literal("").transform(() => undefined)),
  dominantHand: z.enum(hands).optional().or(z.literal("").transform(() => undefined)),
  currentLevel: z.enum(competitiveLevels),
  longTermGoal: z.string().trim().max(500).optional().or(z.literal("").transform(() => undefined)),
  academyName: z.string().trim().max(200).optional().or(z.literal("").transform(() => undefined)),
  coachName: z.string().trim().max(200).optional().or(z.literal("").transform(() => undefined)),
  heightCm: z.coerce.number().int().min(100).max(230).optional().or(z.literal("").transform(() => undefined)),
  weightKg: z.coerce.number().min(25).max(200).optional().or(z.literal("").transform(() => undefined)),
  yearsPlaying: z.coerce.number().int().min(0).max(80).optional().or(z.literal("").transform(() => undefined)),
  trainingDaysPerWeek: z.coerce.number().int().min(0).max(14).optional().or(z.literal("").transform(() => undefined)),
  playingStyleNotes: z.string().trim().max(1000).optional().or(z.literal("").transform(() => undefined)),
  bio: z.string().trim().max(1000).optional().or(z.literal("").transform(() => undefined)),
});

const goalCategories = ["TECHNICAL", "MOVEMENT", "TACTICAL", "PHYSICAL", "MENTAL", "COMPETITION"] as const;
const goalPriorities = ["LOW", "MEDIUM", "HIGH"] as const;

export const goalSchema = z.object({
  title: z.string().trim().min(3, "Title is too short").max(150),
  description: z.string().trim().max(1000).optional().or(z.literal("").transform(() => undefined)),
  category: z.enum(goalCategories),
  priority: z.enum(goalPriorities),
  targetDate: z.coerce.date().optional().or(z.literal("").transform(() => undefined)),
});

const skillLevels = ["EMERGING", "DEVELOPING", "SOLID", "STRONG", "ADVANCED"] as const;
const confidenceLevels = ["VERY_LOW", "LOW", "MODERATE", "HIGH", "VERY_HIGH"] as const;
const trends = ["IMPROVING", "STABLE", "DECLINING", "UNKNOWN"] as const;
const evidenceTypes = [
  "SELF_NOTE",
  "TRAINING_OBSERVATION",
  "COACH_NOTE",
  "MATCH_OBSERVATION",
  "VIDEO_REVIEW",
  "STATISTIC",
] as const;

export const evidenceOnlySchema = z.object({
  evidenceType: z.enum(evidenceTypes),
  evidenceDescription: z
    .string()
    .trim()
    .min(10, "Describe the specific evidence (what happened, when) in at least 10 characters")
    .max(1000),
});

export const assessmentSchema = z.object({
  skillId: z.string().min(1, "Select a skill"),
  level: z.enum(skillLevels),
  confidence: z.enum(confidenceLevels),
  trend: z.enum(trends),
  summary: z
    .string()
    .trim()
    .min(20, "Explain your reasoning in at least 20 characters — a bare rating isn't evidence")
    .max(1000),
  evidenceType: z.enum(evidenceTypes),
  evidenceDescription: z
    .string()
    .trim()
    .min(10, "Describe the specific evidence (what happened, when) in at least 10 characters")
    .max(1000),
});

const matchResults = ["WIN", "LOSS", "UNKNOWN"] as const;

export const matchSchema = z.object({
  opponentName: z.string().trim().max(150).optional().or(z.literal("").transform(() => undefined)),
  playedAt: z.coerce.date(),
  competitionName: z.string().trim().max(200).optional().or(z.literal("").transform(() => undefined)),
  format: z.string().trim().max(100).optional().or(z.literal("").transform(() => undefined)),
  result: z.enum(matchResults),
  score: z.string().trim().max(200).optional().or(z.literal("").transform(() => undefined)),
  notes: z.string().trim().max(2000).optional().or(z.literal("").transform(() => undefined)),
});

const videoTypes = ["MATCH", "TRAINING", "TECHNIQUE", "OTHER"] as const;

export const videoUploadMetaSchema = z.object({
  videoType: z.enum(videoTypes),
  matchId: z.string().trim().min(1).optional().or(z.literal("").transform(() => undefined)),
  originalFilename: z.string().trim().min(1).max(255),
  clientMimeType: z.string().trim().max(100).optional().or(z.literal("").transform(() => undefined)),
});

// Evidence attached directly to a Match or Video (the generalized evidence
// model, M4) rather than to a SkillAssessment. Optional timestamp lets a
// player cite a specific moment in a video.
export const subjectEvidenceSchema = evidenceOnlySchema.extend({
  timestampSeconds: z.coerce
    .number()
    .min(0)
    .optional()
    .or(z.literal("").transform(() => undefined)),
});

export type SignupInput = z.infer<typeof signupSchema>;
export type LoginInput = z.infer<typeof loginSchema>;
export type AthleteProfileInput = z.infer<typeof athleteProfileSchema>;
export type GoalInput = z.infer<typeof goalSchema>;
export type AssessmentInput = z.infer<typeof assessmentSchema>;
export type MatchInput = z.infer<typeof matchSchema>;
export type VideoUploadMetaInput = z.infer<typeof videoUploadMetaSchema>;
export type SubjectEvidenceInput = z.infer<typeof subjectEvidenceSchema>;
