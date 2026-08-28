/*
  Warnings:

  - Added the required column `athleteId` to the `Evidence` table without a default value. This is not possible if the table is not empty.

*/
-- CreateEnum
CREATE TYPE "EvidenceSource" AS ENUM ('PLAYER', 'COACH', 'CV_SYSTEM', 'AI_SYSTEM');

-- CreateEnum
CREATE TYPE "MatchResult" AS ENUM ('WIN', 'LOSS', 'UNKNOWN');

-- CreateEnum
CREATE TYPE "MatchStatus" AS ENUM ('UNPROCESSED', 'PROCESSING', 'PARTIALLY_PROCESSED', 'PROCESSED');

-- CreateEnum
CREATE TYPE "VideoType" AS ENUM ('MATCH', 'TRAINING', 'TECHNIQUE', 'OTHER');

-- CreateEnum
CREATE TYPE "VideoStatus" AS ENUM ('UPLOAD_PENDING', 'UPLOADING', 'UPLOADED', 'VALIDATING', 'VALID', 'INVALID', 'PROCESSING', 'READY_FOR_ANALYSIS', 'ANALYZING', 'ANALYZED', 'FAILED', 'DELETED');

-- CreateEnum
CREATE TYPE "VideoOrientation" AS ENUM ('LANDSCAPE', 'PORTRAIT', 'SQUARE');

-- CreateEnum
CREATE TYPE "RallyWinner" AS ENUM ('ATHLETE', 'OPPONENT', 'UNKNOWN');

-- CreateEnum
CREATE TYPE "RallyStatus" AS ENUM ('UNVERIFIED', 'CONFIRMED');

-- CreateEnum
CREATE TYPE "RallySource" AS ENUM ('MANUAL', 'CV_ANALYSIS');

-- CreateEnum
CREATE TYPE "EventCategory" AS ENUM ('MOVEMENT', 'SHOT', 'POSITION', 'CONTACT', 'COURT_EVENT', 'RALLY_EVENT', 'OTHER');

-- CreateEnum
CREATE TYPE "ShotType" AS ENUM ('SERVE', 'CLEAR', 'SMASH', 'DROP', 'SLICE', 'STICK_SMASH', 'NET', 'NET_KILL', 'LIFT', 'DRIVE', 'PUSH', 'BLOCK', 'DEFENCE', 'INTERCEPTION', 'OTHER');

-- CreateEnum
CREATE TYPE "EventSource" AS ENUM ('MANUAL', 'CV_ANALYSIS');

-- CreateEnum
CREATE TYPE "VideoJobType" AS ENUM ('PROCESSING', 'CV_ANALYSIS');

-- CreateEnum
CREATE TYPE "VideoJobStatus" AS ENUM ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'UNAVAILABLE');

-- AlterTable
-- athleteId is added nullable, backfilled from the only subject type that
-- existed pre-M4 (every row has skillAssessmentId set), then locked to
-- NOT NULL — see docs/DOMAIN_MODEL.md "Generalized evidence model (M4)".
ALTER TABLE "Evidence" ADD COLUMN     "athleteId" TEXT,
ADD COLUMN     "confidence" "ConfidenceLevel",
ADD COLUMN     "matchId" TEXT,
ADD COLUMN     "metadata" JSONB,
ADD COLUMN     "source" "EvidenceSource" NOT NULL DEFAULT 'PLAYER',
ADD COLUMN     "timestampSeconds" DOUBLE PRECISION,
ADD COLUMN     "videoId" TEXT,
ALTER COLUMN "skillAssessmentId" DROP NOT NULL;

UPDATE "Evidence" e
SET "athleteId" = sa."athleteId"
FROM "SkillAssessment" sa
WHERE e."skillAssessmentId" = sa."id" AND e."athleteId" IS NULL;

ALTER TABLE "Evidence" ALTER COLUMN "athleteId" SET NOT NULL;

