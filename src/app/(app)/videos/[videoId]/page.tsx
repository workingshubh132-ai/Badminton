import Link from "next/link";
import { notFound } from "next/navigation";
import { requireAthlete } from "@/lib/session";
import { db } from "@/lib/db";
import { buildVideoStreamUrl } from "@/lib/video/access";
import {
  videoJobStatusLabel,
  videoJobStatusTone,
  videoJobTypeLabel,
  videoStatusExplanation,
  videoStatusLabel,
  videoStatusTone,
  videoTypeLabel,
} from "@/lib/labels";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { VideoEvidenceForm } from "./evidence-form";
import {
  AssociateMatchForm,
  DeleteVideoButton,
  RequestReanalysisButton,
  RetryProcessingButton,
} from "./pipeline-actions";

const PLAYABLE_STATUSES = new Set([
  "UPLOADED",
  "VALIDATING",
  "VALID",
  "PROCESSING",
  "READY_FOR_ANALYSIS",
  "ANALYZING",
  "ANALYZED",
  "FAILED",
]);

function formatBytes(bytes: bigint | null): string | null {
  if (bytes == null) return null;
  const value = Number(bytes);
  const mb = value / (1024 * 1024);
  if (mb >= 1024) return `${(mb / 1024).toFixed(2)} GB`;
  if (mb >= 1) return `${mb.toFixed(1)} MB`;
  return `${Math.max(1, Math.round(value / 1024))} KB`;
}

function formatDuration(seconds: number | null): string | null {
  if (seconds == null) return null;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

export default async function VideoDetailPage({ params }: { params: Promise<{ videoId: string }> }) {
  const { videoId } = await params;
  const { athlete } = await requireAthlete();

  const video = await db.video.findFirst({
    where: { id: videoId, athleteId: athlete.id },
    include: {
      jobs: { orderBy: { createdAt: "desc" } },
      evidence: { orderBy: { createdAt: "desc" } },
      match: { select: { id: true, opponentName: true } },
    },
  });
  if (!video || video.deletedAt) notFound();

  const availableMatches = video.matchId
    ? []
    : await db.match.findMany({
        where: { athleteId: athlete.id },
        orderBy: { playedAt: "desc" },
        select: { id: true, opponentName: true, playedAt: true },
      });

  const canPlay = PLAYABLE_STATUSES.has(video.status);
  const streamUrl = canPlay ? buildVideoStreamUrl(video.id) : null;

  const metadataRows = [
    ["Duration", formatDuration(video.durationSeconds)],
    ["Dimensions", video.width && video.height ? `${video.width} × ${video.height}` : null],
    ["Frame rate", video.frameRate ? `${video.frameRate.toFixed(1)} fps` : null],
    ["Orientation", video.orientation ?? null],
    ["File size", formatBytes(video.byteSize)],
    ["Format", video.detectedFormat ?? null],
  ].filter(([, value]) => value != null) as [string, string][];

  return (
    <div className="flex flex-col gap-8">
      <div>
        <Link
          href={video.match ? `/matches/${video.match.id}` : "/videos"}
          className="text-sm text-muted hover:text-foreground"
        >
          ← {video.match ? `Match vs ${video.match.opponentName || "Unnamed opponent"}` : "All videos"}
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-semibold text-foreground">{video.originalFilename}</h1>
          <Badge tone="neutral">{videoTypeLabel[video.videoType]}</Badge>
        </div>
      </div>

      {!video.match && availableMatches.length > 0 && (
        <Card>
          <AssociateMatchForm videoId={video.id} matches={availableMatches} />
        </Card>
      )}

      {streamUrl && (
        <video
          controls
          className="w-full rounded-xl border border-border bg-black"
          preload="metadata"
          src={streamUrl}
        >
          Your browser cannot play this video format.
        </video>
      )}

      <Card className="border-accent/30">
        <CardHeader>
          <CardTitle>Status</CardTitle>
          <Badge tone={videoStatusTone[video.status]}>{videoStatusLabel[video.status]}</Badge>
        </CardHeader>
        <p className="text-sm text-muted">{videoStatusExplanation[video.status]}</p>
        {video.invalidReason && <p className="mt-2 text-sm text-danger">{video.invalidReason}</p>}
        {video.failureReason && <p className="mt-2 text-sm text-danger">{video.failureReason}</p>}
        <div className="mt-4 flex flex-wrap gap-3">
          {video.status === "FAILED" && <RetryProcessingButton videoId={video.id} />}
          {(video.status === "READY_FOR_ANALYSIS" || video.status === "ANALYZED") && (
            <RequestReanalysisButton videoId={video.id} />
          )}
        </div>
      </Card>

      {metadataRows.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Video details</CardTitle>
          </CardHeader>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
            {metadataRows.map(([label, value]) => (
              <div key={label}>
                <dt className="text-muted">{label}</dt>
                <dd className="text-foreground">{value}</dd>
              </div>
            ))}
          </dl>
        </Card>
      )}

      <div className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-muted-strong">Processing history</h2>
        {video.jobs.length === 0 ? (
          <p className="text-sm text-muted">No processing jobs yet.</p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-border">
            {video.jobs.map((job, i) => (
              <div
                key={job.id}
                className={`flex flex-wrap items-center justify-between gap-2 bg-surface px-4 py-3 text-sm ${
                  i !== 0 ? "border-t border-border" : ""
                }`}
              >
                <div>
                  <span className="font-medium text-foreground">{videoJobTypeLabel[job.type]}</span>
                  {job.engineName && <span className="ml-2 text-muted">via {job.engineName}</span>}
                  {job.errorMessage && <p className="mt-1 text-muted">{job.errorMessage}</p>}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted">attempt {job.attempt}</span>
                  <Badge tone={videoJobStatusTone[job.status]}>{videoJobStatusLabel[job.status]}</Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-muted-strong">Evidence ({video.evidence.length})</h2>
        {video.evidence.map((evidence) => (
          <div key={evidence.id} className="rounded-lg bg-surface-raised p-3 text-sm">
            <span className="text-muted">
              {evidence.evidenceType.replace(/_/g, " ").toLowerCase()}
              {evidence.timestampSeconds != null && ` · ${formatDuration(evidence.timestampSeconds)}`} ·{" "}
              {new Date(evidence.createdAt).toLocaleDateString()}
            </span>
            <p className="mt-1 text-foreground">{evidence.description}</p>
          </div>
        ))}
        <VideoEvidenceForm videoId={video.id} />
      </div>

      <div>
        <DeleteVideoButton videoId={video.id} />
      </div>
    </div>
  );
}
