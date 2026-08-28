"use client";

import { useActionState } from "react";
import type { Athlete, AthleteProfile } from "@/generated/prisma/client";
import { competitiveLevelLabel } from "@/lib/labels";
import { Field, inputClasses } from "@/components/ui/form-field";
import { FormError } from "@/components/ui/form-error";
import { SubmitButton } from "@/components/ui/submit-button";
import type { ActionState } from "@/lib/actions/types";
import { INITIAL_ACTION_STATE } from "@/lib/actions/types";

const LEVEL_OPTIONS = Object.entries(competitiveLevelLabel);

function toDateInputValue(date: Date | string | null | undefined) {
  if (!date) return "";
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toISOString().slice(0, 10);
}

export function ProfileForm({
  action,
  athlete,
  profile,
  submitLabel,
}: {
  action: (prev: ActionState, formData: FormData) => Promise<ActionState>;
  athlete?: Pick<Athlete, "fullName" | "dateOfBirth" | "dominantHand"> | null;
  profile?: Pick<
    AthleteProfile,
    | "currentLevel"
    | "longTermGoal"
    | "academyName"
    | "coachName"
    | "heightCm"
    | "weightKg"
    | "yearsPlaying"
    | "trainingDaysPerWeek"
    | "playingStyleNotes"
    | "bio"
  > | null;
  submitLabel: string;
}) {
  const [state, formAction] = useActionState(action, INITIAL_ACTION_STATE);
  const errors = !state.ok ? state.fieldErrors : undefined;

  return (
    <form action={formAction} className="flex flex-col gap-8">
      <FormError message={!state.ok ? state.error : undefined} />

      <section className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-foreground">Identity</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Full name" htmlFor="fullName" errors={errors?.fullName} required>
            <input
              id="fullName"
              name="fullName"
              type="text"
              required
              defaultValue={athlete?.fullName ?? ""}
              className={inputClasses}
            />
          </Field>
          <Field label="Date of birth" htmlFor="dateOfBirth" errors={errors?.dateOfBirth}>
            <input
              id="dateOfBirth"
              name="dateOfBirth"
              type="date"
              defaultValue={toDateInputValue(athlete?.dateOfBirth)}
              className={inputClasses}
            />
          </Field>
          <Field label="Dominant hand" htmlFor="dominantHand" errors={errors?.dominantHand}>
            <select
              id="dominantHand"
              name="dominantHand"
              defaultValue={athlete?.dominantHand ?? ""}
              className={inputClasses}
            >
              <option value="">Prefer not to say</option>
              <option value="RIGHT">Right</option>
              <option value="LEFT">Left</option>
            </select>
          </Field>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-foreground">Competitive standing</h2>
        <p className="text-xs text-muted">
          Self-reported. This is not a computed ranking — it is only used to give context to your
          own development record.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Current competitive level" htmlFor="currentLevel" errors={errors?.currentLevel} required>
            <select
              id="currentLevel"
              name="currentLevel"
              required
              defaultValue={profile?.currentLevel ?? "INTERMEDIATE"}
              className={inputClasses}
            >
              {LEVEL_OPTIONS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Academy" htmlFor="academyName" errors={errors?.academyName}>
            <input
              id="academyName"
              name="academyName"
              type="text"
              defaultValue={profile?.academyName ?? ""}
              className={inputClasses}
            />
          </Field>
          <Field label="Coach" htmlFor="coachName" errors={errors?.coachName}>
            <input
              id="coachName"
              name="coachName"
              type="text"
              defaultValue={profile?.coachName ?? ""}
              className={inputClasses}
            />
          </Field>
        </div>
        <Field
          label="Long-term goal"
          htmlFor="longTermGoal"
          hint="E.g. reach international-level competition."
          errors={errors?.longTermGoal}
        >
          <textarea
            id="longTermGoal"
            name="longTermGoal"
            rows={2}
            defaultValue={profile?.longTermGoal ?? ""}
            className={inputClasses}
          />
        </Field>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-foreground">Physical &amp; training context</h2>
        <p className="text-xs text-muted">Optional. Never used for medical purposes.</p>
        <div className="grid gap-4 sm:grid-cols-4">
          <Field label="Height (cm)" htmlFor="heightCm" errors={errors?.heightCm}>
            <input
              id="heightCm"
              name="heightCm"
              type="number"
              defaultValue={profile?.heightCm ?? ""}
              className={inputClasses}
            />
          </Field>
          <Field label="Weight (kg)" htmlFor="weightKg" errors={errors?.weightKg}>
            <input
              id="weightKg"
              name="weightKg"
              type="number"
              step="0.1"
              defaultValue={profile?.weightKg ?? ""}
              className={inputClasses}
            />
          </Field>
          <Field label="Years playing" htmlFor="yearsPlaying" errors={errors?.yearsPlaying}>
            <input
              id="yearsPlaying"
              name="yearsPlaying"
              type="number"
              defaultValue={profile?.yearsPlaying ?? ""}
              className={inputClasses}
            />
          </Field>
          <Field label="Training days / week" htmlFor="trainingDaysPerWeek" errors={errors?.trainingDaysPerWeek}>
            <input
              id="trainingDaysPerWeek"
              name="trainingDaysPerWeek"
              type="number"
              defaultValue={profile?.trainingDaysPerWeek ?? ""}
              className={inputClasses}
            />
          </Field>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-foreground">Notes</h2>
        <Field label="Playing style notes" htmlFor="playingStyleNotes" errors={errors?.playingStyleNotes}>
          <textarea
            id="playingStyleNotes"
            name="playingStyleNotes"
            rows={2}
            defaultValue={profile?.playingStyleNotes ?? ""}
            className={inputClasses}
          />
        </Field>
        <Field label="Bio" htmlFor="bio" errors={errors?.bio}>
          <textarea id="bio" name="bio" rows={2} defaultValue={profile?.bio ?? ""} className={inputClasses} />
        </Field>
      </section>

      <SubmitButton pendingText="Saving…" className="self-start">
        {submitLabel}
      </SubmitButton>
    </form>
  );
}
