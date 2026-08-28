-- CreateEnum
CREATE TYPE "QualityStatus" AS ENUM ('GOOD', 'ACCEPTABLE', 'POOR', 'UNUSABLE');

-- CreateEnum
CREATE TYPE "CalibrationStatus" AS ENUM ('NOT_ATTEMPTED', 'SUCCESS', 'PARTIAL', 'FAILED', 'LOW_CONFIDENCE');

-- CreateEnum
CREATE TYPE "PlayerIdentity" AS ENUM ('ATHLETE', 'OPPONENT', 'UNKNOWN');

-- AlterTable
ALTER TABLE "VideoJob" ADD COLUMN     "resultMetadata" JSONB;

-- CreateTable
CREATE TABLE "VideoQualityAssessment" (
    "id" TEXT NOT NULL,
    "videoId" TEXT NOT NULL,
    "videoJobId" TEXT NOT NULL,
    "status" "QualityStatus" NOT NULL,
    "reasons" TEXT[],
    "measuredWidth" INTEGER,
    "measuredHeight" INTEGER,
    "measuredFrameRate" DOUBLE PRECISION,
    "measuredDurationSeconds" DOUBLE PRECISION,
    "framesSampled" INTEGER NOT NULL,
    "blankFrameRatio" DOUBLE PRECISION,
    "decodeFailureRatio" DOUBLE PRECISION,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "VideoQualityAssessment_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "CourtCalibration" (
    "id" TEXT NOT NULL,
    "videoId" TEXT NOT NULL,
    "videoJobId" TEXT NOT NULL,
    "status" "CalibrationStatus" NOT NULL,
    "confidence" "ConfidenceLevel",
    "courtCornersPx" JSONB,
    "homography" JSONB,
    "sourceFrameTimestamps" DOUBLE PRECISION[],
    "warnings" TEXT[],
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "CourtCalibration_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PlayerTrack" (
    "id" TEXT NOT NULL,
    "videoId" TEXT NOT NULL,
    "videoJobId" TEXT NOT NULL,
    "engineTrackId" INTEGER NOT NULL,
    "identity" "PlayerIdentity" NOT NULL DEFAULT 'UNKNOWN',
    "identitySource" TEXT NOT NULL DEFAULT 'HEURISTIC',
    "identityConfirmedByUserId" TEXT,
    "identityConfirmedAt" TIMESTAMP(3),
    "confidence" "ConfidenceLevel" NOT NULL,
    "startTimestampSeconds" DOUBLE PRECISION NOT NULL,
    "endTimestampSeconds" DOUBLE PRECISION NOT NULL,
    "detections" JSONB NOT NULL,
    "gaps" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "PlayerTrack_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "VideoQualityAssessment_videoJobId_key" ON "VideoQualityAssessment"("videoJobId");

-- CreateIndex
CREATE INDEX "VideoQualityAssessment_videoId_idx" ON "VideoQualityAssessment"("videoId");

-- CreateIndex
CREATE UNIQUE INDEX "CourtCalibration_videoJobId_key" ON "CourtCalibration"("videoJobId");

-- CreateIndex
CREATE INDEX "CourtCalibration_videoId_idx" ON "CourtCalibration"("videoId");

-- CreateIndex
CREATE INDEX "PlayerTrack_videoId_idx" ON "PlayerTrack"("videoId");

-- CreateIndex
CREATE INDEX "PlayerTrack_videoJobId_idx" ON "PlayerTrack"("videoJobId");

-- AddForeignKey
ALTER TABLE "VideoQualityAssessment" ADD CONSTRAINT "VideoQualityAssessment_videoId_fkey" FOREIGN KEY ("videoId") REFERENCES "Video"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "VideoQualityAssessment" ADD CONSTRAINT "VideoQualityAssessment_videoJobId_fkey" FOREIGN KEY ("videoJobId") REFERENCES "VideoJob"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "CourtCalibration" ADD CONSTRAINT "CourtCalibration_videoId_fkey" FOREIGN KEY ("videoId") REFERENCES "Video"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "CourtCalibration" ADD CONSTRAINT "CourtCalibration_videoJobId_fkey" FOREIGN KEY ("videoJobId") REFERENCES "VideoJob"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PlayerTrack" ADD CONSTRAINT "PlayerTrack_videoId_fkey" FOREIGN KEY ("videoId") REFERENCES "Video"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PlayerTrack" ADD CONSTRAINT "PlayerTrack_videoJobId_fkey" FOREIGN KEY ("videoJobId") REFERENCES "VideoJob"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PlayerTrack" ADD CONSTRAINT "PlayerTrack_identityConfirmedByUserId_fkey" FOREIGN KEY ("identityConfirmedByUserId") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;
