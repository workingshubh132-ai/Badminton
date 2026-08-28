import Link from "next/link";
import { notFound } from "next/navigation";
import { requireAthlete } from "@/lib/session";
import { db } from "@/lib/db";
import {
  matchResultLabel,
  matchResultTone,
  matchStatusLabel,
  videoStatusLabel,
  videoStatusTone,
  videoTypeLabel,
} from "@/lib/labels";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { VideoUploadForm } from "@/components/video-upload-form";
import { MatchEvidenceForm } from "./evidence-form";
import { DeleteMatchButton } from "./delete-match-button";

export default async function MatchDetailPage({ params }: { params: Promise<{ matchId: string }> }) {
  const { matchId } = await params;
  const { athlete } = await requireAthlete();

  const match = await db.match.findFirst({
    where: { id: matchId, athleteId: athlete.id },
    include: {
      videos: { where: { deletedAt: null }, orderBy: { createdAt: "desc" } },
      evidence: { orderBy: { createdAt: "desc" } },
    },
  });
  if (!match) notFound();

  return (
    <div className="flex flex-col gap-8">
      <div>
        <Link href="/matches" className="text-sm text-muted hover:text-foreground">
          ← Matches
        </Link>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-foreground">
              vs {match.opponentName || "Unnamed opponent"}
            </h1>
            <p className="mt-1 text-sm text-muted">
              {new Date(match.playedAt).toLocaleDateString()}
              {match.competitionName && ` · ${match.competitionName}`}
              {match.format && ` · ${match.format}`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone="neutral">{matchStatusLabel[match.status]}</Badge>
            <Badge tone={matchResultTone[match.result]}>{matchResultLabel[match.result]}</Badge>
          </div>
        </div>
        {match.score && <p className="mt-2 text-sm text-foreground">Score: {match.score}</p>}
        {match.notes && <p className="mt-2 text-sm text-muted">{match.notes}</p>}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Video</CardTitle>
        </CardHeader>
        {match.videos.length > 0 && (
          <div className="mb-4 flex flex-col gap-2">
            {match.videos.map((video) => (
              <Link
                key={video.id}
                href={`/videos/${video.id}`}
                className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm transition-colors hover:border-border-strong"
              >
                <span className="text-foreground">{video.originalFilename}</span>
                <div className="flex items-center gap-2">
                  <Badge tone="neutral">{videoTypeLabel[video.videoType]}</Badge>
                  <Badge tone={videoStatusTone[video.status]}>{videoStatusLabel[video.status]}</Badge>
                </div>
              </Link>
            ))}
          </div>
        )}
        <VideoUploadForm matchId={match.id} lockVideoType="MATCH" />
      </Card>

      <div className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-muted-strong">Evidence ({match.evidence.length})</h2>
        {match.evidence.map((evidence) => (
          <div key={evidence.id} className="rounded-lg bg-surface-raised p-3 text-sm">
            <span className="text-muted">
              {evidence.evidenceType.replace(/_/g, " ").toLowerCase()} ·{" "}
              {new Date(evidence.createdAt).toLocaleDateString()}
            </span>
            <p className="mt-1 text-foreground">{evidence.description}</p>
          </div>
        ))}
        <MatchEvidenceForm matchId={match.id} />
      </div>

      <div>
        <DeleteMatchButton matchId={match.id} />
      </div>
    </div>
  );
}
