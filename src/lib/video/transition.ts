import { db } from "@/lib/db";
import { assertValidVideoStatusTransition } from "@/lib/video/state-machine";
import type { Prisma, Video, VideoStatus } from "@/generated/prisma/client";

/**
 * The one place allowed to write Video.status. Every caller in this codebase
 * (job-runner, the upload route, video actions) goes through this so
 * assertValidVideoStatusTransition is never bypassed — see
 * lib/video/state-machine.ts for the transition table itself, kept
 * dependency-free there so it stays trivially unit-testable.
 */
export async function setVideoStatus(
  video: Pick<Video, "id" | "status">,
  to: VideoStatus,
  data: Prisma.VideoUpdateInput = {},
): Promise<Video> {
  assertValidVideoStatusTransition(video.status, to);
  return db.video.update({ where: { id: video.id }, data: { ...data, status: to } });
}
