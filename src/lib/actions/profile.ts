"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { db } from "@/lib/db";
import { requireUser } from "@/lib/session";
import { athleteProfileSchema } from "@/lib/validation";
import type { ActionState } from "@/lib/actions/types";

function parseProfileForm(formData: FormData) {
  return athleteProfileSchema.safeParse({
    fullName: formData.get("fullName"),
    dateOfBirth: formData.get("dateOfBirth") || "",
    dominantHand: formData.get("dominantHand") || "",
    currentLevel: formData.get("currentLevel"),
    longTermGoal: formData.get("longTermGoal") || "",
    academyName: formData.get("academyName") || "",
    coachName: formData.get("coachName") || "",
    heightCm: formData.get("heightCm") || "",
    weightKg: formData.get("weightKg") || "",
    yearsPlaying: formData.get("yearsPlaying") || "",
    trainingDaysPerWeek: formData.get("trainingDaysPerWeek") || "",
    playingStyleNotes: formData.get("playingStyleNotes") || "",
    bio: formData.get("bio") || "",
  });
}

export async function createAthleteProfileAction(
  _prev: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const user = await requireUser();

  const existing = await db.athlete.findUnique({ where: { userId: user.id } });
  if (existing) {
    redirect("/dashboard");
  }

  const parsed = parseProfileForm(formData);
  if (!parsed.success) {
    return {
      ok: false,
      error: "Please fix the highlighted fields.",
      fieldErrors: parsed.error.flatten().fieldErrors as Record<string, string[]>,
    };
  }

  const { fullName, dateOfBirth, dominantHand, ...profileFields } = parsed.data;

  await db.athlete.create({
    data: {
      userId: user.id,
      fullName,
      dateOfBirth,
      dominantHand,
      profile: {
        create: profileFields,
      },
    },
  });

  redirect("/dashboard");
}

export async function updateAthleteProfileAction(
  _prev: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const user = await requireUser();

  const athlete = await db.athlete.findUnique({ where: { userId: user.id } });
  if (!athlete) {
    redirect("/onboarding");
  }

  const parsed = parseProfileForm(formData);
  if (!parsed.success) {
    return {
      ok: false,
      error: "Please fix the highlighted fields.",
      fieldErrors: parsed.error.flatten().fieldErrors as Record<string, string[]>,
    };
  }

  const { fullName, dateOfBirth, dominantHand, ...profileFields } = parsed.data;

  await db.athlete.update({
    where: { id: athlete.id },
    data: {
      fullName,
      dateOfBirth,
      dominantHand,
      profile: {
        upsert: {
          create: profileFields,
          update: profileFields,
        },
      },
    },
  });

  revalidatePath("/dashboard");
  revalidatePath("/profile");
  return { ok: true };
}
