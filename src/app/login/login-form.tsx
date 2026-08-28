"use client";

import { useActionState } from "react";
import { loginAction } from "@/lib/actions/auth";
import { INITIAL_ACTION_STATE } from "@/lib/actions/types";
import { Field, inputClasses } from "@/components/ui/form-field";
import { FormError } from "@/components/ui/form-error";
import { SubmitButton } from "@/components/ui/submit-button";

export function LoginForm({ callbackUrl }: { callbackUrl?: string }) {
  const [state, formAction] = useActionState(loginAction, INITIAL_ACTION_STATE);

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <input type="hidden" name="callbackUrl" value={callbackUrl ?? ""} />
      <FormError message={!state.ok ? state.error : undefined} />
      <Field label="Email" htmlFor="email" errors={!state.ok ? state.fieldErrors?.email : undefined} required>
        <input id="email" name="email" type="email" autoComplete="email" required className={inputClasses} />
      </Field>
      <Field
        label="Password"
        htmlFor="password"
        errors={!state.ok ? state.fieldErrors?.password : undefined}
        required
      >
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className={inputClasses}
        />
      </Field>
      <SubmitButton pendingText="Logging in…" className="mt-2">
        Log in
      </SubmitButton>
    </form>
  );
}
