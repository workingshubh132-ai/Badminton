# Domain model

## Currently implemented (M1 + M2 + M4 + M5)

Source of truth: `prisma/schema.prisma`. Summary:

| Model | Purpose | Notes |
|---|---|---|
| `User` | Auth identity | `role` (`PLAYER`/`COACH`/`ADMIN`), bcrypt `passwordHash`. Only `PLAYER` is reachable from the UI today. |
| `Athlete` | Stable identity record | 1:1 with `User` for now. Split from `AthleteProfile` so identity and mutable profile data don't share a table — see rationale below. |
| `AthleteProfile` | Mutable/extended profile | Self-reported competitive level, academy/coach names, physical basics, notes. Never a computed ranking. |
| `Goal` | Player/coach-chosen objective | Distinct from a *bottleneck* (system-identified) — a goal is something the player deliberately chose. |
| `Skill` | Seeded reference catalog | 61 rows across 5 categories, from spec section 4. Not user-editable. |
| `SkillAssessment` | A point-in-time judgment about one skill | Always has `level`, `confidence`, `trend`, `status`, `source`, a required written `summary`, and at least one `Evidence` row — enforced by `createAssessmentAction` creating both in one write, not by a DB constraint. |
| `Evidence` | The concrete observation backing a claim | Generalized in M4 — see "Generalized evidence model (M4)" below. Attaches to a `SkillAssessment`, `Match`, or `Video` (exactly one, DB-enforced). |
| `Match` | A recorded match | Athlete, opponent, date, result, free-text score/notes. `status` stays `UNPROCESSED` until a real CV pipeline exists (M7+). |
| `Video` | An uploaded video file | `MATCH`/`TRAINING`/`TECHNIQUE`/`OTHER`. Full status state machine — see `docs/VIDEO_INTELLIGENCE.md` "Video lifecycle." Metadata (duration/dimensions/frame rate) only ever populated from a real prober, never guessed. |
| `VideoJob` | A processing or CV-analysis attempt for a video | See `docs/VIDEO_INTELLIGENCE.md` "Job architecture" for why this is one table with a `type` discriminator rather than two. |
| `Rally`, `Event` | Schema-only foundation for M7-M9 | No code path writes either table yet — see `docs/VIDEO_INTELLIGENCE.md` "Match / Rally / Event foundation." |
| `VideoQualityAssessment` | Real, measured recording-quality result for one CV analysis run | 1:1 with a `CV_ANALYSIS` `VideoJob` (`videoJobId` unique). `status` (`GOOD`/`ACCEPTABLE`/`POOR`/`UNUSABLE`) with specific `reasons`, never a bare score. See `docs/CV_ARCHITECTURE.md`. |
| `CourtCalibration` | Court-boundary detection + video-px→court-metres homography for one run | 1:1 with a `CV_ANALYSIS` `VideoJob`. Confidence capped at `MODERATE` — see `docs/CV_ARCHITECTURE.md` "Court detection." |
| `PlayerTrack` | A tracked person's trajectory for one run | Many per `VideoJob`. `identity` starts `UNKNOWN`/`HEURISTIC`; only a human confirmation (`confirmPlayerTrackIdentityAction`) sets `ATHLETE`/`OPPONENT`/`USER_CONFIRMED`. `detections`/`gaps` are JSON arrays on the row — see the storage-shape reasoning in `schema.prisma`'s M5 comment block. |

### Why `Athlete` and `AthleteProfile` are separate tables

`Athlete` is the identity anchor everything else (goals, assessments, and later matches/videos)
foreign-keys to. `AthleteProfile` holds attributes that change independently of identity and are
queried together (bio, physical stats, academy/coach names, long-term goal). Splitting them means
profile edits never touch the row other tables reference, and it leaves room for a future
"profile history" or multi-coach-view feature without reshaping the identity table.

### Why `SkillAssessment.level` is a 5-band enum, not a number

Spec section 3 explicitly forbids "fake numerical skill ratings with no evidence," and section 27
requires every conclusion to carry an honest confidence level rather than false precision. A
`0-100` score implies a precision the underlying evidence (a self-reported note, at this stage)
cannot support. `EMERGING / DEVELOPING / SOLID / STRONG / ADVANCED` is coarse on purpose.

### Generalized evidence model (M4)