-- CreateTable
CREATE TABLE "Match" (
    "id" TEXT NOT NULL,
    "athleteId" TEXT NOT NULL,
    "opponentName" TEXT,
    "playedAt" TIMESTAMP(3) NOT NULL,
    "competitionName" TEXT,
    "format" TEXT,
    "result" "MatchResult" NOT NULL DEFAULT 'UNKNOWN',
    "score" TEXT,
    "notes" TEXT,
    "status" "MatchStatus" NOT NULL DEFAULT 'UNPROCESSED',
    "createdByUserId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Match_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Video" (
    "id" TEXT NOT NULL,
    "athleteId" TEXT NOT NULL,
    "matchId" TEXT,
    "videoType" "VideoType" NOT NULL,
    "status" "VideoStatus" NOT NULL DEFAULT 'UPLOAD_PENDING',
    "originalFilename" TEXT NOT NULL,
    "clientMimeType" TEXT,
    "detectedFormat" TEXT,
    "byteSize" BIGINT,
    "checksumSha256" TEXT,
    "durationSeconds" DOUBLE PRECISION,
    "width" INTEGER,
    "height" INTEGER,
    "frameRate" DOUBLE PRECISION,
    "orientation" "VideoOrientation",
    "storageKey" TEXT NOT NULL,
    "invalidReason" TEXT,
    "failureReason" TEXT,
    "uploadedByUserId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "deletedAt" TIMESTAMP(3),

    CONSTRAINT "Video_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Rally" (
    "id" TEXT NOT NULL,
    "matchId" TEXT NOT NULL,
    "setNumber" INTEGER,
    "rallyNumber" INTEGER NOT NULL,
    "startTimestampSeconds" DOUBLE PRECISION,
    "endTimestampSeconds" DOUBLE PRECISION,
    "durationSeconds" DOUBLE PRECISION,
    "winner" "RallyWinner" NOT NULL DEFAULT 'UNKNOWN',
    "status" "RallyStatus" NOT NULL DEFAULT 'UNVERIFIED',
    "confidence" "ConfidenceLevel",
    "source" "RallySource" NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Rally_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Event" (
    "id" TEXT NOT NULL,
    "rallyId" TEXT,
    "videoId" TEXT,
    "category" "EventCategory" NOT NULL,
    "shotType" "ShotType",
    "timestampSeconds" DOUBLE PRECISION NOT NULL,
    "confidence" "ConfidenceLevel" NOT NULL,
    "source" "EventSource" NOT NULL,
    "courtX" DOUBLE PRECISION,
    "courtY" DOUBLE PRECISION,
    "metadata" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Event_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "VideoJob" (
    "id" TEXT NOT NULL,
    "videoId" TEXT NOT NULL,
    "type" "VideoJobType" NOT NULL,
    "status" "VideoJobStatus" NOT NULL DEFAULT 'PENDING',
    "progressPercent" INTEGER NOT NULL DEFAULT 0,
    "engineName" TEXT,
    "engineVersion" TEXT,
    "errorMessage" TEXT,
    "attempt" INTEGER NOT NULL DEFAULT 1,
    "maxAttempts" INTEGER NOT NULL DEFAULT 3,
    "startedAt" TIMESTAMP(3),
    "finishedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "VideoJob_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "Match_athleteId_playedAt_idx" ON "Match"("athleteId", "playedAt");

-- CreateIndex
CREATE UNIQUE INDEX "Video_storageKey_key" ON "Video"("storageKey");

-- CreateIndex
CREATE INDEX "Video_athleteId_status_idx" ON "Video"("athleteId", "status");

-- CreateIndex
CREATE INDEX "Video_matchId_idx" ON "Video"("matchId");

-- CreateIndex
CREATE INDEX "Rally_matchId_idx" ON "Rally"("matchId");

-- CreateIndex
CREATE UNIQUE INDEX "Rally_matchId_rallyNumber_key" ON "Rally"("matchId", "rallyNumber");

-- CreateIndex
CREATE INDEX "Event_rallyId_idx" ON "Event"("rallyId");

-- CreateIndex
CREATE INDEX "Event_videoId_timestampSeconds_idx" ON "Event"("videoId", "timestampSeconds");

-- CreateIndex
CREATE INDEX "VideoJob_videoId_type_idx" ON "VideoJob"("videoId", "type");

-- CreateIndex
CREATE INDEX "VideoJob_status_idx" ON "VideoJob"("status");

-- CreateIndex
CREATE INDEX "Evidence_matchId_idx" ON "Evidence"("matchId");

-- CreateIndex
CREATE INDEX "Evidence_videoId_idx" ON "Evidence"("videoId");

-- CreateIndex
CREATE INDEX "Evidence_athleteId_idx" ON "Evidence"("athleteId");

-- AddForeignKey
ALTER TABLE "Evidence" ADD CONSTRAINT "Evidence_athleteId_fkey" FOREIGN KEY ("athleteId") REFERENCES "Athlete"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Evidence" ADD CONSTRAINT "Evidence_matchId_fkey" FOREIGN KEY ("matchId") REFERENCES "Match"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Evidence" ADD CONSTRAINT "Evidence_videoId_fkey" FOREIGN KEY ("videoId") REFERENCES "Video"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Match" ADD CONSTRAINT "Match_athleteId_fkey" FOREIGN KEY ("athleteId") REFERENCES "Athlete"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Match" ADD CONSTRAINT "Match_createdByUserId_fkey" FOREIGN KEY ("createdByUserId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Video" ADD CONSTRAINT "Video_athleteId_fkey" FOREIGN KEY ("athleteId") REFERENCES "Athlete"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Video" ADD CONSTRAINT "Video_matchId_fkey" FOREIGN KEY ("matchId") REFERENCES "Match"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Video" ADD CONSTRAINT "Video_uploadedByUserId_fkey" FOREIGN KEY ("uploadedByUserId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Rally" ADD CONSTRAINT "Rally_matchId_fkey" FOREIGN KEY ("matchId") REFERENCES "Match"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Event" ADD CONSTRAINT "Event_rallyId_fkey" FOREIGN KEY ("rallyId") REFERENCES "Rally"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Event" ADD CONSTRAINT "Event_videoId_fkey" FOREIGN KEY ("videoId") REFERENCES "Video"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "VideoJob" ADD CONSTRAINT "VideoJob_videoId_fkey" FOREIGN KEY ("videoId") REFERENCES "Video"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- Data-integrity guarantee for the generalized evidence model: every
-- Evidence row must attach to exactly one subject. Not expressible in
-- schema.prisma directly (Prisma has no CHECK-constraint syntax), so it is
-- hand-added here — see docs/DOMAIN_MODEL.md "Generalized evidence model
-- (M4)" for why nullable per-subject FKs were chosen over a polymorphic
-- (subjectType, subjectId) pair.
ALTER TABLE "Evidence" ADD CONSTRAINT "evidence_exactly_one_subject" CHECK (
  (CASE WHEN "skillAssessmentId" IS NOT NULL THEN 1 ELSE 0 END) +
  (CASE WHEN "matchId" IS NOT NULL THEN 1 ELSE 0 END) +
  (CASE WHEN "videoId" IS NOT NULL THEN 1 ELSE 0 END) = 1
);
