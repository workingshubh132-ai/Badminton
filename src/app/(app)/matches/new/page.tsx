import Link from "next/link";
import { MatchForm } from "../match-form";

export default function NewMatchPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <Link href="/matches" className="text-sm text-muted hover:text-foreground">
        ← Matches
      </Link>
      <h1 className="mt-2 text-xl font-semibold text-foreground">New match</h1>
      <p className="mt-1 text-sm text-muted">
        Record what you know now — video and evidence can be added afterward from the match page.
      </p>
      <div className="mt-8">
        <MatchForm />
      </div>
    </div>
  );
}
