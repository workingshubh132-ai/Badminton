"use server";

import { revalidatePath } from "next/cache";
import { db } from "@/lib/db";
import { requireAthlete } from "@/lib/session";
import { getVideoStorageProvider } from "@/lib/video/storage";
import { runAnalysisPipeline, runProcessingPipeline } from "@/lib/video/job-runner";
import type { ActionState } from "@/lib/actions/types";

/** Loads a video the current athlete owns, or null. Never trusts a client-supplied athleteId. */
async function requireOwnedVideo(videoId: string) {
  const { user, athlete } = await requireAthlete();
  const video = await db.video.findFirst({ where: { id: videoId, athleteId: athlete.id } });
  return { user, athlete, video };
}

export async function deleteVideoAction(videoId: string): Promise<void> {
  const { video } = await requireOwnedVideo(videoId);
  if (!video || video.deletedAt) return;

  await getVideoStorageProvider().delete(video.storageKey);
  await db.video.update({
    where: { id: video.id },
    data: { status: "DELETED", deletedAt: new Date() },
  });

  revalidatePath("/videos");
  if (video.matchId) revalidatePath(`/matches/${video.matchId}`);
}

export async function retryVideoProcessingAction(
  _prev: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const videoId = String(formData.get("videoId") ?? "");
  const { video } = await requireOwnedVideo(videoId);
  if (!video || video.deletedAt) {
    return { ok: false, error: "Video not found." };
  }
  if (video.status !== "FAILED") {
    return { ok: false, error: "This video is not in a failed state." };
  }

  try {
    await runProcessingPipeline(video.id);
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Retry failed." };
  }

  revalidatePath(`/videos/${videoId}`);
  return { ok: true };
}

export async function requestReanalysisAction(
  _prev: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const videoId = String(formData.get("videoId") ?? "");
  const { video } = await requireOwnedVideo(videoId);
  if (!video || video.deletedAt) {
    return { ok: false, error: "Video not found." };
  }
  if (video.status !== "READY_FOR_ANALYSIS" && video.status !== "ANALYZED") {
    return { ok: false, error: "This video is not ready for analysis yet." };
  }

  await runAnalysisPipeline(video.id);

  revalidatePath(`/videos/${videoId}`);
  return { ok: true };
}

export async function associateVideoWithMatchAction(
  _prev: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const videoId = String(formData.get("videoId") ?? "");
  const matchId = String(formData.get("matchId") ?? "");
  const { athlete, video } = await requireOwnedVideo(videoId);
  if (!video || video.deletedAt) {
    return { ok: false, error: "Video not found." };
  }

  if (matchId) {
    const match = await db.match.findFirst({ where: { id: matchId, athleteId: athlete.id } });
    if (!match) {
      return { ok: false, error: "Match not found." };
    }
  }

  await db.video.update({ where: { id: video.id }, data: { matchId: matchId || null } });

  revalidatePath("/videos");
  revalidatePath(`/videos/${videoId}`);
  if (matchId) revalidatePath(`/matches/${matchId}`);
  return { ok: true };
}

/**
 * The CV engine never guesses ATHLETE/OPPONENT (see cv-service/app/tracking.py)
 * — every PlayerTrack starts UNKNOWN. This is the one write path that can
 * change that: a human explicitly confirming which detected track is them.
 * It only ever labels an existing track; it never creates, edits, or
 * fabricates any detection/trajectory data on it.
 */
export async function confirmPlayerTrackIdentityAction(
  _prev: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const videoId = String(formData.get("videoId") ?? "");
  const trackId = String(formData.get("trackId") ?? "");
  const identity = String(formData.get("identity") ?? "");
  if (identity !== "ATHLETE" && identity !== "OPPONENT") {
    return { ok: false, error: "Invalid identity." };
  }

  const { user, video } = await requireOwnedVideo(videoId);
  if (!video || video.deletedAt) {
    return { ok: false, error: "Video not found." };
  }

  // Scoped by videoId too, not just trackId, so one athlete can never
  // confirm identity on a track that isn't theirs.
  const track = await db.playerTrack.findFirst({ where: { id: trackId, videoId: video.id } });
  if (!track) {
    return { ok: false, error: "Player track not found." };
  }

  await db.playerTrack.update({
    where: { id: track.id },
    data: {
      identity,
      identitySource: "USER_CONFIRMED",
      identityConfirmedByUserId: user.id,
      identityConfirmedAt: new Date(),
    },
  });

  revalidatePath(`/videos/${videoId}`);
  return { ok: true };
}
