"use client";

import { useActionState } from "react";
import { createAssessmentAction } from "@/lib/actions/assessments";
import { INITIAL_ACTION_STATE } from "@/lib/actions/types";
import { Field, inputClasses } from "@/components/ui/form-field";
import { FormError } from "@/components/ui/form-error";
import { SubmitButton } from "@/components/ui/submit-button";

const LEVEL_OPTIONS = [
  ["EMERGING", "Emerging"],
  ["DEVELOPING", "Developing"],
  ["SOLID", "Solid"],
  ["STRONG", "Strong"],
  ["ADVANCED", "Advanced"],
];

const CONFIDENCE_OPTIONS = [
  ["VERY_LOW", "Very low — one observation, could easily be wrong"],
  ["LOW", "Low — a few observations, not consistent"],
  ["MODERATE", "Moderate — a recurring pattern"],
  ["HIGH", "High — consistent across matches/training"],
  ["VERY_HIGH", "Very high — repeatedly confirmed, incl. by coach"],
];

const TREND_OPTIONS = [
  ["UNKNOWN", "Unknown / first assessment"],
  ["IMPROVING", "Improving"],
  ["STABLE", "Stable"],
  ["DECLINING", "Declining"],
];

const EVIDENCE_TYPE_OPTIONS = [
  ["SELF_NOTE", "Self-observed note"],
  ["TRAINING_OBSERVATION", "Training observation"],
  ["COACH_NOTE", "Something my coach told me"],
  ["MATCH_OBSERVATION", "Match observation"],
  ["VIDEO_REVIEW", "Video review"],
  ["STATISTIC", "Statistic / count"],
];

export function AssessmentForm({ skillId }: { skillId: string }) {
  const [state, formAction] = useActionState(createAssessmentAction, INITIAL_ACTION_STATE);
  const errors = !state.ok ? state.fieldErrors : undefined;

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <input type="hidden" name="skillId" value={skillId} />
      <FormError message={!state.ok ? state.error : undefined} />

      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Level" htmlFor="level" errors={errors?.level} required>
          <select id="level" name="level" required defaultValue="DEVELOPING" className={inputClasses}>
            {LEVEL_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Confidence" htmlFor="confidence" errors={errors?.confidence} required>
          <select id="confidence" name="confidence" required defaultValue="LOW" className={inputClasses}>
            {CONFIDENCE_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Trend" htmlFor="trend" errors={errors?.trend} required>
          <select id="trend" name="trend" required defaultValue="UNKNOWN" className={inputClasses}>
            {TREND_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <Field
        label="Reasoning"
        htmlFor="summary"
        hint="Why this level and confidence? What have you actually observed?"
        errors={errors?.summary}
        required
      >
        <textarea id="summary" name="summary" rows={3} required className={inputClasses} />
      </Field>

      <div className="grid gap-4 sm:grid-cols-[200px_1fr]">
        <Field label="Evidence type" htmlFor="evidenceType" errors={errors?.evidenceType} required>
          <select id="evidenceType" name="evidenceType" required defaultValue="SELF_NOTE" className={inputClasses}>
            {EVIDENCE_TYPE_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label="Specific evidence"
          htmlFor="evidenceDescription"
          hint="What happened, and when? E.g. 'Lost 3 of 4 late-rally net exchanges in Aug 20 match.'"
          errors={errors?.evidenceDescription}
          required
        >
          <textarea id="evidenceDescription" name="evidenceDescription" rows={3} required className={inputClasses} />
        </Field>
      </div>

      <SubmitButton pendingText="Saving assessment…" className="self-start">
        Save assessment
      </SubmitButton>
    </form>
  );
}
