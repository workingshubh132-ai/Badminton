import Link from "next/link";
import { LoginForm } from "./login-form";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string }>;
}) {
  const { callbackUrl } = await searchParams;

  return (
    <div className="flex min-h-full flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-sm">
        <Link href="/" className="text-sm font-semibold tracking-wide text-foreground">
          BADMINTON<span className="text-accent">INTEL</span>
        </Link>
        <h1 className="mt-8 text-xl font-semibold text-foreground">Log in</h1>
        <p className="mt-1 text-sm text-muted">Continue your athlete development record.</p>
        <div className="mt-6">
          <LoginForm callbackUrl={callbackUrl} />
        </div>
        <p className="mt-6 text-sm text-muted">
          No account yet?{" "}
          <Link href="/signup" className="text-accent hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
