import Link from "next/link";
import { requireAthlete } from "@/lib/session";
import { db } from "@/lib/db";
import { matchResultLabel, matchResultTone, matchStatusLabel } from "@/lib/labels";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default async function MatchesPage() {
  const { athlete } = await requireAthlete();

  const matches = await db.match.findMany({
    where: { athleteId: athlete.id },
    orderBy: { playedAt: "desc" },
    include: { _count: { select: { videos: true } } },
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Matches</h1>
          <p className="mt-1 text-sm text-muted">
            Every match is UNPROCESSED until a computer-vision pipeline exists to analyze it —
            recording it now still builds your evidence record.
          </p>
        </div>
        <Link href="/matches/new">
          <Button variant="primary">New match</Button>
        </Link>
      </div>

      {matches.length === 0 ? (
        <p className="text-sm text-muted">No matches recorded yet.</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border">
          {matches.map((match, i) => (
            <Link
              key={match.id}
              href={`/matches/${match.id}`}
              className={`flex flex-wrap items-center justify-between gap-3 bg-surface px-4 py-3 text-sm transition-colors hover:bg-surface-raised ${
                i !== 0 ? "border-t border-border" : ""
              }`}
            >
              <div>
                <span className="font-medium text-foreground">
                  {match.opponentName || "Unnamed opponent"}
                </span>
                <span className="ml-2 text-muted">{new Date(match.playedAt).toLocaleDateString()}</span>
                {match.competitionName && <span className="ml-2 text-muted">· {match.competitionName}</span>}
              </div>
              <div className="flex items-center gap-2">
                <Badge tone="neutral">
                  {match._count.videos} video{match._count.videos === 1 ? "" : "s"}
                </Badge>
                <Badge tone="neutral">{matchStatusLabel[match.status]}</Badge>
                <Badge tone={matchResultTone[match.result]}>{matchResultLabel[match.result]}</Badge>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
