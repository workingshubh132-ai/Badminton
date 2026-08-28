"use server";

import { revalidatePath } from "next/cache";
import { db } from "@/lib/db";
import { requireAthlete } from "@/lib/session";
import { goalSchema } from "@/lib/validation";
import type { ActionState } from "@/lib/actions/types";

export async function createGoalAction(_prev: ActionState, formData: FormData): Promise<ActionState> {
  const { athlete } = await requireAthlete();

  const parsed = goalSchema.safeParse({
    title: formData.get("title"),
    description: formData.get("description") || "",
    category: formData.get("category"),
    priority: formData.get("priority"),
    targetDate: formData.get("targetDate") || "",
  });

  if (!parsed.success) {
    return {
      ok: false,
      error: "Please fix the highlighted fields.",
      fieldErrors: parsed.error.flatten().fieldErrors as Record<string, string[]>,
    };
  }

  await db.goal.create({
    data: { ...parsed.data, athleteId: athlete.id },
  });

  revalidatePath("/goals");
  revalidatePath("/dashboard");
  return { ok: true };
}

export async function setGoalStatusAction(goalId: string, status: "ACTIVE" | "ACHIEVED" | "ABANDONED") {
  const { athlete } = await requireAthlete();

  await db.goal.updateMany({
    where: { id: goalId, athleteId: athlete.id },
    data: { status },
  });

  revalidatePath("/goals");
  revalidatePath("/dashboard");
}

export async function deleteGoalAction(goalId: string) {
  const { athlete } = await requireAthlete();

  await db.goal.deleteMany({
    where: { id: goalId, athleteId: athlete.id },
  });

  revalidatePath("/goals");
  revalidatePath("/dashboard");
}
