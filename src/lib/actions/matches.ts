"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { db } from "@/lib/db";
import { requireAthlete } from "@/lib/session";
import { matchSchema } from "@/lib/validation";
import type { ActionState } from "@/lib/actions/types";

export async function createMatchAction(_prev: ActionState, formData: FormData): Promise<ActionState> {
  const { user, athlete } = await requireAthlete();

  const parsed = matchSchema.safeParse({
    opponentName: formData.get("opponentName") || "",
    playedAt: formData.get("playedAt"),
    competitionName: formData.get("competitionName") || "",
    format: formData.get("format") || "",
    result: formData.get("result"),
    score: formData.get("score") || "",
    notes: formData.get("notes") || "",
  });

  if (!parsed.success) {
    return {
      ok: false,
      error: "Please fix the highlighted fields.",
      fieldErrors: parsed.error.flatten().fieldErrors as Record<string, string[]>,
    };
  }

  const match = await db.match.create({
    data: { ...parsed.data, athleteId: athlete.id, createdByUserId: user.id },
  });

  revalidatePath("/matches");
  redirect(`/matches/${match.id}`);
}

export async function deleteMatchAction(matchId: string): Promise<void> {
  const { athlete } = await requireAthlete();

  await db.match.deleteMany({ where: { id: matchId, athleteId: athlete.id } });

  revalidatePath("/matches");
}
