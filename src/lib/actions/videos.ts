"use server";

import { revalidatePath } from "next/cache";
import { db } from "@/lib/db";
import { requireAthlete } from "@/lib/session";
import { getVideoStorageProvider } from "@/lib/video/storage";
import { runAnalysisPipeline, runProcessingPipeline } from "@/lib/video/job-runner";
import type { ActionState } from "@/lib/actions/types";

/** Loads a video the current athlete owns, or null. Never trusts a client-supplied athleteId. */
async function requireOwnedVideo(videoId: string) {
  const { athlete } = await requireAthlete();
  const video = await db.video.findFirst({ where: { id: videoId, athleteId: athlete.id } });
  return { athlete, video };
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
