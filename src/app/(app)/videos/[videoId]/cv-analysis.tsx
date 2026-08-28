import type {
  ConfidenceLevel,
  CourtCalibration,
  PlayerTrack,
  VideoQualityAssessment,
} from "@/generated/prisma/client";
import type { CVPlayerDetectionPoint, CVTrackingGap } from "@/lib/video/cv-engine";
import {
  calibrationStatusLabel,
  calibrationStatusTone,
  confidenceLabel,
  confidenceTone,
  playerIdentityLabel,
  qualityStatusLabel,
  qualityStatusTone,
} from "@/lib/labels";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmPlayerIdentityButtons } from "./pipeline-actions";

// ---------------------------------------------------------------------------
// Renders the M5 computer-vision result for one video: quality assessment,
// court calibration, and player tracking. Every value here comes straight
// from a VideoQualityAssessment/CourtCalibration/PlayerTrack row written by
// job-runner.ts from a real cv-service response — nothing on this page is
// computed, estimated, or invented client-side. See spec M5 section 15
// ("UI") and docs/CV_ARCHITECTURE.md.
//
// `detections`/`gaps`/`courtCornersPx`/`homography` are Prisma Json columns;
// the casts below are safe only because job-runner.ts is the sole writer
// and always writes the CVPlayerDetectionPoint[]/CVTrackingGap[]/
// [number,number][] shapes from cv-engine.ts — see that file's docstring.
// ---------------------------------------------------------------------------

function formatTimestamp(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds - mins * 60;
  return `${String(mins).padStart(2, "0")}:${secs.toFixed(2).padStart(5, "0")}`;
}

