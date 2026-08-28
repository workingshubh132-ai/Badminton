"use client";

import { useActionState } from "react";
import { useRouter } from "next/navigation";
import {
  retryVideoProcessingAction,
  requestReanalysisAction,
  deleteVideoAction,
  associateVideoWithMatchAction,
  confirmPlayerTrackIdentityAction,
} from "@/lib/actions/videos";
import { INITIAL_ACTION_STATE } from "@/lib/actions/types";
import { Button } from "@/components/ui/button";
import { FormError } from "@/components/ui/form-error";
import { SubmitButton } from "@/components/ui/submit-button";
import { inputClasses } from "@/components/ui/form-field";

export function RetryProcessingButton({ videoId }: { videoId: string }) {
  const [state, formAction] = useActionState(retryVideoProcessingAction, INITIAL_ACTION_STATE);
  return (
    <form action={formAction} className="flex flex-col gap-2">
      <input type="hidden" name="videoId" value={videoId} />
      <FormError message={!state.ok ? state.error : undefined} />
      <SubmitButton variant="secondary" pendingText="Retrying…">
        Retry processing
      </SubmitButton>
    </form>
  );
}

export function RequestReanalysisButton({ videoId }: { videoId: string }) {
  const [state, formAction] = useActionState(requestReanalysisAction, INITIAL_ACTION_STATE);
  return (
    <form action={formAction} className="flex flex-col gap-2">
      <input type="hidden" name="videoId" value={videoId} />
      <FormError message={!state.ok ? state.error : undefined} />
      <SubmitButton variant="secondary" pendingText="Checking…">
        Check for analysis
      </SubmitButton>
    </form>
  );
}

export function AssociateMatchForm({
  videoId,
  matches,
}: {
  videoId: string;
  matches: { id: string; opponentName: string | null; playedAt: Date }[];
}) {
  const [state, formAction] = useActionState(associateVideoWithMatchAction, INITIAL_ACTION_STATE);
  return (
    <form action={formAction} className="flex flex-col gap-2 sm:flex-row sm:items-end sm:gap-3">
      <input type="hidden" name="videoId" value={videoId} />
      <FormError message={!state.ok ? state.error : undefined} />
      <div className="flex flex-1 flex-col gap-1.5">
        <label htmlFor="matchId" className="text-sm font-medium text-muted-strong">
          Attach to a match
        </label>
        <select id="matchId" name="matchId" defaultValue="" className={inputClasses}>
          <option value="" disabled>
            Select a match…
          </option>
          {matches.map((match) => (
            <option key={match.id} value={match.id}>
              vs {match.opponentName || "Unnamed opponent"} · {match.playedAt.toLocaleDateString()}
            </option>
          ))}
        </select>
      </div>
      <SubmitButton variant="secondary" pendingText="Linking…">
        Attach
      </SubmitButton>
    </form>
  );
}

function ConfirmIdentityForm({
  videoId,
  trackId,
  identity,
  label,
}: {
  videoId: string;
  trackId: string;
  identity: "ATHLETE" | "OPPONENT";
  label: string;
}) {
  const [state, formAction] = useActionState(confirmPlayerTrackIdentityAction, INITIAL_ACTION_STATE);
  return (
    <form action={formAction} className="inline-flex flex-col gap-1">
      <input type="hidden" name="videoId" value={videoId} />
      <input type="hidden" name="trackId" value={trackId} />
      <input type="hidden" name="identity" value={identity} />
      <FormError message={!state.ok ? state.error : undefined} />
      <SubmitButton variant="secondary" pendingText="Saving…">
        {label}
      </SubmitButton>
    </form>
  );
}

/**
 * Lets an athlete confirm which detected track is them — the CV engine
 * itself never guesses this (see cv-service/app/tracking.py). Only shown
 * for a track that isn't already USER_CONFIRMED; once confirmed, the plain
 * identity badge on the page (not this component) takes over.
 */
export function ConfirmPlayerIdentityButtons({ videoId, trackId }: { videoId: string; trackId: string }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-muted">Who is this?</span>
      <ConfirmIdentityForm videoId={videoId} trackId={trackId} identity="ATHLETE" label="This is me" />
      <ConfirmIdentityForm videoId={videoId} trackId={trackId} identity="OPPONENT" label="Opponent" />
    </div>
  );
}

export function DeleteVideoButton({ videoId }: { videoId: string }) {
  const router = useRouter();
  return (
    <Button
      variant="danger"
      onClick={async () => {
        if (!confirm("Delete this video? This cannot be undone.")) return;
        await deleteVideoAction(videoId);
        router.push("/videos");
      }}
    >
      Delete video
    </Button>
  );
}
