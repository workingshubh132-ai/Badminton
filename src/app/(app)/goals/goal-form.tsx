"use client";

import { useActionState } from "react";
import { createGoalAction } from "@/lib/actions/goals";
import { INITIAL_ACTION_STATE } from "@/lib/actions/types";
import { goalCategoryLabel, goalPriorityLabel } from "@/lib/labels";
import { Field, inputClasses } from "@/components/ui/form-field";
import { FormError } from "@/components/ui/form-error";
import { SubmitButton } from "@/components/ui/submit-button";

export function GoalForm() {
  const [state, formAction] = useActionState(createGoalAction, INITIAL_ACTION_STATE);
  const errors = !state.ok ? state.fieldErrors : undefined;

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <FormError message={!state.ok ? state.error : undefined} />
      <Field label="Title" htmlFor="title" errors={errors?.title} required>
        <input
          id="title"
          name="title"
          type="text"
          required
          placeholder="e.g. Stop overrunning the backhand corner in defence"
          className={inputClasses}
        />
      </Field>
      <Field label="Description" htmlFor="description" errors={errors?.description}>
        <textarea id="description" name="description" rows={2} className={inputClasses} />
      </Field>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Field label="Category" htmlFor="category" errors={errors?.category} required>
          <select id="category" name="category" required defaultValue="TECHNICAL" className={inputClasses}>
            {Object.entries(goalCategoryLabel).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Priority" htmlFor="priority" errors={errors?.priority} required>
          <select id="priority" name="priority" required defaultValue="MEDIUM" className={inputClasses}>
            {Object.entries(goalPriorityLabel).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Target date" htmlFor="targetDate" errors={errors?.targetDate}>
          <input id="targetDate" name="targetDate" type="date" className={inputClasses} />
        </Field>
      </div>
      <SubmitButton pendingText="Adding…" className="self-start">
        Add goal
      </SubmitButton>
    </form>
  );
}
