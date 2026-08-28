-- CreateEnum
CREATE TYPE "UserRole" AS ENUM ('PLAYER', 'COACH', 'ADMIN');

-- CreateEnum
CREATE TYPE "Hand" AS ENUM ('LEFT', 'RIGHT');

-- CreateEnum
CREATE TYPE "CompetitiveLevel" AS ENUM ('BEGINNER', 'INTERMEDIATE', 'CLUB_COMPETITIVE', 'DISTRICT_OR_STATE_COMPETITIVE', 'NATIONAL_COMPETITIVE', 'INTERNATIONAL_ASPIRANT');

-- CreateEnum
CREATE TYPE "GoalCategory" AS ENUM ('TECHNICAL', 'MOVEMENT', 'TACTICAL', 'PHYSICAL', 'MENTAL', 'COMPETITION');

-- CreateEnum
CREATE TYPE "GoalPriority" AS ENUM ('LOW', 'MEDIUM', 'HIGH');

-- CreateEnum
CREATE TYPE "GoalStatus" AS ENUM ('ACTIVE', 'ACHIEVED', 'ABANDONED');

-- CreateEnum
CREATE TYPE "SkillCategory" AS ENUM ('TECHNICAL', 'MOVEMENT', 'TACTICAL', 'PHYSICAL', 'MENTAL');

-- CreateEnum
CREATE TYPE "SkillLevel" AS ENUM ('EMERGING', 'DEVELOPING', 'SOLID', 'STRONG', 'ADVANCED');

-- CreateEnum
CREATE TYPE "ConfidenceLevel" AS ENUM ('VERY_LOW', 'LOW', 'MODERATE', 'HIGH', 'VERY_HIGH');

-- CreateEnum
CREATE TYPE "Trend" AS ENUM ('IMPROVING', 'STABLE', 'DECLINING', 'UNKNOWN');

-- CreateEnum
CREATE TYPE "AssessmentStatus" AS ENUM ('PROVISIONAL', 'CONFIRMED');

-- CreateEnum
CREATE TYPE "AssessmentSource" AS ENUM ('SELF_REPORT', 'COACH_OBSERVATION', 'AI_VIDEO_ANALYSIS', 'MATCH_EVIDENCE');

-- CreateEnum
CREATE TYPE "EvidenceType" AS ENUM ('SELF_NOTE', 'TRAINING_OBSERVATION', 'COACH_NOTE', 'MATCH_OBSERVATION', 'VIDEO_REVIEW', 'STATISTIC');

-- CreateTable
CREATE TABLE "User" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "passwordHash" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "role" "UserRole" NOT NULL DEFAULT 'PLAYER',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Athlete" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "fullName" TEXT NOT NULL,
    "dateOfBirth" TIMESTAMP(3),
    "dominantHand" "Hand",
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Athlete_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "AthleteProfile" (
    "id" TEXT NOT NULL,
    "athleteId" TEXT NOT NULL,
    "currentLevel" "CompetitiveLevel" NOT NULL DEFAULT 'INTERMEDIATE',
    "longTermGoal" TEXT,
    "academyName" TEXT,
    "coachName" TEXT,
    "heightCm" INTEGER,
    "weightKg" DOUBLE PRECISION,
    "yearsPlaying" INTEGER,
    "trainingDaysPerWeek" INTEGER,
    "playingStyleNotes" TEXT,
    "bio" TEXT,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "AthleteProfile_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Goal" (
    "id" TEXT NOT NULL,
    "athleteId" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "description" TEXT,
    "category" "GoalCategory" NOT NULL,
    "priority" "GoalPriority" NOT NULL DEFAULT 'MEDIUM',
    "status" "GoalStatus" NOT NULL DEFAULT 'ACTIVE',
    "targetDate" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Goal_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Skill" (
    "id" TEXT NOT NULL,
    "key" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "category" "SkillCategory" NOT NULL,
    "description" TEXT,
    "sortOrder" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "Skill_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "SkillAssessment" (
    "id" TEXT NOT NULL,
    "athleteId" TEXT NOT NULL,
    "skillId" TEXT NOT NULL,
    "level" "SkillLevel" NOT NULL,
    "confidence" "ConfidenceLevel" NOT NULL,
    "trend" "Trend" NOT NULL DEFAULT 'UNKNOWN',
    "status" "AssessmentStatus" NOT NULL DEFAULT 'PROVISIONAL',
    "source" "AssessmentSource" NOT NULL DEFAULT 'SELF_REPORT',
    "summary" TEXT NOT NULL,
    "assessedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "createdByUserId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "SkillAssessment_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Evidence" (
    "id" TEXT NOT NULL,
    "skillAssessmentId" TEXT NOT NULL,
    "evidenceType" "EvidenceType" NOT NULL,
    "description" TEXT NOT NULL,
    "observedAt" TIMESTAMP(3),
    "createdByUserId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Evidence_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE UNIQUE INDEX "Athlete_userId_key" ON "Athlete"("userId");

-- CreateIndex
CREATE UNIQUE INDEX "AthleteProfile_athleteId_key" ON "AthleteProfile"("athleteId");

-- CreateIndex
CREATE INDEX "Goal_athleteId_status_idx" ON "Goal"("athleteId", "status");

-- CreateIndex
CREATE UNIQUE INDEX "Skill_key_key" ON "Skill"("key");

-- CreateIndex
CREATE INDEX "Skill_category_sortOrder_idx" ON "Skill"("category", "sortOrder");

-- CreateIndex
CREATE INDEX "SkillAssessment_athleteId_skillId_idx" ON "SkillAssessment"("athleteId", "skillId");

-- CreateIndex
CREATE INDEX "SkillAssessment_athleteId_status_idx" ON "SkillAssessment"("athleteId", "status");

-- CreateIndex
CREATE INDEX "Evidence_skillAssessmentId_idx" ON "Evidence"("skillAssessmentId");

-- AddForeignKey
ALTER TABLE "Athlete" ADD CONSTRAINT "Athlete_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AthleteProfile" ADD CONSTRAINT "AthleteProfile_athleteId_fkey" FOREIGN KEY ("athleteId") REFERENCES "Athlete"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Goal" ADD CONSTRAINT "Goal_athleteId_fkey" FOREIGN KEY ("athleteId") REFERENCES "Athlete"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SkillAssessment" ADD CONSTRAINT "SkillAssessment_athleteId_fkey" FOREIGN KEY ("athleteId") REFERENCES "Athlete"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SkillAssessment" ADD CONSTRAINT "SkillAssessment_skillId_fkey" FOREIGN KEY ("skillId") REFERENCES "Skill"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SkillAssessment" ADD CONSTRAINT "SkillAssessment_createdByUserId_fkey" FOREIGN KEY ("createdByUserId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Evidence" ADD CONSTRAINT "Evidence_skillAssessmentId_fkey" FOREIGN KEY ("skillAssessmentId") REFERENCES "SkillAssessment"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Evidence" ADD CONSTRAINT "Evidence_createdByUserId_fkey" FOREIGN KEY ("createdByUserId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
