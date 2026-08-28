# Architecture

This is a from-scratch build (the repository had zero commits when this document was written), so
the stack below was chosen deliberately for this product, not inherited.

## Why this stack

- **Next.js 16 (App Router) + TypeScript.** One deployable app for both the UI and the backend API
  surface (Server Actions + Route Handlers). Good fit for a data/decision-dense dashboard. CV
  processing (M5, built) lives in a separate Python service (`cv-service/`) — see "Video upload /
  storage / job infrastructure and CV pipeline" below and `docs/CV_ARCHITECTURE.md` — so this
  choice never locked us into Next.js for computer vision.
- **PostgreSQL + Prisma ORM.** The domain — athletes, matches, rallies, shots, evidence,
  bottlenecks — is inherently relational with real foreign keys and constraints (an assessment
  belongs to an athlete and a skill; evidence belongs to an assessment; a bottleneck will need to
  reference the matches and rallies that support it). A document store would fight this model.
  Prisma gives typed queries and real migrations, which matter for a schema that will grow for
  years.
- **Auth.js (NextAuth v5), Credentials provider + JWT sessions.** No email/SMS infrastructure is
  configured for this environment, so password auth is the honest baseline. JWT sessions avoid
  needing `Account`/`Session` tables since we don't use OAuth providers (yet). Switching to
  database sessions or adding OAuth later is additive, not a rewrite.
- **Tailwind CSS v4, no component library.** Kept dependencies minimal; the UI primitives in
  `src/components/ui/` are small and specific to this product's "clean, athletic, data-driven"
  bar (spec section 24) rather than a generic design system.