export function CvAnalysisSection({
  videoId,
  quality,
  calibration,
  tracks,
  job,
}: {
  videoId: string;
  quality: VideoQualityAssessment | null;
  calibration: CourtCalibration | null;
  tracks: PlayerTrack[];
  job: { engineName: string | null; engineVersion: string | null; resultMetadata: unknown } | null;
}) {
  if (!quality) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Computer-vision analysis</CardTitle>
        </CardHeader>
        <CardDescription className="mt-0">
          Not yet available for this video. It will appear here once a computer-vision analysis pass completes.
        </CardDescription>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Recording quality</CardTitle>
          <Badge tone={qualityStatusTone[quality.status]}>{qualityStatusLabel[quality.status]}</Badge>
        </CardHeader>
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
          {quality.reasons.map((reason, i) => (
            <li key={i}>{reason}</li>
          ))}
        </ul>
        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
          {quality.measuredWidth && quality.measuredHeight && (
            <div>
              <dt className="text-muted">Measured resolution</dt>
              <dd className="text-foreground">
                {quality.measuredWidth} × {quality.measuredHeight}
              </dd>
            </div>
          )}
          {quality.measuredFrameRate != null && (
            <div>
              <dt className="text-muted">Measured frame rate</dt>
              <dd className="text-foreground">{quality.measuredFrameRate.toFixed(1)} fps</dd>
            </div>
          )}
          <div>
            <dt className="text-muted">Frames analyzed</dt>
            <dd className="text-foreground">{quality.framesSampled}</dd>
          </div>
          {quality.blankFrameRatio != null && (
            <div>
              <dt className="text-muted">Blank frames</dt>
              <dd className="text-foreground">{Math.round(quality.blankFrameRatio * 100)}%</dd>
            </div>
          )}
          {quality.decodeFailureRatio != null && quality.decodeFailureRatio > 0 && (
            <div>
              <dt className="text-muted">Decode failures</dt>
              <dd className="text-foreground">{Math.round(quality.decodeFailureRatio * 100)}%</dd>
            </div>
          )}
        </dl>
      </Card>

      {calibration && (
        <Card>
          <CardHeader>
            <CardTitle>Court calibration</CardTitle>
            <div className="flex items-center gap-2">
              {calibration.confidence && (
                <Badge tone={confidenceTone[calibration.confidence]}>{confidenceLabel[calibration.confidence]}</Badge>
              )}
              <Badge tone={calibrationStatusTone[calibration.status]}>
                {calibrationStatusLabel[calibration.status]}
              </Badge>
            </div>
          </CardHeader>
          {calibration.warnings.length > 0 && (
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
              {calibration.warnings.map((warning, i) => (
                <li key={i}>{warning}</li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-xs text-muted">
            Based on {calibration.sourceFrameTimestamps.length} sampled frame
            {calibration.sourceFrameTimestamps.length === 1 ? "" : "s"}. Court-position estimates are approximate —
            not survey-accurate measurements.
          </p>
        </Card>
      )}

      <CourtOverlay quality={quality} calibration={calibration} tracks={tracks} />

      <Card>
        <CardHeader>
          <CardTitle>Player tracking</CardTitle>
          <span className="text-xs text-muted">
            {tracks.length} track{tracks.length === 1 ? "" : "s"} found
          </span>
        </CardHeader>
        {tracks.length === 0 ? (
          <p className="text-sm text-muted">
            No people were reliably tracked across the sampled frames of this recording.
          </p>
        ) : (
          <div className="flex flex-col gap-4">
            {tracks.map((track) => (
              <PlayerTrackCard key={track.id} videoId={videoId} track={track} />
            ))}
          </div>
        )}
      </Card>

      <DebugDetails quality={quality} calibration={calibration} tracks={tracks} job={job} />
    </div>
  );
}

function PlayerTrackCard({ videoId, track }: { videoId: string; track: PlayerTrack }) {
  const detections = track.detections as unknown as CVPlayerDetectionPoint[];
  const gaps = track.gaps as unknown as CVTrackingGap[];

  return (
    <div className="rounded-lg border border-border bg-surface-raised p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Badge tone={track.identity === "UNKNOWN" ? "neutral" : "accent"}>
            {playerIdentityLabel[track.identity]}
          </Badge>
          <Badge tone={confidenceTone[track.confidence as ConfidenceLevel]}>
            {confidenceLabel[track.confidence as ConfidenceLevel]}
          </Badge>
          {track.identitySource === "USER_CONFIRMED" && (
            <span className="text-xs text-muted">confirmed by you</span>
          )}
        </div>
        <span className="text-xs text-muted">
          {formatTimestamp(track.startTimestampSeconds)} – {formatTimestamp(track.endTimestampSeconds)} ·{" "}
          {detections.length} detection{detections.length === 1 ? "" : "s"}
        </span>
      </div>

      {track.identitySource !== "USER_CONFIRMED" && (
        <div className="mt-2">
          <ConfirmPlayerIdentityButtons videoId={videoId} trackId={track.id} />
        </div>
      )}

      {gaps.length > 0 && (
        <div className="mt-2 flex flex-col gap-1 text-xs text-muted">
          {gaps.map((gap, i) => (
            <span key={i}>
              TRACKING GAP {formatTimestamp(gap.startSeconds)} → {formatTimestamp(gap.endSeconds)} — {gap.reason}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

const MAX_OVERLAY_POINTS_PER_TRACK = 150;

function identityColor(identity: PlayerTrack["identity"]): string {
  if (identity === "ATHLETE") return "var(--success)";
  if (identity === "OPPONENT") return "var(--danger)";
  return "var(--muted)";
}

/**
 * Optional basic visual overlay (spec M5 section 16): the detected court
 * quadrilateral plus each track's actual sampled trajectory, drawn to a
 * viewBox sized from the real data itself (not the video frame dimensions,
 * which may be unmeasured) so it never depends on unavailable metadata.
 * Every point plotted is a real detection; long tracks are evenly
 * subsampled for rendering size, never smoothed or interpolated, and the
 * caption says so.
 */
function CourtOverlay({
  quality,
  calibration,
  tracks,
}: {
  quality: VideoQualityAssessment;
  calibration: CourtCalibration | null;
  tracks: PlayerTrack[];
}) {
  const frameW = quality.measuredWidth;
  const frameH = quality.measuredHeight;
  const corners = calibration?.courtCornersPx as [number, number][] | null | undefined;

  if (!frameW || !frameH || (!corners && tracks.length === 0)) {
    return null;
  }

  const trackPoints = tracks.map((track) => {
    const detections = track.detections as unknown as CVPlayerDetectionPoint[];
    const allPoints = detections.map((d): [number, number] => [(d.x + d.width / 2) * frameW, (d.y + d.height / 2) * frameH]);
    const step = Math.max(1, Math.ceil(allPoints.length / MAX_OVERLAY_POINTS_PER_TRACK));
    const shown = allPoints.filter((_, i) => i % step === 0);
    return { track, points: shown, totalDetections: allPoints.length };
  });

  const allXY: [number, number][] = [
    ...(corners ?? []),
    ...trackPoints.flatMap((t) => t.points),
  ];
  if (allXY.length === 0) return null;

  const xs = allXY.map((p) => p[0]);
  const ys = allXY.map((p) => p[1]);
  const padX = Math.max(20, (Math.max(...xs) - Math.min(...xs)) * 0.05);
  const padY = Math.max(20, (Math.max(...ys) - Math.min(...ys)) * 0.05);
  const minX = Math.min(...xs) - padX;
  const minY = Math.min(...ys) - padY;
  const width = Math.max(...xs) - Math.min(...xs) + padX * 2;
  const height = Math.max(...ys) - Math.min(...ys) + padY * 2;

  const wasSubsampled = trackPoints.some((t) => t.points.length < t.totalDetections);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Detected court &amp; tracking overlay</CardTitle>
      </CardHeader>
      <div className="overflow-hidden rounded-lg border border-border bg-black">
        <svg viewBox={`${minX} ${minY} ${width} ${height}`} className="h-auto w-full" role="img" aria-label="Detected court boundary and player trajectories">
          {corners && corners.length === 4 && (
            <polygon
              points={corners.map(([x, y]) => `${x},${y}`).join(" ")}
              fill="none"
              stroke="var(--accent)"
              strokeWidth={Math.max(1, width / 400)}
            />
          )}
          {trackPoints.map(({ track, points }) => (
            <g key={track.id}>
              {points.length > 1 && (
                <polyline
                  points={points.map(([x, y]) => `${x},${y}`).join(" ")}
                  fill="none"
                  stroke={identityColor(track.identity)}
                  strokeWidth={Math.max(1, width / 500)}
                  opacity={0.7}
                />
              )}
              {points.map(([x, y], i) => (
                <circle key={i} cx={x} cy={y} r={Math.max(2, width / 250)} fill={identityColor(track.identity)} />
              ))}
            </g>
          ))}
        </svg>
      </div>
      <p className="mt-2 text-xs text-muted">
        {corners ? "Detected court boundary" : "No court boundary detected"}
        {tracks.length > 0 && " and sampled player position points"}. Colors: green = you (once confirmed), red =
        opponent, gray = not yet identified.
        {wasSubsampled && ` Showing up to ${MAX_OVERLAY_POINTS_PER_TRACK} evenly-spaced points per track.`}
      </p>
    </Card>
  );
}

/**
 * Developer/debug view (spec M5 section 19) — kept visually separate from
 * the athlete-facing summary above via a collapsed <details>, and limited
 * to real processing metadata (engine/model versions, sampling config,
 * checksum) rather than a full frame-by-frame inspector, which is out of
 * scope for this milestone's UI.
 */
function DebugDetails({
  quality,
  calibration,
  tracks,
  job,
}: {
  quality: VideoQualityAssessment;
  calibration: CourtCalibration | null;
  tracks: PlayerTrack[];
  job: { engineName: string | null; engineVersion: string | null; resultMetadata: unknown } | null;
}) {
  const raw = {
    engine: job ? { name: job.engineName, version: job.engineVersion } : null,
    processingMetadata: job?.resultMetadata ?? null,
    quality,
    calibration,
    tracks: tracks.map((t) => ({ id: t.id, engineTrackId: t.engineTrackId, identity: t.identity, detections: t.detections, gaps: t.gaps })),
  };
  return (
    <details className="rounded-xl border border-border bg-surface p-4 text-sm">
      <summary className="cursor-pointer font-medium text-muted-strong">Developer / debug details</summary>
      <pre className="mt-3 max-h-96 overflow-auto rounded-lg bg-surface-raised p-3 text-xs text-muted">
        {JSON.stringify(raw, (_key, value) => (typeof value === "bigint" ? value.toString() : value), 2)}
      </pre>
    </details>
  );
}
