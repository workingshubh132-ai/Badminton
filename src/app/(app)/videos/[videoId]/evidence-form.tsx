"use client";

import { useActionState } from "react";
import { addVideoEvidenceAction } from "@/lib/actions/evidence";
import { INITIAL_ACTION_STATE } from "@/lib/actions/types";
import { Field, inputClasses } from "@/components/ui/form-field";
import { FormError } from "@/components/ui/form-error";
import { SubmitButton } from "@/components/ui/submit-button";

const EVIDENCE_TYPE_OPTIONS = [
  ["VIDEO_REVIEW", "Video review"],
  ["SELF_NOTE", "Self-observed note"],
  ["MATCH_OBSERVATION", "Match observation"],
  ["COACH_NOTE", "Something my coach told me"],
];

export function VideoEvidenceForm({ videoId }: { videoId: string }) {
  const boundAction = addVideoEvidenceAction.bind(null, videoId);
  const [state, formAction] = useActionState(boundAction, INITIAL_ACTION_STATE);
  const errors = !state.ok ? state.fieldErrors : undefined;

  return (
    <form action={formAction} className="flex flex-col gap-3 rounded-lg border border-dashed border-border-strong p-3">
      <FormError message={!state.ok ? state.error : undefined} />
      <div className="grid gap-3 sm:grid-cols-[160px_120px_1fr]">
        <Field label="Type" htmlFor="videoEvidenceType" errors={errors?.evidenceType}>
          <select id="videoEvidenceType" name="evidenceType" defaultValue="VIDEO_REVIEW" className={inputClasses}>
            {EVIDENCE_TYPE_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Timestamp (s)" htmlFor="timestampSeconds" errors={errors?.timestampSeconds} hint="Optional">
          <input id="timestampSeconds" name="timestampSeconds" type="number" min="0" step="0.1" className={inputClasses} />
        </Field>
        <Field
          label="What did you notice?"
          htmlFor="videoEvidenceDescription"
          hint="e.g. 'At 1:32 I completely lost my split-step before the smash.'"
          errors={errors?.evidenceDescription}
        >
          <textarea id="videoEvidenceDescription" name="evidenceDescription" rows={2} className={inputClasses} />
        </Field>
      </div>
      <SubmitButton variant="secondary" pendingText="Adding…" className="self-start">
        Add evidence
      </SubmitButton>
    </form>
  );
}
