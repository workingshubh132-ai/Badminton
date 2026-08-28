# Badminton Performance Intelligence

An evidence-based athlete performance system for competitive singles badminton — not a chatbot,
not a workout generator. See `AGENTS.md` for the full product specification and
`docs/ROADMAP.md` for what's built versus planned.

Current scope: **M1** (auth, athlete identity) and **M2** (skill catalog, self-reported skill
assessments with required evidence, goals, dashboard shell). See `docs/ARCHITECTURE.md` and
`docs/DOMAIN_MODEL.md` for how it's built and why.

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
3. **Install + migrate + seed:**
   ```bash
   npm install
   npx prisma migrate dev
   npx prisma db seed   # seeds the 61-skill catalog; safe to re-run (upsert)
   ```
4. **Run:**
   ```bash
   npm run dev
   ```

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

- **Unit tests (Vitest):** validation schemas and label-map completeness — `src/**/*.test.ts`.
- **E2E (Playwright, `npm run test:e2e`):** `e2e/golden-path.spec.ts` drives the full M1/M2 golden
  path — signup → onboarding → goal → evidence-backed skill assessment → dashboard reflecting real
  data (including the honest "insufficient evidence" bottleneck state) → sign-out/sign-in — plus a
  regression check for a mobile-nav overlap bug found during manual testing. Requires a migrated,
  seeded `DATABASE_URL` (same as dev); it starts its own `next dev` on port 3100 automatically.
  Uses the environment's pre-installed Chromium (`/opt/pw-browsers/chromium` by default — override
  with `PLAYWRIGHT_CHROMIUM_PATH` if running elsewhere); does not run `playwright install`.

## Project layout

See `docs/ARCHITECTURE.md`.
