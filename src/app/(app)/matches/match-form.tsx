"use client";

import { useActionState } from "react";
import { createMatchAction } from "@/lib/actions/matches";
import { INITIAL_ACTION_STATE } from "@/lib/actions/types";
import { Field, inputClasses } from "@/components/ui/form-field";
import { FormError } from "@/components/ui/form-error";
import { SubmitButton } from "@/components/ui/submit-button";

const RESULT_OPTIONS = [
  ["UNKNOWN", "Unknown / not sure"],
  ["WIN", "Win"],
  ["LOSS", "Loss"],
];

export function MatchForm() {
  const [state, formAction] = useActionState(createMatchAction, INITIAL_ACTION_STATE);
  const errors = !state.ok ? state.fieldErrors : undefined;

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <FormError message={!state.ok ? state.error : undefined} />
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Opponent" htmlFor="opponentName" errors={errors?.opponentName}>
          <input id="opponentName" name="opponentName" type="text" className={inputClasses} />
        </Field>
        <Field label="Date" htmlFor="playedAt" errors={errors?.playedAt} required>
          <input
            id="playedAt"
            name="playedAt"
            type="date"
            required
            defaultValue={new Date().toISOString().slice(0, 10)}
            className={inputClasses}
          />
        </Field>
        <Field label="Competition" htmlFor="competitionName" errors={errors?.competitionName}>
          <input id="competitionName" name="competitionName" type="text" className={inputClasses} />
        </Field>
        <Field label="Format" htmlFor="format" errors={errors?.format} hint="e.g. Best of 3 games to 21">
          <input id="format" name="format" type="text" className={inputClasses} />
        </Field>
        <Field label="Result" htmlFor="result" errors={errors?.result} required>
          <select id="result" name="result" required defaultValue="UNKNOWN" className={inputClasses}>
            {RESULT_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Score" htmlFor="score" errors={errors?.score} hint="e.g. 21-18, 15-21, 21-19">
          <input id="score" name="score" type="text" className={inputClasses} />
        </Field>
      </div>
      <Field label="Notes" htmlFor="notes" errors={errors?.notes}>
        <textarea id="notes" name="notes" rows={3} className={inputClasses} />
      </Field>
      <SubmitButton pendingText="Creating…" className="self-start">
        Create match
      </SubmitButton>
    </form>
  );
}
