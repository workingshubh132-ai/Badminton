# Video intelligence (M4 + M5)

This document covers the match/video upload infrastructure built in M4 and the CV engine boundary
it defines: what exists, how it's wired together, and where "real, working infrastructure" hands
off to the actual computer-vision engine. M5 built a real implementation of that engine — see
`docs/CV_ARCHITECTURE.md` for the CV-specific design (models, court calibration, tracking, data
contracts, evaluation, limitations); this document stays focused on the upload/storage/job
infrastructure and the interface boundary itself. See `docs/ARCHITECTURE.md` for the rest of the
stack and `docs/DOMAIN_MODEL.md` for the full schema reasoning.

**The one rule everything here follows:** nothing in this codebase fabricates a CV result. Every
screen that could show analysis says so honestly — a specific, measured quality/calibration/
tracking result when `cv-service` is configured and ran, or "no computer-vision analysis engine is
configured yet" when it isn't (still the default in any environment that hasn't set
`CV_SERVICE_URL`, CI included) — never a plausible-looking fake number either way. See
`lib/video/cv-engine.ts`.

## Video lifecycle

`Video.status` is a state machine, not a free-form string — see `lib/video/state-machine.ts` for
the authoritative transition table (also unit-tested in `state-machine.test.ts`) and
`lib/video/transition.ts` for the single function (`setVideoStatus`) allowed to write it. Every
write to `Video.status` anywhere in the codebase — the upload route, the job runner, video actions
— goes through that one function, so an illegal transition throws instead of silently corrupting
state.

```
UPLOAD_PENDING → UPLOADING → UPLOADED → VALIDATING → VALID → PROCESSING → READY_FOR_ANALYSIS
                                             │                      │
                                             ▼                      ▼
                                          INVALID               ANALYZING ⇄ ANALYZED
                                        (terminal;                   │
                                     delete + re-upload)      bounces back to
                                                            READY_FOR_ANALYSIS if the
                                                          CV engine has nothing to report
```

`FAILED` can be reached from `UPLOAD_PENDING`/`UPLOADING` (upload broke) or `PROCESSING` (metadata
extraction broke unexpectedly) and is retryable — `FAILED → VALIDATING` re-enters the pipeline
against the same already-stored bytes. `DELETED` is reachable from any non-deleted state and is
fully terminal.

A subtlety worth calling out: `ANALYZING` never resolves to a video-level `FAILED`. A CV analysis
attempt failing or having nothing to say (no engine configured) doesn't mean anything is wrong with
the *video* — it bounces back to `READY_FOR_ANALYSIS`, and the specific outcome (`UNAVAILABLE` vs.
`FAILED`) is recorded on the `VideoJob` row instead. See "Job architecture" below.

## Storage architecture

`lib/video/storage.ts` defines `VideoStorageProvider` — an interface for storage-level operations
only (upload, retrieve, exists, delete). The only implementation today is
`LocalFilesystemVideoStorageProvider`, writing under `storage/videos/` (gitignored, never
committed, never under `public/`). Swapping to S3/R2/GCS later means implementing the interface —
nothing above this layer knows or cares where bytes physically live.

Two things are deliberately **not** part of `VideoStorageProvider`:

- **"Generate temporary access URL"** (listed as a storage operation in the product spec) lives in
  `lib/video/access.ts` instead, and always resolves to this app's own
  `/api/videos/[videoId]/stream` route — never a raw storage URL handed to the client. Even a
  future S3-backed provider should stay proxied through that route rather than returning a raw
  presigned S3 URL, so ownership and soft-delete checks are enforced on every access, not just at
  URL-generation time.
- **Path resolution is not configurable via environment variable.** An earlier version read
  `process.env.VIDEO_STORAGE_DIR`; that was removed because a dynamically-computed filesystem path
  defeats Next.js's static file-tracing for serverless bundling (Turbopack has to conservatively
  trace the *entire* project instead of just the storage subfolder). Since local disk is already a
  documented dev-only stand-in, this cost more than it was worth — a real deployment swaps the
  whole provider, not this path.

