"use server";

import { revalidatePath } from "next/cache";
import { db } from "@/lib/db";
import { requireAthlete } from "@/lib/session";
import { evidenceOnlySchema, subjectEvidenceSchema } from "@/lib/validation";
import type { ActionState } from "@/lib/actions/types";

/**
 * The generalized-evidence writers: unlike lib/actions/assessments.ts (which
 * always attaches evidence to a SkillAssessment), these attach an Evidence
 * row directly to a Match or a Video the current athlete owns — the two new
 * subjects the M4 evidence model supports. See docs/DOMAIN_MODEL.md
 * "Generalized evidence model (M4)".
 */

export async function addMatchEvidenceAction(
  matchId: string,
  _prev: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const { user, athlete } = await requireAthlete();

  const match = await db.match.findFirst({ where: { id: matchId, athleteId: athlete.id } });
  if (!match) {
    return { ok: false, error: "Match not found." };
  }

  const parsed = evidenceOnlySchema.safeParse({
    evidenceType: formData.get("evidenceType"),
    evidenceDescription: formData.get("evidenceDescription"),
  });
  if (!parsed.success) {
    return { ok: false, error: "Describe the specific evidence in at least 10 characters." };
  }

  await db.evidence.create({
    data: {
      athleteId: athlete.id,
      matchId: match.id,
      evidenceType: parsed.data.evidenceType,
      description: parsed.data.evidenceDescription,
      source: "PLAYER",
      createdByUserId: user.id,
    },
  });

  revalidatePath(`/matches/${matchId}`);
  return { ok: true };
}

export async function addVideoEvidenceAction(
  videoId: string,
  _prev: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const { user, athlete } = await requireAthlete();

  const video = await db.video.findFirst({
    where: { id: videoId, athleteId: athlete.id, deletedAt: null },
  });
  if (!video) {
    return { ok: false, error: "Video not found." };
  }

  const parsed = subjectEvidenceSchema.safeParse({
    evidenceType: formData.get("evidenceType"),
    evidenceDescription: formData.get("evidenceDescription"),
    timestampSeconds: formData.get("timestampSeconds") || "",
  });
  if (!parsed.success) {
    return { ok: false, error: "Describe the specific evidence in at least 10 characters." };
  }

  await db.evidence.create({
    data: {
      athleteId: athlete.id,
      videoId: video.id,
      evidenceType: parsed.data.evidenceType,
      description: parsed.data.evidenceDescription,
      timestampSeconds: parsed.data.timestampSeconds,
      source: "PLAYER",
      createdByUserId: user.id,
    },
  });

  revalidatePath(`/videos/${videoId}`);
  return { ok: true };
}
