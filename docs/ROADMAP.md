# Milestone roadmap

Status against the master spec's M1-M20 milestone list.

## Done

**M1 — Project architecture + database + authentication + athlete profile.**
Next.js 16 + TypeScript + Prisma 7 + PostgreSQL scaffold. Credentials auth (Auth.js v5, JWT
sessions, bcrypt). `Athlete` + `AthleteProfile` models, onboarding flow, profile editing.

**M2 — Athlete Performance Model + goals + evidence system.**
61-skill catalog seeded from spec section 4 (Technical/Movement/Tactical/Physical/Mental). Goals
CRUD with category/priority/status. Skill assessments that always carry level, confidence, trend,
status, source, and a written rationale, and that cannot be created without at least one evidence
row. Dashboard shell (spec section 23) with honest empty states where the underlying evidence
doesn't exist yet.

**M4 — Match/video upload infrastructure.**
Full match CRUD; private local-disk video storage behind a swappable `VideoStorageProvider`
interface; a validated, streamed (never memory-buffered) upload pipeline with magic-byte format
detection and optional real ffprobe metadata extraction; a `Video` status state machine with unit
tests covering every legal/illegal transition; a `VideoJob` table shaped like a real job queue,
run today via a documented-honest synchronous local runner (see `docs/VIDEO_INTELLIGENCE.md`); the
`CVAnalysisEngine` interface with a `NullCvEngine` that honestly reports no analysis engine exists
yet rather than fabricating a result; a generalized `Evidence` model (now attaches to a `Match` or
`Video`, not just a `SkillAssessment`, with a DB `CHECK` constraint enforcing exactly one subject);
schema-only `Rally`/`Event` foundations for M7-M9 to populate later; authenticated, time-limited,
range-request-capable video streaming with defense-in-depth ownership checks; real soft deletion
that actually revokes stream access. Dashboard now shows real match/video counts. See
`docs/VIDEO_INTELLIGENCE.md` for the full design and `e2e/video-pipeline.spec.ts` for the
end-to-end security/pipeline test coverage.

**M5 — Computer vision foundation: court calibration + player detection/tracking + ground-truth evaluation.**
Replaced `NullCvEngine` with `PythonCvEngine`, calling a new separate Python service (`cv-service/`,
FastAPI) over HTTP — see `docs/CV_ARCHITECTURE.md` for the full design. Real video preprocessing
(ffprobe-based, streamed frame sampling, never loads a whole video into memory); recording-quality
assessment with specific reasons, never a bare score; classical (non-learned, explicitly
explainable) court boundary detection and video-px→court-metres homography calibration, confidence
deliberately capped at `MODERATE`; real person detection (MediaPipe + EfficientDet-Lite0,
Apache 2.0, CPU-only) with a documented "never assume the largest human is the athlete" identity
model — every track starts `UNKNOWN` and only a human "This is me"/"Opponent" confirmation
(`confirmPlayerTrackIdentityAction`) changes that; classical IoU-based tracking with explicit,
never-silently-bridged tracking gaps; three new Postgres models
(`VideoQualityAssessment`/`CourtCalibration`/`PlayerTrack`) with full provenance back to the
`VideoJob` that produced them; a ground-truth evaluation framework (`cv-service/eval/`) separate
from the pytest suite, with a synthetic (clearly-labeled, non-photorealistic) fixture proving the
calibration geometry is correct (mean corner error 2.99 px, IoU 0.988 against ground truth); the
video detail page now shows real quality/calibration/tracking status, a basic SVG overlay of the
actual detected court and trajectories, and a collapsed developer/debug panel. **Honestly flagged,
not solved:** real-badminton-footage accuracy is unvalidated — only synthetic-fixture geometry has
been proven correct; see `docs/CV_ARCHITECTURE.md` "Test fixtures and the real-footage gap" and
"Known limitations" for the full account, including the inline-request CV-invocation limitation
inherited from M4's job-runner design.

## Not started