### Temporary access tokens

`lib/video/access.ts` HMAC-signs `videoId + expiry` with `AUTH_SECRET` (`createVideoAccessToken`),
producing tokens like `expiresAt.signature` verified with a constant-time comparison
(`timingSafeEqual`) to avoid timing attacks. The streaming route checks this token **and**
separately re-verifies that the requesting session's athlete owns the video — a leaked-but-
unexpired token alone is not sufficient. Both layers are covered in
`e2e/video-pipeline.spec.ts` ("a second athlete cannot see... even with a valid token").

### Streaming

`/api/videos/[videoId]/stream` supports HTTP Range requests (206 Partial Content with a correct
`Content-Range`/`Content-Length`), which real `<video>` elements need for seeking and, in some
browsers, to play at all. It streams from disk via Node streams the whole way — never buffers a
full video into memory (`Readable.toWeb()` piped straight into the `Response`).

### Upload

`/api/videos/upload` is a **Route Handler**, not a Server Action. Server Actions fully buffer
their `FormData` payload before invoking the action function, which is wrong for large video
files; a Route Handler's `request.body` is a genuine Web `ReadableStream` that gets converted to a
Node `Readable` (`Readable.fromWeb`) and piped straight to disk (`lib/video/storage.ts`'s `upload`
hashes and counts bytes in a `Transform` tap as they pass through — never materializes the whole
file in memory). Upload metadata (video type, optional match association, filename) travels as
query parameters rather than multipart fields, specifically so the request body can stay raw
bytes with no multipart parsing needed.

The size limit (`MAX_VIDEO_UPLOAD_BYTES`, default 750 MB) is enforced twice: an early reject on
`Content-Length` if the client sends one (avoids wasting bandwidth on an obviously-too-large
upload), and — because a client header can be missing or wrong — a hard enforcement inside the
storage write itself, which aborts and deletes the partial file the moment actual received bytes
exceed the limit.

## Job architecture

The product spec's pipeline diagram has two stages — "PROCESSING JOB" and "CV ANALYSIS JOB." This
codebase unifies them into one `VideoJob` table with a `type` discriminator
(`PROCESSING` | `CV_ANALYSIS`) rather than two near-identical tables, for the same reason the
Evidence model wasn't made polymorphic before there was a second real shape to design against —
see `docs/DOMAIN_MODEL.md`. Both job types share the same real shape: status, progress, engine
name/version, error message, attempt/maxAttempts, timestamps.

**The local job runner (`lib/video/job-runner.ts`) is a documented stand-in for a real queue, not
a fake one.** `runProcessingPipeline(videoId)` and `runAnalysisPipeline(videoId)` run inline, in
the same request that triggered them — never behind an arbitrary `setTimeout`, and never
fabricating a result while "pretending" to be async. That was fully honest through M4, when every
step was genuinely fast:

- magic-byte format sniffing reads ~64 bytes (`lib/video/magic-bytes.ts`)
- ffprobe reads container headers, not the whole file (`lib/video/probe.ts`)
- `NullCvEngine` resolves instantly because it does no real work

