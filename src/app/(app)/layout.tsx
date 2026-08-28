import Link from "next/link";
import { requireUser } from "@/lib/session";
import { signOutAction } from "@/lib/actions/session";

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/goals", label: "Goals" },
  { href: "/skills", label: "Skill Assessments" },
  { href: "/profile", label: "Profile" },
];

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await requireUser();

  return (
    <div className="min-h-full flex flex-col">
      <header className="border-b border-border bg-surface/60 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4 py-3 sm:px-6 sm:py-4">
          <div className="flex items-center justify-between gap-3">
            <Link href="/dashboard" className="shrink-0 text-sm font-semibold tracking-wide text-foreground">
              BADMINTON<span className="text-accent">INTEL</span>
            </Link>
            <div className="flex items-center gap-3">
              <span className="hidden text-sm text-muted sm:inline">{user.name}</span>
              <form action={signOutAction}>
                <button
                  type="submit"
                  className="rounded-md px-3 py-1.5 text-sm text-muted transition-colors hover:bg-surface-raised hover:text-foreground"
                >
                  Sign out
                </button>
              </form>
            </div>
          </div>
          <nav className="-mx-4 mt-3 flex items-center gap-1 overflow-x-auto px-4 sm:mx-0 sm:mt-2 sm:px-0">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="shrink-0 rounded-md px-3 py-1.5 text-sm text-muted transition-colors hover:bg-surface-raised hover:text-foreground"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">{children}</main>
    </div>
  );
}
