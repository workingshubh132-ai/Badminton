import Link from "next/link";
import { requireAthlete } from "@/lib/session";
import { db } from "@/lib/db";
import { videoStatusLabel, videoStatusTone, videoTypeLabel } from "@/lib/labels";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { VideoUploadForm } from "@/components/video-upload-form";

const PAGE_SIZE = 20;

export default async function VideosPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const { athlete } = await requireAthlete();
  const { page: pageParam } = await searchParams;
  const page = Math.max(1, Number(pageParam) || 1);

  const [videos, totalCount] = await Promise.all([
    db.video.findMany({
      where: { athleteId: athlete.id, deletedAt: null },
      orderBy: { createdAt: "desc" },
      skip: (page - 1) * PAGE_SIZE,
      take: PAGE_SIZE,
      include: { match: { select: { id: true, opponentName: true } } },
    }),
    db.video.count({ where: { athleteId: athlete.id, deletedAt: null } }),
  ]);

  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Videos</h1>
        <p className="mt-1 text-sm text-muted">
          {totalCount} video{totalCount === 1 ? "" : "s"}. Every video is analyzed the moment a
          computer-vision engine is available — none is today, so this library shows honest,
          real pipeline status, not analysis results.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upload a video</CardTitle>
        </CardHeader>
        <VideoUploadForm />
      </Card>

      {videos.length === 0 ? (
        <p className="text-sm text-muted">No videos yet.</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border">
          {videos.map((video, i) => (
            <Link
              key={video.id}
              href={`/videos/${video.id}`}
              className={`flex flex-wrap items-center justify-between gap-3 bg-surface px-4 py-3 text-sm transition-colors hover:bg-surface-raised ${
                i !== 0 ? "border-t border-border" : ""
              }`}
            >
              <div>
                <span className="font-medium text-foreground">{video.originalFilename}</span>
                <span className="ml-2 text-muted">{new Date(video.createdAt).toLocaleDateString()}</span>
                {video.match && (
                  <span className="ml-2 text-muted">
                    · vs {video.match.opponentName || "Unnamed opponent"}
                  </span>
                )}
                {video.durationSeconds != null && (
                  <span className="ml-2 text-muted">
                    · {Math.floor(video.durationSeconds / 60)}:
                    {String(Math.round(video.durationSeconds % 60)).padStart(2, "0")}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Badge tone="neutral">{videoTypeLabel[video.videoType]}</Badge>
                <Badge tone={videoStatusTone[video.status]}>{videoStatusLabel[video.status]}</Badge>
              </div>
            </Link>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          {page > 1 && (
            <Link href={`/videos?page=${page - 1}`}>
              <Button variant="secondary">Newer</Button>
            </Link>
          )}
          <span className="text-sm text-muted">
            Page {page} of {totalPages}
          </span>
          {page < totalPages && (
            <Link href={`/videos?page=${page + 1}`}>
              <Button variant="secondary">Older</Button>
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