**M3 — AI Coach + persistent structured athlete memory.**
Needs `ANTHROPIC_API_KEY` (not provisioned in this environment) and a decision on what the coach
synthesizes over — now that M4 gives it match/video/evidence records to reason over (still no CV
analysis results, since M5+ doesn't exist yet), realistically this reads goals + skill assessments
+ match/video evidence and produces a narrative summary, clearly labeled as synthesis over
self-reported data, not an independent diagnosis. Should NOT be built as a chatbot with its own
memory — spec section 31 requires structured output written back to the athlete model.

**M6 — Basic CV event detection (shuttle/racket tracking, shot classification).**
Builds on M5's real court calibration and player tracking — see `docs/CV_ARCHITECTURE.md` "Future
CV roadmap" for the recommended order: first, a small hand-labeled real-footage evaluation set to
finally validate (or correct) M5's provisional acceptance thresholds and confirm the pipeline works
on actual badminton video, not just synthetic geometry; then shuttle/racket tracking and shot
classification, writing to the `Event` model M4 already shaped for this. Every detection carries a
confidence score; below-threshold detections are surfaced as "insufficient visual evidence," never
silently dropped or guessed (spec section 7).

**M7 — Rally reconstruction.** Depends on M5/M6.

**M8 — Match analysis (Match Autopsy, spec section 10).** Depends on M7.

**M9 — "What should I have played?" decision engine (spec section 9).** Depends on M7/M8.

**M10 — Bottleneck engine (spec section 5).**
This is the dashboard's current honest gap: `hasEnoughEvidenceForBottleneck` is hard-coded `false`
in `src/app/(app)/dashboard/page.tsx` with a comment explaining why. Do not flip this to `true`
without the frequency/severity/opponent-exploitation evidence model this milestone requires —
that would be exactly the "fake numerical skill ratings" / fabricated-conclusion failure mode the
spec repeatedly warns against.

**M11 — Technique Lab.** Video upload (M4) is done; this milestone is specifically the
repetition-comparison UX (spec section 14) on top of it — requesting specific technique clips,
comparing consistency across repetitions. Needs M5/M6 for any real technical feedback.

**M12 — Movement analysis.** Depends on M5/M6.

**M13 — Longitudinal progress engine.**
Partially enabled by M2's data model (every `SkillAssessment` is timestamped and versioned per
skill), but the "solved weakness / regression / training-improvement-vs-match-transfer" reasoning
described in spec section 19/15 needs match data to mean anything.

**M14 — Coach collaboration.** `coach_observations` table (see `DOMAIN_MODEL.md`), plus a UI for a
coach account (role already exists on `User`, unused) to view and annotate an athlete's record.

**M15 — Opponent scouting.** Video upload (M4) is done; needs M5 for any automated scouting
signal. An opponent could technically upload/tag videos today via `Video.videoType: OTHER`, but no
opponent-scouting UI or `Opponent`/`tactical_patterns` model exists yet.

**M16 — Elite reference analysis.** Needs a real reference dataset before this can be anything but
marketing copy — spec section 12 is explicit that this must never become "you are X% as good as
[player]." Lowest priority until there's a credible data source.

**M17 — Tactical simulator (decision training, spec section 20).** Can start once the decision
taxonomy from M9 exists, so situations can be scored consistently.

**M18 — Advanced CV/biomechanics.** Depends on M5/M6 maturing.

**M19 — Tournament intelligence.** `tournaments` + `tournament_results` tables (see
`DOMAIN_MODEL.md`).

**M20 — Production hardening + observability + security + performance.**
Notable gaps already known from M1/M2/M4/M5 that belong here: no rate limiting on
signup/login/upload, no audit log (spec section 33 requires one), no deployment target configured
(local Postgres + local disk video storage only), no real background job queue yet (see
`docs/VIDEO_INTELLIGENCE.md` "Job architecture" for why that's currently honest rather than a
corner cut — M5's CV analysis call now genuinely needs this, not just processing/metadata
extraction, since real model inference is no longer instant), 750 MB per-video upload ceiling with
no chunked/resumable upload, `ffmpeg`/`ffprobe` is a host dependency not bundled with the app,
`cv-service` assumes a shared filesystem with the Next.js app (see `docs/CV_ARCHITECTURE.md`
"Deployment" — a real constraint for a future multi-host deployment). An automated test suite now
exists (Vitest unit tests, a Playwright e2e suite, and cv-service's own pytest + ground-truth eval
suite — see `README.md` "Testing") but has no CI wiring yet.

## Sequencing note

M3 (AI Coach) is listed next in the master spec's suggested order, but M6-M10 (shot/event detection
through the bottleneck engine) are the ones that give the AI Coach and the dashboard something new
to reason over beyond what M2 already provided (M4 added match/video *records*; M5 added real but
still shot/rally-blind court+player tracking — not yet "what happened in this rally" analysis).
Either order is defensible; this file doesn't prescribe which to build next — that's a product call
for the next session, not an architecture call.
