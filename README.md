# Badminton Performance Intelligence

An evidence-based athlete performance system for competitive singles badminton — not a chatbot,
not a workout generator. See `AGENTS.md` for the full product specification and
`docs/ROADMAP.md` for what's built versus planned.

Current scope: **M1** (auth, athlete identity), **M2** (skill catalog, self-reported skill
assessments with required evidence, goals, dashboard shell), **M4** (match/video upload, private
storage, a real (non-fake) processing pipeline, and a generalized evidence model), and **M5**
(computer-vision foundation: court calibration, player detection/tracking, and ground-truth
evaluation — a real Python CV service, not a fabricated result). See `docs/ARCHITECTURE.md`,
`docs/DOMAIN_MODEL.md`, `docs/VIDEO_INTELLIGENCE.md`, and `docs/CV_ARCHITECTURE.md` for how it's
built and why.

## Stack

Next.js 16 (App Router) · TypeScript · PostgreSQL · Prisma 7 · Auth.js v5 (Credentials + JWT) ·
Tailwind CSS v4 · zod · Python 3.11 + FastAPI + OpenCV + MediaPipe (`cv-service/`, see
`docs/CV_ARCHITECTURE.md`)

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

6. **`cv-service` (optional, enables real CV analysis).** Without it, videos still upload and
   process normally — the CV analysis stage honestly reports "no computer-vision analysis engine is
   configured yet" instead of a fabricated result. To enable it:
   ```bash
   cd cv-service
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   Then set `CV_SERVICE_URL="http://127.0.0.1:8000"` in `.env`. See `docs/CV_ARCHITECTURE.md`
   "Deployment" for the single-host filesystem-sharing assumption this relies on.

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
  machine (every legal/illegal transition), magic-byte format detection, signed video-access
  tokens, the CV-engine selection fallback (`getCvEngine`), and `PythonCvEngine`'s wire-format
  translation and failure handling (unreachable service, timeout, non-2xx, unparseable body) —
  `src/**/*.test.ts`.
- **`cv-service`'s own test suite (pytest, run from `cv-service/` with its venv active):**
  ```bash
  cd cv-service && source .venv/bin/activate && pytest
  ```
  Fast unit tests (court-geometry math, quality scoring, IoU tracking association, corner-to-court
  coordinate mapping) plus `@pytest.mark.integration` tests that load the real model and/or call
  the real HTTP API against the committed synthetic fixture — run everything with `pytest`, or
  `pytest -m "not integration"` for the fast subset. All deterministic, no network calls, no
  external model download at test time (the model is committed — see `docs/CV_ARCHITECTURE.md`
  "Deployment"), so this is CI-safe.
- **`cv-service`'s ground-truth evaluation report** (separate from pytest — see
  `docs/CV_ARCHITECTURE.md` "Ground-truth evaluation" for why): `python3 eval/evaluate.py`, prints
  real measured accuracy numbers (corner error, IoU) against every fixture in `eval/ground_truth/`.
- **E2E (Playwright, `npm run test:e2e`):**
  - `e2e/golden-path.spec.ts` — the M1/M2 golden path: signup → onboarding → goal →
    evidence-backed skill assessment → dashboard reflecting real data (including the honest
    "insufficient evidence" bottleneck state) → sign-out/sign-in, plus a regression check for a
    mobile-nav overlap bug found during manual testing.
  - `e2e/video-pipeline.spec.ts` — the M4 flow against a real committed video fixture
    (`e2e/fixtures/`): record a match → upload a real video → the (non-fake) pipeline actually
    validates it, extracts real metadata via ffprobe if available, and honestly reports no CV
    engine exists yet (when `CV_SERVICE_URL` isn't set — the default) → evidence on both the match
    and the video → an unreadable file is rejected with a real reason, not silently accepted → a
    second athlete gets 404 on the first athlete's video/match pages *and* on the streaming route
    even with a syntactically valid token (proving the ownership check, not just the token check,
    is what's blocking it) → deleting a video revokes a previously-valid stream token. Also checks
    real HTTP Range request support.
  - `e2e/cv-analysis.spec.ts` (M5) — upload the committed synthetic court fixture, wait for a
    **real** `cv-service` analysis run to complete, and assert the video detail page renders the
    actual measured result: quality status, court calibration status/confidence, an SVG overlay of
    the real detected court quadrilateral, the honest "no people tracked" message (the synthetic
    fixture has no real human shape), and a debug panel with real processing metadata. **Skips
    honestly** (doesn't fail) when `CV_SERVICE_URL` isn't set, matching this suite's existing
    "degrade gracefully when an optional dependency is absent" pattern (e.g. missing `ffprobe`).
    To run it: start `cv-service` (see "Setup" above), then
    `CV_SERVICE_URL=http://127.0.0.1:8000 npx playwright test e2e/cv-analysis.spec.ts`. Run it in
    isolation like this, not alongside the rest of the suite with `CV_SERVICE_URL` set globally —
    `video-pipeline.spec.ts`'s M4-era assertions (e.g. "no computer-vision analysis engine is
    configured yet") are written against the default `NullCvEngine` state and will fail if a real
    engine is active for that run too.

  All Playwright spec files require a migrated, seeded `DATABASE_URL` (same as dev); the suite
  starts its own `next dev` on port 3100 automatically and runs on a single worker (tests share
  that one dev-server database). Uses the environment's pre-installed Chromium
  (`/opt/pw-browsers/chromium` by default — override with `PLAYWRIGHT_CHROMIUM_PATH` if running
  elsewhere); does not run `playwright install`.

## Project layout

See `docs/ARCHITECTURE.md`.
