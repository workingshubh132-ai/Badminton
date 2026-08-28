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

## Not started

**M3 — AI Coach + persistent structured athlete memory.**
Needs `ANTHROPIC_API_KEY` (not provisioned in this environment) and a decision on what the coach
synthesizes over given that matches/video don't exist yet — realistically this reads goals +
skill assessments + evidence and produces a narrative summary, clearly labeled as synthesis over
self-reported data, not an independent diagnosis. Should NOT be built as a chatbot with its own
memory — spec section 31 requires structured output written back to the athlete model.

**M4 — Match/video upload infrastructure.**
Needs a storage decision (S3-compatible, private, signed URLs — spec section 33 forbids public
video URLs) and `videos` + `video_jobs` tables (see `DOMAIN_MODEL.md`).

**M5 — Video processing pipeline + court/player detection.**
Separate Python service (see `ARCHITECTURE.md` "CV pipeline"). This is a genuinely large,
separate engineering effort — likely its own repo/deployment target, not a Next.js API route.

**M6 — Basic CV event detection.**
Depends on M5. Every detection carries a confidence score; below-threshold detections are surfaced
as "insufficient visual evidence," never silently dropped or guessed (spec section 7).

**M7 — Rally reconstruction.** Depends on M5/M6.

**M8 — Match analysis (Match Autopsy, spec section 10).** Depends on M7.

**M9 — "What should I have played?" decision engine (spec section 9).** Depends on M7/M8.

**M10 — Bottleneck engine (spec section 5).**
This is the dashboard's current honest gap: `hasEnoughEvidenceForBottleneck` is hard-coded `false`
in `src/app/(app)/dashboard/page.tsx` with a comment explaining why. Do not flip this to `true`
without the frequency/severity/opponent-exploitation evidence model this milestone requires —
that would be exactly the "fake numerical skill ratings" / fabricated-conclusion failure mode the
spec repeatedly warns against.

**M11 — Technique Lab.** Depends on M4 (video upload) at minimum.

**M12 — Movement analysis.** Depends on M5/M6.

**M13 — Longitudinal progress engine.**
Partially enabled by M2's data model (every `SkillAssessment` is timestamped and versioned per
skill), but the "solved weakness / regression / training-improvement-vs-match-transfer" reasoning
described in spec section 19/15 needs match data to mean anything.

**M14 — Coach collaboration.** `coach_observations` table (see `DOMAIN_MODEL.md`), plus a UI for a
coach account (role already exists on `User`, unused) to view and annotate an athlete's record.

**M15 — Opponent scouting.** Depends on M4/M5.

**M16 — Elite reference analysis.** Needs a real reference dataset before this can be anything but
marketing copy — spec section 12 is explicit that this must never become "you are X% as good as
[player]." Lowest priority until there's a credible data source.

**M17 — Tactical simulator (decision training, spec section 20).** Can start once the decision
taxonomy from M9 exists, so situations can be scored consistently.

**M18 — Advanced CV/biomechanics.** Depends on M5/M6 maturing.

**M19 — Tournament intelligence.** `tournaments` + `tournament_results` tables (see
`DOMAIN_MODEL.md`).

**M20 — Production hardening + observability + security + performance.**
Notable gaps already known from M1/M2 that belong here: no rate limiting on signup/login, no audit
log (spec section 33 requires one), no automated test suite yet (tracked separately — see
`README.md` "Testing"), no deployment target configured (local Postgres only).

## Sequencing note

M3 (AI Coach) is listed next in the master spec's suggested order, but M4-M10 (match/video
pipeline through bottleneck engine) are the ones that give the AI Coach and the dashboard
something real to reason over. Either order is defensible; this file doesn't prescribe which to
build next — that's a product call for the next session, not an architecture call.
