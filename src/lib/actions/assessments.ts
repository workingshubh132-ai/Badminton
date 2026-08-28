"use server";

import { revalidatePath } from "next/cache";
import { db } from "@/lib/db";
import { requireAthlete } from "@/lib/session";
import { assessmentSchema, evidenceOnlySchema } from "@/lib/validation";
import type { ActionState } from "@/lib/actions/types";

export async function createAssessmentAction(
  _prev: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const { user, athlete } = await requireAthlete();

  const parsed = assessmentSchema.safeParse({
    skillId: formData.get("skillId"),
    level: formData.get("level"),
    confidence: formData.get("confidence"),
    trend: formData.get("trend"),
    summary: formData.get("summary"),
    evidenceType: formData.get("evidenceType"),
    evidenceDescription: formData.get("evidenceDescription"),
  });

  if (!parsed.success) {
    return {
      ok: false,
      error: "Please fix the highlighted fields.",
      fieldErrors: parsed.error.flatten().fieldErrors as Record<string, string[]>,
    };
  }

  const skill = await db.skill.findUnique({ where: { id: parsed.data.skillId } });
  if (!skill) {
    return { ok: false, error: "Unknown skill." };
  }

  const { skillId, level, confidence, trend, summary, evidenceType, evidenceDescription } = parsed.data;

  // An assessment is meaningless without evidence, so both rows are created
  // together — there is no code path that produces a bare rating.
  await db.skillAssessment.create({
    data: {
      athleteId: athlete.id,
      skillId,
      level,
      confidence,
      trend,
      summary,
      source: "SELF_REPORT",
      status: "PROVISIONAL",
      createdByUserId: user.id,
      evidence: {
        create: {
          evidenceType,
          description: evidenceDescription,
          createdByUserId: user.id,
        },
      },
    },
  });

  revalidatePath("/skills");
  revalidatePath("/dashboard");
  return { ok: true };
}

export async function addEvidenceAction(
  assessmentId: string,
  _prev: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const { user, athlete } = await requireAthlete();

  const assessment = await db.skillAssessment.findFirst({
    where: { id: assessmentId, athleteId: athlete.id },
  });
  if (!assessment) {
    return { ok: false, error: "Assessment not found." };
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
      skillAssessmentId: assessment.id,
      evidenceType: parsed.data.evidenceType,
      description: parsed.data.evidenceDescription,
      createdByUserId: user.id,
    },
  });

  revalidatePath("/skills");
  return { ok: true };
}
