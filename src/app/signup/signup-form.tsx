"use client";

import { useActionState } from "react";
import { signupAction } from "@/lib/actions/auth";
import { INITIAL_ACTION_STATE } from "@/lib/actions/types";
import { Field, inputClasses } from "@/components/ui/form-field";
import { FormError } from "@/components/ui/form-error";
import { SubmitButton } from "@/components/ui/submit-button";

export function SignupForm() {
  const [state, formAction] = useActionState(signupAction, INITIAL_ACTION_STATE);

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <FormError message={!state.ok ? state.error : undefined} />
      <Field label="Name" htmlFor="name" errors={!state.ok ? state.fieldErrors?.name : undefined} required>
        <input id="name" name="name" type="text" autoComplete="name" required className={inputClasses} />
      </Field>
      <Field label="Email" htmlFor="email" errors={!state.ok ? state.fieldErrors?.email : undefined} required>
        <input id="email" name="email" type="email" autoComplete="email" required className={inputClasses} />
      </Field>
      <Field
        label="Password"
        htmlFor="password"
        hint="At least 8 characters."
        errors={!state.ok ? state.fieldErrors?.password : undefined}
        required
      >
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          className={inputClasses}
        />
      </Field>
      <SubmitButton pendingText="Creating account…" className="mt-2">
        Create account
      </SubmitButton>
    </form>
  );
}