- **CV (M5) is built; LLM integration is not yet.** The AI Coach is a real future milestone (see
  `ROADMAP.md`), and wiring it in before there's data for it to work on would mean fabricating
  output — which the product spec explicitly forbids (spec section 41, "Never fabricate
  functionality"). The CV engine boundary (`CVAnalysisEngine`) followed the same discipline until
  M5 gave it a real implementation — see `docs/CV_ARCHITECTURE.md`.

## High-level shape

```
Next.js app (this repo)
├─ app/                       route segments (pages, layouts, route handlers)
│  └─ api/videos/              two Route Handlers, not Server Actions — see "Video upload / storage" below
├─ lib/
│  ├─ actions/                Server Actions — the only way the UI mutates data (except raw video bytes)
│  ├─ video/                  storage, upload validation, state machine, job runner, CV engine
│  │                          interface + PythonCvEngine (calls cv-service over HTTP) — see
│  │                          docs/VIDEO_INTELLIGENCE.md and docs/CV_ARCHITECTURE.md
│  ├─ db.ts                   Prisma client singleton (driver-adapter based, see below)
│  ├─ session.ts              auth/session/athlete-loading helpers used by every protected page
│  ├─ validation.ts           zod schemas — the single source of truth for input shape
│  └─ labels.ts                enum -> human label / badge-tone maps, used across pages
├─ components/ui/             small style primitives (Card, Badge, Button, form fields)
├─ auth.ts                    Auth.js config (Node runtime — see "proxy.ts" below)
├─ proxy.ts                   route protection (Next.js 16 renamed middleware.ts -> proxy.ts)
└─ generated/prisma/          generated Prisma client (git-ignored, regenerated via `prisma generate`)

prisma/
├─ schema.prisma              current models (M1 + M2 + M4 scope — see DOMAIN_MODEL.md)
├─ seed.ts                    seeds the Skill catalog (61 rows, from spec section 4)
└─ migrations/                real, versioned SQL migrations

storage/videos/                local video storage (gitignored — dev-only, see VIDEO_INTELLIGENCE.md)

cv-service/                    Python FastAPI computer-vision service (M5) — see docs/CV_ARCHITECTURE.md
├─ app/                         preprocessing, quality, court calibration, detection, tracking, pipeline
├─ eval/                        ground-truth evaluation CLI + fixtures (separate from tests/)
├─ tests/                       pytest suite
└─ models/                      committed model weights (efficientdet_lite0.tflite)
```

Nothing here is a monolith by accident: Server Actions are the only mutation path for structured
data (no ad-hoc `fetch` to hand-rolled API routes), and every action re-derives the current
user/athlete from the session server-side rather than trusting a client-supplied id — this is the
row-level access control mechanism until a real authorization layer is needed (see "Security
notes"). The one deliberate exception is raw video bytes: `/api/videos/upload` and
`/api/videos/[videoId]/stream` are Route Handlers, not Server Actions, specifically because Server
Actions buffer their whole payload before invoking the action — wrong for large files. Both still
re-derive the session server-side the same way every action does.

## Data flow discipline

The product spec is explicit: **"Do not make the LLM the database. Do not make chat history the
athlete model. Use structured data."** Concretely, in this codebase that means:

- Every enum used for a judgment call (skill level, confidence, trend, assessment status) lives in
  `schema.prisma`, not in prose. The UI renders these through `lib/labels.ts`; it never invents new
  categories on the fly.
- An assessment cannot exist without evidence — `createAssessmentAction` creates both rows in one
  Prisma call, and the zod schema (`assessmentSchema`) rejects a summary/evidence description under
  20/10 characters respectively, specifically to force "why," not just a bare rating.
- `AssessmentStatus` starts at `PROVISIONAL` for every self-reported entry and there is currently no
  UI path to `CONFIRMED` — that transition is reserved for when match evidence, video analysis, or
  coach confirmation (M5+/M14) actually exists.
- The dashboard's "What is holding you back?" section (spec section 23) has a `hasEnoughEvidenceForBottleneck`
  flag hard-coded to `false` with a comment explaining why. This is intentional: a real bottleneck
  determination requires match-level evidence (frequency, severity, opponent exploitation — spec
  section 5), which doesn't exist yet. Faking it would violate spec section 41 rule #1. When M10
  lands, that flag becomes a real query, not a rename.

## Auth

`src/auth.ts` configures Auth.js v5 with a single Credentials provider (bcrypt-hashed passwords,
12 salt rounds) and JWT sessions. `src/proxy.ts` (see below) redirects unauthenticated requests to
protected prefixes to `/login?callbackUrl=...`, and redirects authenticated users away from
`/login`/`/signup`. Session `role` (`PLAYER` / `COACH` / `ADMIN`) is carried in the JWT for future
authorization checks — no UI currently branches on it besides the schema existing, since only
`PLAYER` accounts can be created today.

## Next.js 16 specifics worth knowing

This project was scaffolded on Next.js 16.3.3 and React 19.2, which is newer than most training
data. Two conventions that differ from older Next.js docs:

- **`middleware.ts` is renamed to `proxy.ts`**, and its exported function is named `proxy`, not
  `middleware`. The `edge` runtime is no longer supported for it — it always runs on Node.js, which
  is why `src/proxy.ts` can import `@/auth` (which touches Postgres) directly, with no separate
  edge-safe auth config needed.
- **Prisma 7's client generator (`prisma-client`, not `prisma-client-js`) requires a driver
  adapter.** `src/lib/db.ts` constructs a `PrismaPg` adapter from `@prisma/adapter-pg` rather than
  passing a bare connection string to `PrismaClient`. The generated client lives at
  `src/generated/prisma/` (git-ignored) and is regenerated by `prisma generate` (also run
  automatically by `prisma migrate dev`).

See `node_modules/next/dist/docs/` for the authoritative, version-matched docs — that directory is
regenerated by `next dev` and is why `AGENTS.md` at the repo root points there.

## Video upload / storage / job infrastructure (M4) and CV pipeline (M5, both built)

M4 built the real infrastructure this needs: private local-disk storage behind a swappable
`VideoStorageProvider` interface, a validated upload pipeline (magic-byte format detection +
optional ffprobe metadata extraction), a `Video` status state machine, and a `VideoJob` table
shaped like a real job queue. See `docs/VIDEO_INTELLIGENCE.md` for the full design — including why
the "job runner" is currently synchronous-but-honest rather than a fake async queue, and exactly
what changes (and what doesn't) when a real background worker replaces it.

M5 built the CV *detection* itself, exactly along the boundary M4 already drew — per spec sections
6, 7, and 30, computer vision is a separate concern from this web app, not a library called inline
in a request handler:

```
Video already uploaded + stored (M4, done)
   -> VideoJob{type: CV_ANALYSIS} row created
   -> PythonCvEngine (implementing lib/video/cv-engine.ts's CVAnalysisEngine) calls cv-service, a
      separate Python FastAPI service (FastAPI + OpenCV + MediaPipe) over HTTP
   -> cv-service returns a structured result: recording-quality assessment, court calibration
      (with a homography), and player tracks (trajectory + confidence + explicit tracking gaps)
   -> job-runner.ts writes VideoQualityAssessment/CourtCalibration/PlayerTrack rows, each with
      real confidence and full provenance back to the VideoJob that produced them
   -> web app reads only these structured rows, never touches cv-service's internals directly
```

`PythonCvEngine` replaced `NullCvEngine` as the default when `CV_SERVICE_URL` is configured;
`NullCvEngine` remains the honest fallback (`status: "unavailable"`) for any environment that
hasn't started `cv-service` — CI included. See `docs/CV_ARCHITECTURE.md` for the full design: model
selection, court-detection methodology, player tracking/identity, data contracts, ground-truth
evaluation, measured performance, and known limitations (most importantly: real-badminton-footage
accuracy is not yet validated — only synthetic-fixture geometry is).

## AI Coach (target design, not yet built)

Per spec section 31, the "AI Coach" is a synthesis layer over the structured athlete model, not a
chatbot with its own memory. The target shape: a service module that reads from Postgres (skills,
goals, evidence, and — once they exist — matches/bottlenecks), calls the Anthropic API with a
schema-constrained prompt (tool use / structured output), and writes its output back as a normal
row (e.g., a `coach_note` or `ai_recommendation`) rather than holding state in conversation history.

## Known accepted risk: `prisma` CLI's transitive `deepmerge-ts` advisory

`npm audit` reports a high-severity advisory (GHSA-ggr8-5vv4-36mx, stack exhaustion in
`deepmerge-ts`) via `prisma -> @prisma/config -> deepmerge-ts`. This is a **devDependency of the
CLI's own config-file loader**, not runtime code shipped to production, and it only ever parses
this repo's own trusted `prisma.config.ts` — never untrusted input. The suggested fix
(`npm audit fix --force`) would downgrade `prisma` to 6.12.0 while leaving `@prisma/client` at
7.10.0, reintroducing a CLI/client major-version mismatch, which is worse. Left as-is; revisit when
Prisma ships a patched `@prisma/config`.

## Local dev environment (this session)

- PostgreSQL 16 runs locally (`sudo service postgresql start`), database `badminton_dev`, role
  `badminton` — see `.env.example`. This is throwaway dev state specific to this sandboxed session;
  it does not persist and is not a deployment target.
- `ffmpeg`/`ffprobe` installed via `apt` for real video-metadata extraction (M4) — see
  `docs/VIDEO_INTELLIGENCE.md` "Metadata extraction." Optional at runtime: its absence degrades
  gracefully rather than breaking uploads.
- Uploaded video bytes live under `storage/videos/` (gitignored), local-disk only in this
  environment — see `docs/VIDEO_INTELLIGENCE.md` "Storage architecture."
- `cv-service`'s Python venv (`cv-service/.venv/`, gitignored) has the pinned dependencies from
  `cv-service/requirements-dev.txt` installed, including the real EfficientDet-Lite0 model
  (committed at `cv-service/models/`) — see `docs/CV_ARCHITECTURE.md` "Deployment" for how to run
  it and wire it in via `CV_SERVICE_URL`.
- Deployment needs a real managed Postgres (e.g., Neon, Supabase, RDS, Prisma Postgres), a real
  `AUTH_SECRET`, a real video storage backend (implementing `VideoStorageProvider`), `ffmpeg` on
  the host or container image, and — for real CV analysis — `cv-service` deployed and reachable at
  `CV_SERVICE_URL`, with a shared filesystem for video bytes (see `docs/CV_ARCHITECTURE.md`
  "Deployment" for that single-host assumption). None is provisioned here — see `README.md` for
  setup steps.
