"use client";

import { useActionState } from "react";
import { addMatchEvidenceAction } from "@/lib/actions/evidence";
import { INITIAL_ACTION_STATE } from "@/lib/actions/types";
import { Field, inputClasses } from "@/components/ui/form-field";
import { FormError } from "@/components/ui/form-error";
import { SubmitButton } from "@/components/ui/submit-button";

const EVIDENCE_TYPE_OPTIONS = [
  ["SELF_NOTE", "Self-observed note"],
  ["MATCH_OBSERVATION", "Match observation"],
  ["STATISTIC", "Statistic / count"],
  ["COACH_NOTE", "Something my coach told me"],
];

export function MatchEvidenceForm({ matchId }: { matchId: string }) {
  const boundAction = addMatchEvidenceAction.bind(null, matchId);
  const [state, formAction] = useActionState(boundAction, INITIAL_ACTION_STATE);
  const errors = !state.ok ? state.fieldErrors : undefined;

  return (
    <form action={formAction} className="flex flex-col gap-3 rounded-lg border border-dashed border-border-strong p-3">
      <FormError message={!state.ok ? state.error : undefined} />
      <div className="grid gap-3 sm:grid-cols-[200px_1fr]">
        <Field label="Type" htmlFor="matchEvidenceType" errors={errors?.evidenceType}>
          <select id="matchEvidenceType" name="evidenceType" defaultValue="SELF_NOTE" className={inputClasses}>
            {EVIDENCE_TYPE_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label="What happened?"
          htmlFor="matchEvidenceDescription"
          hint="Specific and dated beats general — e.g. 'Lost 4 straight points at 18-18 in game 2 after rushing serves.'"
          errors={errors?.evidenceDescription}
        >
          <textarea id="matchEvidenceDescription" name="evidenceDescription" rows={2} className={inputClasses} />
        </Field>
      </div>
      <SubmitButton variant="secondary" pendingText="Adding…" className="self-start">
        Add evidence
      </SubmitButton>
    </form>
  );
}
