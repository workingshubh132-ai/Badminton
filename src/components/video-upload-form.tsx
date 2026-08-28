"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { videoTypeLabel } from "@/lib/labels";
import { inputClasses } from "@/components/ui/form-field";

const VIDEO_TYPES = ["MATCH", "TRAINING", "TECHNIQUE", "OTHER"] as const;

const RECORDING_TIPS = [
  "Keep the full court visible in frame — better to stand back too far than crop the baseline.",
  "Keep yourself in frame throughout the rally, not just at the start.",
  "Avoid people or objects between the camera and the court.",
  "A stable placement (propped against something steady) beats a handheld shot, even without a tripod.",
];

type UploadState =
  | { phase: "idle" }
  | { phase: "uploading"; progressPercent: number }
  | { phase: "processing" }
  | { phase: "error"; message: string }
  | { phase: "done"; videoId: string; status: string };

export function VideoUploadForm({
  matchId,
  lockVideoType,
}: {
  matchId?: string;
  lockVideoType?: (typeof VIDEO_TYPES)[number];
}) {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [videoType, setVideoType] = useState<(typeof VIDEO_TYPES)[number]>(lockVideoType ?? "MATCH");
  const [state, setState] = useState<UploadState>({ phase: "idle" });

  function handleFileChosen(file: File) {
    setState({ phase: "uploading", progressPercent: 0 });

    const params = new URLSearchParams({
      videoType,
      originalFilename: file.name,
      clientMimeType: file.type,
      ...(matchId ? { matchId } : {}),
    });

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/videos/upload?${params.toString()}`);
    xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        setState({ phase: "uploading", progressPercent: Math.round((event.loaded / event.total) * 100) });
      }
    };

    xhr.onload = () => {
      let body: { videoId?: string; status?: string; error?: string } = {};
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        // fall through to generic error below
      }
      if (xhr.status >= 200 && xhr.status < 300 && body.videoId) {
        setState({ phase: "done", videoId: body.videoId, status: body.status ?? "" });
        router.refresh();
      } else {
        setState({ phase: "error", message: body.error ?? `Upload failed (HTTP ${xhr.status}).` });
      }
    };

    xhr.onerror = () => setState({ phase: "error", message: "Upload failed — check your connection and try again." });

    setState({ phase: "uploading", progressPercent: 0 });
    xhr.send(file);
  }

  return (
    <div className="flex flex-col gap-4">
      <details className="rounded-lg border border-border-strong bg-surface-raised p-3 text-sm text-muted">
        <summary className="cursor-pointer font-medium text-muted-strong">Recording tips (no tripod needed)</summary>
        <ul className="mt-2 list-disc space-y-1 pl-4">
          {RECORDING_TIPS.map((tip) => (
            <li key={tip}>{tip}</li>
          ))}
        </ul>
      </details>

      {!lockVideoType && (
        <div className="flex flex-col gap-1.5">
          <label htmlFor="videoType" className="text-sm font-medium text-muted-strong">
            Video type
          </label>
          <select
            id="videoType"
            value={videoType}
            onChange={(e) => setVideoType(e.target.value as (typeof VIDEO_TYPES)[number])}
            className={inputClasses}
            disabled={state.phase === "uploading"}
          >
            {VIDEO_TYPES.map((type) => (
              <option key={type} value={type}>
                {videoTypeLabel[type]}
              </option>
            ))}
          </select>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="video/*"
        capture="environment"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFileChosen(file);
        }}
      />

      {state.phase === "idle" && (
        <Button variant="primary" type="button" onClick={() => fileInputRef.current?.click()} className="self-start">
          Choose or record a video
        </Button>
      )}

      {state.phase === "uploading" && (
        <div className="flex flex-col gap-2">
          <div className="h-2 w-full overflow-hidden rounded-full bg-surface-raised">
            <div
              className="h-full bg-accent transition-all"
              style={{ width: `${state.progressPercent}%` }}
            />
          </div>
          <p className="text-sm text-muted">Uploading… {state.progressPercent}%</p>
        </div>
      )}

      {state.phase === "error" && (
        <div className="flex flex-col gap-2">
          <p className="text-sm text-danger">{state.message}</p>
          <Button variant="secondary" type="button" onClick={() => setState({ phase: "idle" })} className="self-start">
            Try again
          </Button>
        </div>
      )}

      {state.phase === "done" && (
        <div className="rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">
          Video uploaded.{" "}
          <a href={`/videos/${state.videoId}`} className="underline">
            View status
          </a>
        </div>
      )}
    </div>
  );
}
