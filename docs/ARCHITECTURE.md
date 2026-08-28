# Architecture

This is a from-scratch build (the repository had zero commits when this document was written), so
the stack below was chosen deliberately for this product, not inherited.

## Why this stack

- **Next.js 16 (App Router) + TypeScript.** One deployable app for both the UI and the backend API
  surface (Server Actions + Route Handlers). Good fit for a data/decision-dense dashboard. CV
  processing (M5+) will live in a separate Python service — see "CV pipeline" below — so this
  choice does not lock us into Next.js for computer vision.
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
- **No CV, no LLM integration yet.** Both are real future milestones (see `ROADMAP.md`), and
  wiring them in before there's data for them to work on would mean fabricating output — which
  the product spec explicitly forbids (spec section 41, "Never fabricate functionality").

## High-level shape

```
Next.js app (this repo)
├─ app/                       route segments (pages, layouts, route handlers)
├─ lib/
│  ├─ actions/                Server Actions — the only way the UI mutates data
│  ├─ db.ts                   Prisma client singleton (driver-adapter based, see below)
│  ├─ session.ts              auth/session/athlete-loading helpers used by every protected page
│  ├─ validation.ts           zod schemas — the single source of truth for input shape
│  └─ labels.ts                enum -> human label / badge-tone maps, used across pages
├─ components/ui/             small style primitives (Card, Badge, Button, form fields)
├─ auth.ts                    Auth.js config (Node runtime — see "proxy.ts" below)
├─ proxy.ts                   route protection (Next.js 16 renamed middleware.ts -> proxy.ts)
└─ generated/prisma/          generated Prisma client (git-ignored, regenerated via `prisma generate`)

prisma/
├─ schema.prisma              current models (M1 + M2 scope — see DOMAIN_MODEL.md)
├─ seed.ts                    seeds the Skill catalog (61 rows, from spec section 4)
└─ migrations/                real, versioned SQL migrations
```

Nothing here is a monolith by accident: Server Actions are the only mutation path (no ad-hoc
`fetch` to hand-rolled API routes), and every action re-derives the current user/athlete from the
session server-side rather than trusting a client-supplied id — this is the row-level access
control mechanism until a real authorization layer is needed (see "Security notes").

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

## CV pipeline (target design, not yet built)

Per spec sections 6, 7, and 30, computer vision is a separate concern from this web app, not a
library called inline in a request handler. The target shape:

```
Phone video upload -> object storage (private, signed URLs)
   -> video_jobs row created (status: QUEUED)
   -> Python CV service (FastAPI + OpenCV/MediaPipe or similar) picks up the job
   -> writes structured cv_events / pose_data / court_calibrations rows, each with a confidence score
   -> web app reads only the structured rows, never touches the video pipeline's internals
```

This keeps the CV model swappable (spec section 30: "use replaceable interfaces for CV models, do
not tightly couple the entire application to one computer-vision model") and keeps long-running
video processing off the Next.js request/response cycle entirely.

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
- Deployment needs a real managed Postgres (e.g., Neon, Supabase, RDS, Prisma Postgres) and a real
  `AUTH_SECRET`. Neither is provisioned here — see `README.md` for setup steps.