**M5's `PythonCvEngine` is the real step that changes this** — a real model pass over real video
takes real time (measured: ~0.86s for a 5-second clip; see `docs/CV_ARCHITECTURE.md`
"Performance" for why that doesn't scale linearly-and-safely to a full match yet). This is exactly
the trigger condition this section already predicted. M5 adds a client-side request timeout
(`PythonCvEngine`, default 10 minutes) so a slow or hung call fails honestly rather than hanging
the request forever, but does **not** move analysis behind a real queue — that's a genuinely bigger
architectural decision than this milestone should make unilaterally. The schema/interfaces already
support that migration with zero changes when it happens: `VideoJob` rows are already
queue-shaped, and every stage already goes through the exact function a background worker would
call (`runProcessingPipeline(videoId)` / `runAnalysisPipeline(videoId)`). Swapping "call it inline"
for "enqueue a message that calls it" is the entire migration — no schema change, no interface
change. See `docs/CV_ARCHITECTURE.md` "Known limitations" and "Recommended M6" in the M5 final
report for the full accounting of this gap.

`runProcessingPipeline` auto-chains into `runAnalysisPipeline` once a video reaches
`READY_FOR_ANALYSIS`, so the player sees the honest "no CV engine yet" result immediately rather
than needing to click something that would only ever produce the same disappointing result. A
manual "Check for analysis" action exists on the video detail page for `READY_FOR_ANALYSIS` /
`ANALYZED` videos — genuinely useful the day a real engine lands, since it re-invokes the same real
code path with no changes needed to "activate" it.

### Retry semantics

`FAILED → VALIDATING` (via "Retry processing") re-runs the full pipeline against the already-
stored bytes, capped at `MAX_PROCESSING_ATTEMPTS` (3) — counted from actual `VideoJob` rows, not a
separate counter that could drift from reality. Exceeding the cap requires deleting and
re-uploading rather than retrying indefinitely.

## Metadata extraction

`lib/video/probe.ts` shells out to `ffprobe` (part of ffmpeg) for real duration/width/height/frame-
rate. This is optional-but-real, not a hard dependency: if `ffprobe` isn't on `PATH`, the video
still proceeds to `READY_FOR_ANALYSIS` with those fields left `null` — the UI shows "not
available," never a guess. If `ffprobe` *is* present but determines the file genuinely isn't a
decodable video (e.g. a truncated upload that passed the magic-byte check), that's treated as a
real defect and the video becomes `INVALID`, not silently accepted.

In this dev environment `ffmpeg`/`ffprobe` is installed via `apt`. A production deployment target
needs the same (a Docker base image with `ffmpeg`, or a bundled static binary) for metadata to
populate — degrading gracefully to "not available" if it's absent either way.

## CV engine interface

`lib/video/cv-engine.ts` defines `CVAnalysisEngine` — the boundary a real computer-vision engine
plugs into. `analyze(input)` returns a `CVAnalysisResult` with a `status` of `"completed"`,
`"unavailable"`, or `"failed"` — deliberately three states, not two, because "no engine exists yet"
and "an engine exists and broke" are different situations that deserve different messaging (see
`VideoJobStatus.UNAVAILABLE` vs. `FAILED` in the schema).

Two implementations exist:

- **`NullCvEngine`** — performs no video processing at all; honestly reports
  `status: "unavailable"` with an explanatory message. This is the pattern M4 shipped this
  interface with, and every real pipeline stage around it (job creation, status transitions,
  event-writing on success) already worked end-to-end against it before any real engine existed.
- **`PythonCvEngine`** (M5, `lib/video/python-cv-engine.ts`) — calls `cv-service`, a separate
  Python FastAPI service, over HTTP. Translates its wire-format JSON response field-for-field into
  the same `CVAnalysisResult` shape (extended in M5 with `quality`/`courtCalibration`/
  `playerTracks`/`processingMetadata`, all optional so `NullCvEngine`'s minimal shape stays valid)
  — never reinterprets or guesses a value the service didn't send. See `docs/CV_ARCHITECTURE.md`
  for the full CV design this implementation wraps.

`getCvEngine()` picks between them based on whether `CV_SERVICE_URL` is configured — unset (the
default for CI and any environment that hasn't started `cv-service`) means `NullCvEngine`, exactly
the same honest fallback M4 shipped. Swapping engines, or adding a third implementation later,
touches only `getCvEngine()` — nothing else in the codebase needs to change, proving out the
interface boundary M4 designed this around.

## Evidence architecture

See `docs/DOMAIN_MODEL.md` "Generalized evidence model (M4)" for the schema-level reasoning. In
short: `Evidence` now optionally attaches to a `Match` or `Video` in addition to a
`SkillAssessment`, with a database `CHECK` constraint guaranteeing exactly one subject per row.
Two real, working entry points exist: adding a note to a match (`addMatchEvidenceAction`) and
adding a timestamped note to a video (`addVideoEvidenceAction`, e.g. "at 1:32 I lost my split-step
before the smash").

## Match / Rally / Event foundation

`Match` is fully real — creation, videos, evidence, deletion all work. `Rally` and `Event` exist
purely as schema (see `docs/DOMAIN_MODEL.md`): nothing in M4 writes a row to either table. They're
there so M5-M7's CV pipeline can populate them without a breaking migration, per the spec's
explicit instruction to build the domain representation ahead of the engine that fills it — not
because a UI to manually annotate rallies/shots is part of this milestone (that's real product
surface area belonging to later milestones, and building it now would be exactly the kind of
overbuilding the spec warns against).

## Security model

- **Authentication**: every route (pages, the upload Route Handler, the streaming Route Handler)
  requires a valid session.
- **Authorization**: every query that touches a `Video`, `Match`, or `Evidence` row scopes by
  `athleteId` derived from the session server-side — never a client-supplied ID. Verified in
  `e2e/video-pipeline.spec.ts`: a second athlete gets 404 on another athlete's video page, match
  page, *and* a syntactically valid-but-wrong-owner stream token.
- **Private storage**: no permanent public video URL exists anywhere in the codebase. The only
  path to bytes is the short-lived signed stream route.
- **Soft deletion**: `deleteVideoAction` actually removes the file from storage (real deletion of
  bytes) while keeping a tombstone `Video` row (`status: DELETED`, `deletedAt` set) so `VideoJob`
  and `Evidence` history referencing it stays intact and inspectable. Every read path filters on
  `deletedAt: null` (or checks `status !== DELETED`), and the streaming route independently
  verifies the file still exists on disk — so a previously-valid, unexpired token stops working
  the instant a video is deleted (also covered in `e2e/video-pipeline.spec.ts`).
- **Upload limits**: size enforced both via an early `Content-Length` check and — because that
  header can't be trusted — during the actual write. MIME type is never trusted from the client;
  the real check is magic-byte sniffing on the received bytes.

## Known limitations

- **750 MB per-video ceiling** (`MAX_VIDEO_UPLOAD_BYTES`). A full 60-90 minute match at typical
  phone bitrates can exceed this. Chunked/resumable upload is a reasonable follow-up, not solved
  here — for now, recording in shorter segments (per rally/game) stays under the limit.
- **No background queue yet, and M5 is the first stage where that actually matters** — see "Job
  architecture" above for why this was honest through M4, what changed with a real CV engine, and
  exactly what the migration to a real queue looks like.
- **`ffprobe` is an optional host dependency**, not bundled. Metadata gracefully degrades to
  "not available" without it; a production deployment should ensure it's present for the feature
  to actually populate duration/dimensions.
- **Camera-quality assessment now exists (M5)** — real, measured recording-quality analysis
  (resolution/fps/blank-frame/decode-failure signals) via `cv-service`, replacing what used to be a
  flat "not available." See `docs/CV_ARCHITECTURE.md` "Acceptance thresholds" for why those
  thresholds are still provisional, not validated against real badminton footage yet.
- **No chunked upload / resume-on-failure.** A dropped connection mid-upload currently means
  starting over; the partial file is cleaned up (`storage.upload` deletes on error) rather than
  left as a corrupt orphan, but there's no resume capability.

CV-specific limitations (court detection accuracy, tracking, identity, single-host filesystem
assumption, and more) are covered in full in `docs/CV_ARCHITECTURE.md` "Known limitations" rather
than duplicated here.
