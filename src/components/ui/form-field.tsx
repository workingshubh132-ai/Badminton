import { LabelHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Field({
  label,
  htmlFor,
  hint,
  errors,
  children,
  required,
}: {
  label: string;
  htmlFor: string;
  hint?: string;
  errors?: string[];
  children: ReactNode;
  required?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <FieldLabel htmlFor={htmlFor}>
        {label}
        {required && <span className="text-accent"> *</span>}
      </FieldLabel>
      {children}
      {hint && !errors?.length && <p className="text-xs text-muted">{hint}</p>}
      {errors?.map((error) => (
        <p key={error} className="text-xs text-danger">
          {error}
        </p>
      ))}
    </div>
  );
}

function FieldLabel({ className, ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn("text-sm font-medium text-muted-strong", className)} {...props} />;
}

export const inputClasses =
  "w-full rounded-lg border border-border-strong bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted focus:border-accent focus:outline-none";