M2 shipped `Evidence` with a required, non-nullable `skillAssessmentId`, explicitly deferring
generalization until there was a second real consumer to design against (see the git history of
this file for that original reasoning). M4's product spec explicitly calls for generalizing it
("GENERALIZED EVIDENCE SYSTEM" is one of the milestone's named objectives), and now gives it two
real second/third consumers — `Match` and `Video` — so the extension happened for real:

- `skillAssessmentId`, `matchId`, `videoId` are all nullable FKs on `Evidence`; a Postgres `CHECK`
  constraint (`evidence_exactly_one_subject`, added by hand in the M4 migration since Prisma has no
  schema-level `CHECK` syntax) guarantees exactly one is set per row — real referential integrity,
  not application-level convention alone.
- A generic polymorphic `(subjectType, subjectId)` pair was deliberately **not** used — it would
  give up real foreign-key constraints (Postgres can't enforce "this ID exists in whichever table
  `subjectType` names"), and Prisma can't express a polymorphic relation as a typed relation at
  all. Named nullable FKs, one per real subject, keep every relation type-safe and enforced.
- `Evidence.athleteId` was added as a **direct**, always-present column, even though it's always
  derivable by joining through whichever subject FK is set. This redundancy is deliberate: every
  authorization check (`WHERE athleteId = currentAthleteId`) becomes uniform regardless of subject
  type, rather than needing a different join per subject and risking a missed case. Direct
  ownership columns for authorization simplicity are a standard, worthwhile trade on a
  security-sensitive table.
- `confidence`, `timestampSeconds`, and `metadata` were added as nullable fields per the spec's
  explicit field list for this milestone's evidence model, even though only `timestampSeconds` has
  a real writer today (the video-evidence form). `confidence` and `metadata` are reserved for
  CV/AI-sourced evidence (M5+) — unlike most "no writer yet" decisions in this codebase, these were
  added now because generalizing this exact model, with this exact field list, *is* the M4 work
  item the spec asked for, not a speculative extension ahead of it.
- `rallyId`, `eventId`, and `hypothesisId` were deliberately **not** added. `Rally`/`Event` exist as
  schema-only foundation with no writer (see `docs/VIDEO_INTELLIGENCE.md`), and no `Hypothesis`
  table exists at all — the master spec explicitly says not to build a hypothesis engine before
  it's genuinely part of the milestone (that's M10). These are the documented next extension
  points, added when M7/M9/M10 give them a real producer, following the same pattern this file
  already used for M2→M4.

### Why `AssessmentSource` has values with no UI path yet

`COACH_OBSERVATION`, `AI_VIDEO_ANALYSIS`, and `MATCH_EVIDENCE` exist in the enum but only
`SELF_REPORT` is reachable from the current UI. This is a forward-compatible schema decision, not
fabricated functionality: adding a source value later (M5 CV pipeline, M14 coach collaboration)
won't require a breaking migration or a data backfill.

### CV result models (M5)

`VideoQualityAssessment`, `CourtCalibration`, and `PlayerTrack` are keyed 1:1 (the first two) or
many (`PlayerTrack`) to a `CV_ANALYSIS` `VideoJob` via `videoJobId`, not just to the `Video` — a
video can be re-analyzed, and each run's rows stay distinct rather than being overwritten, so past
runs remain inspectable. All three are structured Postgres rows, not object/blob storage — full
storage-shape reasoning (including why `PlayerTrack.detections`/`.gaps` are JSON array columns on
the row rather than a row-per-detection child table) lives in `schema.prisma`'s M5 comment block
and `docs/CV_ARCHITECTURE.md` "Data contracts." `VideoJob.resultMetadata` (a new nullable JSON
column) carries the parts of the CV service's `ProcessingMetadata` response that don't have fixed
columns yet (model versions, sampling config, independently-computed video checksum) — see
`docs/CV_ARCHITECTURE.md` "Provenance."

`PlayerTrack.identity` deliberately starts `UNKNOWN`/`HEURISTIC` and is never heuristically guessed
by the CV engine — see `docs/CV_ARCHITECTURE.md` "Player detection and tracking" for why, and for
the human-confirmation write path (`identitySource: USER_CONFIRMED`,
`identityConfirmedByUserId`/`identityConfirmedAt`) this milestone ships instead.

## Target schema (full spec section 32 domain, for later milestones)

The spec's suggested table list, reasoned through rather than copied verbatim:

**Already implemented:** `users`, `athletes`, `athlete_profiles`, `goals`, `skills`,
`skill_assessments`, `evidence` (generalized in M4 — see above), `matches` (as `Match`), `videos`
(as `Video`), `video_jobs` (as `VideoJob`, unified across the processing/analysis job types — see
`docs/VIDEO_INTELLIGENCE.md`), schema-only `rallies`/`events` (as `Rally`/`Event`, no writer yet),
and, from M5, `court_calibrations` (as `CourtCalibration`), player tracking (as `PlayerTrack` — the
spec's suggested `pose_data` shape isn't needed yet since M5 tracks bounding boxes, not skeletons —
see below), and `VideoQualityAssessment` (not in the spec's suggested table list, added because a
measured recording-quality result needed somewhere real to live — see `docs/CV_ARCHITECTURE.md`).

**M6-M7 (shot/pose detection, rally reconstruction — builds on M5's court calibration + player tracking):**
- `pose_data` — per-frame (or sampled) skeleton/joint data. Not built in M5: M5's player detection
  is bounding-box-only (no pose/keypoint model evaluated or installed yet — see
  `docs/CV_ARCHITECTURE.md` "Model selection"). A real addition, not a rename, once a pose model is
  selected.
- Generic structured detections (shuttle position, racket position, classified shots and
  movement — spec's `cv_events`/`movement_events`/`shots`) reuse the `Event` model added in M4
  (`category`, `shotType`, `confidence`, `courtX`/`courtY`, `metadata`) rather than three more
  tables — `Event` was already designed to carry exactly this shape. `Rally` (also added in M4,
  schema-only so far) gets its first real writer here: shot-sequence reconstruction of one rally —
  serve, sequence, outcome, key decision points (spec section 8).
- `match_sets` — a match is a container of sets; a set is a container of rallies. Not yet modeled;
  `Match.score` stays free text (see `docs/VIDEO_INTELLIGENCE.md` "Match / Rally / Event
  foundation") until this exists to populate it for real.
- `players` — for opponent tracking within a match where the opponent isn't a registered `Athlete`.
  M5's `PlayerTrack.identity` (`ATHLETE`/`OPPONENT`/`UNKNOWN`) is a per-video-run label, not a
  standing opponent identity/profile — a real `players` table (name, notes, matches played against)
  is still open, most relevant once M15 (opponent scouting) needs it.

**M9 (decision engine):**
- `decision_points` — a rally moment flagged as tactically significant (score situation, position,
  options available).
- `decision_evaluations` — the AI's structured judgment on a decision point (best/strong
  alternative/acceptable/low-percentage/poor/forced/unavoidable — spec section 9's taxonomy), always
  with confidence and reasoning, never a bare verdict.

**M10 (bottleneck engine):**
- `bottlenecks` — a system-identified weakness, distinct from a `Goal` (player-chosen). Carries
  frequency/severity/impact fields and a `status` (primary/secondary/monitor — spec section 5).
- Bottleneck evidence reuses the `Evidence` extension point described above rather than a new table.

**M14 (coach collaboration):**
- `coach_observations` — a coach's note, optionally linked to a skill/goal/bottleneck. Spec section
  17 requires the system to store both AI and human observations *without* either silently
  overriding the other — `coach_observations` and `skill_assessments` (with `source: AI_VIDEO_ANALYSIS`)
  coexist rather than one being merged into the other.

**M15 (opponent scouting):**
- `opponents` — a scouted player (may or may not be a registered `Athlete`).
- `tactical_patterns` — observed tendencies, always with a confidence and the evidence count behind it.

**M18-M19 (advanced CV, tournaments):**
- `tournaments`, `tournament_results` — competition history and results, feeding the "international
  development gap" model in spec section 22 (never a computed ranking — a gap analysis with named
  dimensions and evidence).

**Deliberately deferred / not planned as literal tables:**
- `recovery_logs`, `mental_performance_logs` — spec section 28 restricts this product from medical
  claims. If these land, they'll be scoped tightly to performance language (e.g., "shot selection
  became more conservative late-game" — spec section 21), not physiological/medical fields, and
  will be designed against real requirements from M13 (longitudinal engine) rather than speculated
  now.
- `ai_recommendations`, `recommendation_outcomes` — reasonable future tables (M18/M20 territory:
  did a recommended intervention actually get followed, did it help), deferred until the
  Development Recommendation Engine (spec section 18) exists to populate them.

The guiding rule for all of the above, restated from spec section 34/35: build the table when a
milestone needs to write to it, not before. A schema with columns nothing writes to is exactly the
kind of fabricated-looking functionality section 41 warns against.
