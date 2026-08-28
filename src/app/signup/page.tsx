import Link from "next/link";
import { SignupForm } from "./signup-form";

export default function SignupPage() {
  return (
    <div className="flex min-h-full flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-sm">
        <Link href="/" className="text-sm font-semibold tracking-wide text-foreground">
          BADMINTON<span className="text-accent">INTEL</span>
        </Link>
        <h1 className="mt-8 text-xl font-semibold text-foreground">Create your account</h1>
        <p className="mt-1 text-sm text-muted">
          Start your athlete performance record. You&apos;ll set up your profile next.
        </p>
        <div className="mt-6">
          <SignupForm />
        </div>
        <p className="mt-6 text-sm text-muted">
          Already have an account?{" "}
          <Link href="/login" className="text-accent hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
