"use client";

import { useActionState } from "react";
import { addEvidenceAction } from "@/lib/actions/assessments";
import { INITIAL_ACTION_STATE } from "@/lib/actions/types";
import { Field, inputClasses } from "@/components/ui/form-field";
import { FormError } from "@/components/ui/form-error";
import { SubmitButton } from "@/components/ui/submit-button";

const EVIDENCE_TYPE_OPTIONS = [
  ["SELF_NOTE", "Self-observed note"],
  ["TRAINING_OBSERVATION", "Training observation"],
  ["COACH_NOTE", "Something my coach told me"],
  ["MATCH_OBSERVATION", "Match observation"],
  ["VIDEO_REVIEW", "Video review"],
  ["STATISTIC", "Statistic / count"],
];

export function EvidenceForm({ assessmentId }: { assessmentId: string }) {
  const boundAction = addEvidenceAction.bind(null, assessmentId);
  const [state, formAction] = useActionState(boundAction, INITIAL_ACTION_STATE);
  const errors = !state.ok ? state.fieldErrors : undefined;

  return (
    <form action={formAction} className="flex flex-col gap-3 rounded-lg border border-dashed border-border-strong p-3">
      <FormError message={!state.ok ? state.error : undefined} />
      <div className="grid gap-3 sm:grid-cols-[180px_1fr_auto] sm:items-end">
        <Field label="Type" htmlFor={`evidenceType-${assessmentId}`} errors={errors?.evidenceType}>
          <select
            id={`evidenceType-${assessmentId}`}
            name="evidenceType"
            defaultValue="SELF_NOTE"
            className={inputClasses}
          >
            {EVIDENCE_TYPE_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label="Add supporting evidence"
          htmlFor={`evidenceDescription-${assessmentId}`}
          errors={errors?.evidenceDescription}
        >
          <input
            id={`evidenceDescription-${assessmentId}`}
            name="evidenceDescription"
            type="text"
            className={inputClasses}
          />
        </Field>
        <SubmitButton variant="secondary" pendingText="Adding…">
          Add
        </SubmitButton>
      </div>
    </form>
  );
}
