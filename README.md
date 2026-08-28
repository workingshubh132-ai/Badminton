# Badminton Performance Intelligence

An evidence-based athlete performance system for competitive singles badminton — not a chatbot,
not a workout generator. See `AGENTS.md` for the full product specification and
`docs/ROADMAP.md` for what's built versus planned.

Current scope: **M1** (auth, athlete identity), **M2** (skill catalog, self-reported skill
assessments with required evidence, goals, dashboard shell), and **M4** (match/video upload,
private storage, a real (non-fake) processing pipeline, and a generalized evidence model). See
`docs/ARCHITECTURE.md`, `docs/DOMAIN_MODEL.md`, and `docs/VIDEO_INTELLIGENCE.md` for how it's
built and why.

## Stack

Next.js 16 (App Router) · TypeScript · PostgreSQL · Prisma 7 · Auth.js v5 (Credentials + JWT) ·
Tailwind CSS v4 · zod

## Setup

1. **Postgres.** Point `DATABASE_URL` (see `.env.example`) at a Postgres 14+ database. Locally:
   ```bash
   createuser badminton --pwprompt   # or: CREATE ROLE ... via psql
   createdb badminton_dev -O badminton
   ```
2. **Env.** `cp .env.example .env` and fill in `DATABASE_URL` and `AUTH_SECRET`
   (`openssl rand -base64 32`).
3. **`ffmpeg` (optional, recommended).** Enables real video duration/dimensions/frame-rate
   extraction on upload (`apt install ffmpeg` or equivalent). Its absence doesn't break
   uploads — that metadata just stays "not available" instead of being extracted. Not needed to
   run the app or its test suite.
4. **Install + migrate + seed:**
   ```bash
   npm install
   npx prisma migrate dev
   npx prisma db seed   # seeds the 61-skill catalog; safe to re-run (upsert)
   ```
5. **Run:**
   ```bash
   npm run dev
   ```

Uploaded videos are stored under `storage/videos/` (gitignored, local disk only — see
`docs/VIDEO_INTELLIGENCE.md` "Storage architecture" for the production story).

## Commands

| Command | Does |
|---|---|
| `npm run dev` | Dev server (Turbopack) |
| `npm run build` | Production build |
| `npm run lint` | ESLint |
| `npx tsc --noEmit` | Type-check |
| `npx prisma migrate dev --name <desc>` | New migration |
| `npx prisma studio` | Browse the database |
| `npm test` | Unit tests (Vitest) |

## Testing

- **Unit tests (Vitest):** validation schemas, label-map completeness, the video status state
  machine (every legal/illegal transition), magic-byte format detection, and signed video-access
  tokens — `src/**/*.test.ts`.
- **E2E (Playwright, `npm run test:e2e`):**
  - `e2e/golden-path.spec.ts` — the M1/M2 golden path: signup → onboarding → goal →
    evidence-backed skill assessment → dashboard reflecting real data (including the honest
    "insufficient evidence" bottleneck state) → sign-out/sign-in, plus a regression check for a
    mobile-nav overlap bug found during manual testing.
  - `e2e/video-pipeline.spec.ts` — the M4 flow against a real committed video fixture
    (`e2e/fixtures/`): record a match → upload a real video → the (non-fake) pipeline actually
    validates it, extracts real metadata via ffprobe if available, and honestly reports no CV
    engine exists yet → evidence on both the match and the video → an unreadable file is rejected
    with a real reason, not silently accepted → a second athlete gets 404 on the first athlete's
    video/match pages *and* on the streaming route even with a syntactically valid token (proving
    the ownership check, not just the token check, is what's blocking it) → deleting a video
    revokes a previously-valid stream token. Also checks real HTTP Range request support.

  Both spec files require a migrated, seeded `DATABASE_URL` (same as dev); the suite starts its
  own `next dev` on port 3100 automatically and runs on a single worker (tests share that one
  dev-server database). Uses the environment's pre-installed Chromium
  (`/opt/pw-browsers/chromium` by default — override with `PLAYWRIGHT_CHROMIUM_PATH` if running
  elsewhere); does not run `playwright install`.

## Project layout

See `docs/ARCHITECTURE.md`.
