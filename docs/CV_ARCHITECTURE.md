# Computer vision architecture (M5)

M5 replaces `NullCvEngine` with the first real, measurable computer-vision capability: video
preprocessing, recording-quality assessment, badminton court detection/calibration, player
detection, and player tracking, plus the ground-truth evaluation infrastructure to actually measure
whether any of it works. See `docs/VIDEO_INTELLIGENCE.md` for the M4 upload/job infrastructure this
plugs into, and `docs/DOMAIN_MODEL.md` for the schema additions.

**The rule everything here follows, restated from the spec:** CV accuracy matters more than feature
count. Never fabricate a player location, a court coordinate, a confidence score, or a status.
When uncertain, the pipeline returns an honest low-confidence or failed result — never a
plausible-looking fake one. Every number in this document is either a measured result from this
codebase's own tests/eval run, or explicitly labeled as not yet measured.

**Explicitly out of scope for M5** (reserved for M6+): shuttle tracking, racket tracking, shot
classification, rally reconstruction, tactical analysis, opponent intelligence, biomechanics,
elite-player comparison. Nothing below claims any of these.

## Why a separate Python service, not CV-in-Node

`cv-service/` is a standalone FastAPI service, not a library called inline from a Next.js route —
per spec sections 20/34's explicit authorization to propose this if it's the technically correct
choice. The reasoning:

- Every viable, license-clean, CPU-runnable object-detection model with a maintained runtime today
  ships a Python-first (or Python-only) inference API. Forcing detection into Node would mean
  either shelling out to Python per-frame anyway (worse latency, harder error handling) or using a
  materially weaker/less-maintained JS binding.
- Classical CV (the court-detection approach — see "Court detection" below) needs OpenCV, which has
  a mature, fast, well-documented Python API; the Node bindings are thinner and less commonly
  exercised in production.
- A clean HTTP boundary (`POST /analyze`) keeps the two runtimes' dependency graphs, deployment
  targets, and scaling characteristics fully independent — Next.js never needs a native OpenCV/
  TensorFlow build in its own container image.

The cost is real and is paid deliberately: two services to run in dev (see "Deployment" below), and
an HTTP call from `PythonCvEngine` (`src/lib/video/python-cv-engine.ts`) instead of an in-process
function call. `CVAnalysisEngine` (`src/lib/video/cv-engine.ts`) is exactly the interface boundary
that makes this swap invisible to the rest of the app — see `docs/VIDEO_INTELLIGENCE.md` "CV engine
interface."

## Model selection

Three capabilities, three different kinds of model, chosen independently:

| Capability | Approach | Why |
|---|---|---|
| Person detection | **MediaPipe Tasks `ObjectDetector` + EfficientDet-Lite0** (COCO-pretrained, "person" class only) | Apache 2.0 license (commercial-use clean), ~14 MB, CPU inference in ~90 ms/frame on 4 CPU cores (measured in this environment), no GPU dependency — matches the "single phone recording, no professional hardware" reality the spec requires designing for. |
| Court detection/calibration | **Classical OpenCV** (Canny edges → probabilistic Hough line transform → convex hull of line endpoints → `approxPolyDP` quadrilateral fit → `findHomography`) — **not a learned model** | No labeled badminton-court dataset exists to train a detector on, and training one is out of scope for this milestone. A classical geometric pipeline fails in a legible, explainable way ("no lines found," "no stable quadrilateral") rather than as an opaque black box — see "Court detection" below for the honest account of when this is expected to work. |
| Player tracking | **Classical greedy IoU-based frame-to-frame association** — no model | No license question, fully explainable, and the association problem (which detection in frame N+1 is the same person as frame N) doesn't need a learned model at this milestone's scope (single-scene, low frame count, no re-identification-after-long-occlusion requirement). |

Model selection criteria actually applied before installing anything (spec section 20): license
(Apache 2.0 confirmed for MediaPipe/EfficientDet-Lite0), CPU-only runtime compatibility (verified —
this environment has no GPU), model size (14 MB, committed to the repo — see "Deployment"), inference
speed (measured, see "Performance" below), and platform/maintenance risk (MediaPipe Tasks is an
actively maintained Google library with a stable model zoo URL, not a one-off research checkpoint).

**Rejected: real-time full-court multi-object trackers (e.g. ByteTrack, DeepSORT) and pose
estimation for M5.** Both are genuinely useful for later milestones (M6+ shot/movement
classification) but add real complexity (embedding-based re-identification, a second model to
license and evaluate) this milestone's scope — basic player-on-court trajectory — doesn't need yet.
Greedy IoU tracking with explicit, never-silently-bridged gaps (see "Player detection and tracking"
below) is the honest, minimal thing that actually satisfies this milestone's requirement.

## Processing pipeline

`cv-service/app/pipeline.py`'s `run_analysis` orchestrates, in order:

```
probe_video (ffprobe via subprocess, mirrors the Next.js side's own independent probe)
  -> sample_frames (stride-based OpenCV VideoCapture, generator — never loads the whole video)
  -> assess_quality
       -> UNUSABLE? stop here (skip calibration/detection, return an honest partial result
          with a warning explaining why)
  -> calibrate_court (on a spread subset of sampled frames)
  -> detect (per sampled frame, the person detector)
  -> track_players (greedy IoU association across all sampled frames)
  -> enrich tracks with court_x/court_y (only if calibration produced a homography)
  -> assemble AnalysisResult with full ProcessingMetadata (engine/model versions, config,
     independently-computed video checksum, processing time)
```

Frame sampling defaults to 2 fps, capped at 600 sampled frames per run
(`DEFAULT_SAMPLING_FPS`/`DEFAULT_MAX_SAMPLED_FRAMES` in `cv-service/app/config.py`) — a deliberate
accuracy/cost trade for this milestone's scope (basic trajectory, not frame-perfect shot timing),
revisit once shot-level timing (M6+) needs finer sampling.

## Court detection

`cv-service/app/court.py`. Method: Canny edge detection → `cv2.HoughLinesP` → convex hull of all
line endpoints → `cv2.approxPolyDP` at multiple epsilon fractions to find a 4-point quadrilateral →
corner ordering (top-left/top-right/bottom-right/bottom-left, via the standard sum/difference
heuristic) → `cv2.findHomography` against the BWF doubles court boundary (6.1 m × 13.4 m).

Calibration runs across up to 8 spread sampled frames (`COURT_CALIBRATION_MAX_FRAMES`); a per-frame
quadrilateral is only kept if the frames' detected corners agree within
`_CORNER_AGREEMENT_TOLERANCE_FRACTION` of the overall median. `CourtCalibration.status` is one of
`NOT_ATTEMPTED` (no frames given, e.g. UNUSABLE quality), `FAILED` (no frame produced a usable
quadrilateral), `LOW_CONFIDENCE`/`PARTIAL` (frames disagree, or few frames agreed), or `SUCCESS`.

**Confidence is capped at `MODERATE`, never `HIGH`/`VERY_HIGH`, regardless of how many frames
agree.** HIGH confidence would require either a learned court detector with accuracy validated
against real badminton footage, or a manual corner-confirmation step — neither exists yet. This cap
is enforced in code (`app/court.py`), not just documentation, and is asserted by
`tests/test_court.py::TestCalibrateCourt::test_confidence_is_never_above_moderate`.

**An early, since-fixed bug is worth recording as a reminder of why this approach was chosen over a
simpler one:** the first implementation classified Hough lines into "near-horizontal"/"near-vertical"
groups by absolute angle and picked the outermost strong cluster per group as a boundary line. It
failed on the very first real (if synthetic) test: a trapezoidal court under camera perspective has
side-boundary lines at ~70°/110° — outside the near-vertical window — while a drawn centre service
line sits at exactly 90° and got mistakenly selected instead. The angle-classification approach was
replaced with the convex-hull + `approxPolyDP` approach described above, which is robust to
perspective distortion because it doesn't assume any line is axis-aligned. This is exactly the kind
of thing "write code, then actually run it against real content" catches that reading the code
never would.

`video_point_to_court(homography, x_px, y_px)` maps a single video-pixel point to real-world court
metres, returning `None` (never a fabricated position) for anything projecting more than a 2 m
margin outside the court boundary — a common signal of a bad homography or a genuinely off-court
point (e.g. a spectator).

## Player detection and tracking

`cv-service/app/detection.py` + `cv-service/app/tracking.py`.

**Detection**: EfficientDet-Lite0, filtered to the `person` COCO category,
`score_threshold=0.35` (`PERSON_DETECTION_SCORE_THRESHOLD`). `max_results=10` per frame — this
milestone does not assume the largest detected human is the athlete; see "Identity" below for how
that's actually handled (or, honestly, not yet fully handled).

**Tracking**: greedy per-frame IoU matching (`IOU_MATCH_THRESHOLD=0.25`), most-recently-active track
matched first each frame. A track that goes unmatched starts (or continues) a gap; a gap exceeding
`MAX_GAP_SAMPLES` (3 sampling intervals) closes the track rather than being bridged — a reappearing
detection after that starts a genuinely new track. **Tracks are never silently stitched across a
gap that exceeds this window** — this is the spec's explicit "never silently connect unrelated
detections into one trajectory" requirement, enforced in code and unit-tested
(`tests/test_tracking.py`: "never bridges far-apart detections," "long absence ends track").

Each `PlayerTrack.gaps` entry is `{start_seconds, end_seconds, reason}` — e.g. "Not reliably
detected (occlusion, motion blur, or left frame)" or "Track ended — not re-detected within the
gap-tolerance window," matching the spec's example format (`TRACKING GAP 00:31.20 → 00:31.63`,
rendered exactly that way on the video detail page).

**Trajectory representation**: each detection stores a normalized (0–1) bounding box; the tracked
point is the **bbox centre** (per the spec's explicit instruction), converted to real-world court
metres via the run's homography when calibration succeeded. This is a documented proxy, not a foot
position — a standing player's bbox centre is roughly torso height, which introduces real
(currently unmeasured) error versus true court position, especially for camera angles far from
directly overhead. Revisit if a future milestone needs sub-meter court-position accuracy.

**Identity (ATHLETE vs. OPPONENT vs. UNKNOWN)**: the engine **never guesses this** —
`cv-service/app/tracking.py` always returns `identity: UNKNOWN`, `identity_source: HEURISTIC`. This
was a deliberate, minimal-but-honest choice among the spec's suggested mechanisms (initial user
selection, court-side heuristic, tracking continuity): court-side and tracking-continuity heuristics
both require either a reliable calibration (not always available) or an assumption about camera
framing this milestone doesn't want to bake in silently. Instead, M5 ships the one mechanism that
can never be wrong by construction — **explicit human confirmation** —
(`confirmPlayerTrackIdentityAction` in `src/lib/actions/videos.ts`, surfaced as "This is me" /
"Opponent" buttons per track on the video detail page), which sets
`identity_source: USER_CONFIRMED` and records who confirmed it and when
(`PlayerTrack.identityConfirmedByUserId`/`identityConfirmedAt`). A heuristic identity assignment
(court side, tracking continuity) is a reasonable M6 addition once there's a real accuracy bar to
evaluate it against — see "Recommended M6" in the final report.

## Confidence model

Every detection carries a `score` (raw model confidence, 0–1) mapped to a 5-level
`ConfidenceLevel` (`VERY_LOW`/`LOW`/`MODERATE`/`HIGH`/`VERY_HIGH`) via `score_to_confidence` in
`cv-service/app/detection.py` — a direct, documented, monotonic threshold mapping
(`>=0.75` HIGH, `>=0.55` MODERATE, `>=PERSON_DETECTION_SCORE_THRESHOLD` LOW, else VERY_LOW), not an
invented scale. A track's confidence is the average of its member detections' scores, re-mapped
through the same function. Court calibration confidence is capped separately — see "Court
detection" above. Every `QualityAssessment`, `CourtCalibration`, and `PlayerTrack` carries its own
independent confidence/status; nothing downstream infers one from another.

## Acceptance thresholds

Quality thresholds (`cv-service/app/config.py`: `MIN_ACCEPTABLE_WIDTH=640`,
`MIN_GOOD_WIDTH=1280`, `MIN_ACCEPTABLE_FPS=15.0`, `MIN_GOOD_FPS=24.0`,
`MAX_BLANK_FRAME_RATIO=0.3`, `MAX_DECODE_FAILURE_RATIO=0.1`) and the blank-frame luminance-std
threshold (`BLANK_FRAME_STD_THRESHOLD=6.0` in `cv-service/app/quality.py`) are **explicitly marked
provisional in code**, chosen from general video-quality reasoning (a phone recording well under
720p or 15 fps is genuinely unreliable for tracking fast badminton movement) rather than from a
labeled dataset of badminton recordings graded by a human, because no such dataset exists yet. The
scoring bands (0 penalty = GOOD, 1–2 = ACCEPTABLE, 3–4 = POOR, 5+ = UNUSABLE, with each hard signal
— below-floor resolution, below-floor fps, excessive blank-frame ratio — contributing 3 points and
softer signals 1) were tuned once, against real unit-test cases exercising each signal in isolation
(`cv-service/tests/test_quality.py`), specifically so one hard failure alone reaches POOR rather
than being diluted into ACCEPTABLE. **These thresholds should be revisited once real badminton
footage across the diverse conditions in "Ground-truth evaluation" below has been collected and
graded** — until then, treat POOR/UNUSABLE boundary calls as reasonable-but-unvalidated, not as
data-derived truth.

Person-detection score threshold (`0.35`) and the IoU match threshold (`0.25`) are similarly
reasoned defaults (a lower score threshold risks false positives on court-colored background
regions; a lower IoU threshold risks bridging two different people standing close together),
**not** derived from a precision/recall sweep against labeled badminton footage — that sweep is the
natural next step once real footage exists (see "Test fixtures and the real-footage gap").

## Data contracts

`cv-service/app/schemas.py` is the authoritative wire contract (`AnalysisResult`, `QualityAssessment`,
`CourtCalibration`, `PlayerTrack`, `Detection`, `TrackingGap`, `ProcessingMetadata`) — pydantic
models serialized as-is (snake_case field names, no camelCase alias generator) over `POST /analyze`.
`src/lib/video/python-cv-engine.ts` mirrors this exactly as private `Wire*` TypeScript interfaces
and translates it field-for-field into the app's own camelCase `CV*` types
(`src/lib/video/cv-engine.ts`) — see `python-cv-engine.test.ts::mapWireResult` for a test asserting
that translation is lossless and never invents a value the wire response didn't send.

The contract is deliberately extensible: `AnalysisResult` has room for future `pose`/`shuttle`/
`racket`/`shot`/`movement`/`rally` sections without forcing a breaking change to today's shape —
nothing in M5 tries to guess that future shape ahead of time.

### Storage: Postgres vs. object storage

`VideoQualityAssessment`, `CourtCalibration`, and `PlayerTrack` (see `docs/DOMAIN_MODEL.md`) all
live in Postgres as structured, typed, indexed rows — not object storage — because every field is
small, bounded, and needs to be queried/joined against `Video`/`Athlete`/`User` for authorization
and display. The one deliberate storage-shape decision: `PlayerTrack.detections`/`.gaps` are JSON
array columns on the track row itself, **not** a row-per-detection child table (see the extended
reasoning in `prisma/schema.prisma`'s M5 comment block) — the only access pattern that exists or is
planned is "read one track's whole trajectory," never a SQL filter across individual points, and at
the ~2 fps sampling rate even a long match keeps a track's JSON payload to a few thousand small
objects. **No raw video frames or images are ever written to Postgres** — sampled frames exist only
transiently in `cv-service`'s process memory during one `/analyze` call and are never persisted;
`VideoStorageProvider` (see `docs/VIDEO_INTELLIGENCE.md`) remains the only place video bytes live.

### Evidence integration boundary

CV observations are **capable of** becoming `Evidence` (the `CV_SYSTEM`/`AI_SYSTEM` values on
`EvidenceSource`, and `Evidence.confidence`/`.metadata`, were reserved for exactly this in M4 — see
`docs/DOMAIN_MODEL.md`), but **M5 does not auto-create any `Evidence` row from a detection, a
calibration, or a track.** A raw CV observation ("a player was tracked with MODERATE confidence
from 0:04–0:31") is not the same thing as a coaching conclusion, and collapsing that distinction is
exactly the "fabricated conclusion" failure mode the spec repeatedly warns against. The layering
stays: **observation** (`VideoQualityAssessment`/`CourtCalibration`/`PlayerTrack` rows, this
milestone) → **evidence** (a human- or future-system-authored `Evidence` row that *cites* an
observation) → **interpretation** → **coaching conclusion** (both future milestones). The one
human-driven write this milestone adds near this boundary is identity confirmation
(`confirmPlayerTrackIdentityAction`) — a factual label on an existing observation, not a generated
conclusion.

## Ground-truth evaluation

Required by spec, not optional. `cv-service/eval/` is a framework separate from the pytest unit
suite (`cv-service/tests/`), matching the spec's explicit "maintain a separate CV evaluation
command/test suite for actual model inference" instruction — pytest asserts pass/fail against known
expectations for fast, deterministic CI use; `eval/evaluate.py` *reports* real measured numbers
against every labeled fixture in `eval/ground_truth/`, for human review, run with:

```bash
cd cv-service && source .venv/bin/activate && python3 eval/evaluate.py
```

Metrics computed, never invented (spec section 17): court calibration compares detected vs.
ground-truth corners via mean/max per-corner Euclidean pixel error and quadrilateral IoU (via
rasterized mask intersection — `cv2.fillPoly` + `np.logical_and`/`logical_or`, correct for
non-axis-aligned shapes, unlike a naive bbox IoU). Player-tracking ground truth (precision, recall,
identity switches) is supported by the same framework's structure but has no real fixture to run it
against yet — see the gap below.

### Test fixtures and the real-footage gap

**Only one fixture exists today: `eval/fixtures/synthetic_court_01.mp4`, and it is explicitly
non-photorealistic.** `eval/fixtures/generate_synthetic_fixture.py` renders a flat-shaded court
(known-exact trapezoidal corners, simulating camera perspective) with a solid-rectangle "player"
proxy, entirely via OpenCV drawing calls — no real camera, no real court, no real human. Its
matching `eval/ground_truth/synthetic_court_01.json` records the exact corner pixel coordinates and
the rectangle's per-frame position, so `evaluate_court_calibration` has a known-correct answer to
compare against.

**What this fixture validates:** the calibration *geometry* is implemented correctly — corner
detection, corner ordering, homography computation, IoU/error math. Measured result: mean corner
error 2.99 px, max 4.24 px, IoU 0.988 against ground truth (`python3 eval/evaluate.py` output,
this session).

**What this fixture does NOT validate:** real-world court-detection accuracy on actual badminton
footage (real courts have shadows, uneven lighting, ad boards, spectators, worn/faded lines, and
non-trapezoidal lens distortion none of which this fixture has), and person-detection accuracy is
not benchmarked against it at all — the "player" is a solid rectangle with no human shape, so a
correctly-working detector should (and does) find zero people in it. The only person-detection
accuracy check in this codebase (`tests/test_detection.py::TestPersonDetectorRealInference`) uses a
single real photograph — `skimage.data.astronaut()`, a NASA public-domain image bundled in the
versioned `scikit-image` PyPI package, chosen specifically because this environment's outbound
network proxy blocks arbitrary web image fetches (verified: a direct request to Wikimedia Commons
returned a 403 from the proxy) and scraping an unlicensed image was not an acceptable alternative.
That test confirms the detector fires on *a* real human shape with reasonable confidence and a
sane bounding box — it says nothing about badminton-specific accuracy (players in athletic poses,
mid-court, at varied distances and angles).

**This is a real, open gap, stated plainly rather than glossed over:** neither the court detector
nor the person detector has been evaluated against real badminton footage in this codebase.
Person-detection accuracy in general is covered only by the model vendor's own published COCO
benchmark figures (cited, not independently reproduced here). Closing this gap needs a small,
curated set of real (or at minimum realistic) badminton clips across the diverse conditions the
spec calls for — lighting, motion blur, near-baseline/near-net framing, occlusion, camera height/
angle, clothing, court color — each with hand-labeled court corners and player bounding boxes, then
run through `eval/evaluate.py`. No such clips are available in this environment (no camera, no
licensed badminton footage source), so this remains the single most important recommended M6 item.
**Until that evaluation exists, do not present this pipeline's real-footage accuracy as validated —
it has only been proven correct on synthetic geometry.**

## Provenance

Every `VideoJob` row carries `engineName`/`engineVersion` (already present since M4) plus a new
`resultMetadata` JSON column (the full `ProcessingMetadata` payload: model versions, sampling fps,
frames sampled, config, an independently-computed SHA-256 of the video file — `cv-service`
re-hashes the file itself rather than trusting the Next.js-reported checksum, for genuine
reproducibility rather than a copied value). Every `CourtCalibration`/`VideoQualityAssessment`/
`PlayerTrack` row links back to the exact `VideoJob` that produced it (`videoJobId`, `@unique` for
the 1:1 rows) — re-analyzing a video creates a new `VideoJob` and a new set of rows rather than
overwriting the previous run, so every past run stays inspectable.

## Security

`cv-service` is an internal-only service, never internet-facing — it is invoked exclusively by
`PythonCvEngine` over `localhost`/the shared host, with an optional shared-secret header
(`X-Internal-Token`, checked against `CV_SERVICE_TOKEN`) as defense-in-depth against a stray local
process on the same host, not as internet-facing authentication (`cv-service/app/main.py`). All
real athlete/video authorization stays exactly where M4 put it: the Next.js app resolves a
`videoId` to an owned `Video` row (`athleteId` from the session, never client-supplied) *before*
ever calling the CV engine, and every `VideoQualityAssessment`/`CourtCalibration`/`PlayerTrack`
query on the video detail page is scoped through that same already-checked `video.id` — see
`src/app/(app)/videos/[videoId]/page.tsx`. `confirmPlayerTrackIdentityAction` re-verifies both video
ownership and that the target track belongs to that specific video before writing, the same
double-scoping pattern already proven (and e2e-tested) for `associateVideoWithMatchAction` in M4.

## Failure handling

Every real failure mode has explicit, distinct handling, never a downstream fabrication from
invalid upstream data:

- **ffmpeg/ffprobe unavailable or the file won't decode** — `probe_video` raises; `run_analysis`
  never gets valid `VideoInfo`, so `assess_quality` marks the result `UNUSABLE` with a specific
  reason rather than guessing metadata.
- **Model fails to load** — `PersonDetector()` raises at service startup (inside FastAPI's
  `lifespan`), so the service fails to come up rather than silently serving requests with no
  detector; `GET /health`'s `model_loaded` field reflects real state.
- **Court can't be detected** — `CourtCalibration.status = FAILED`, with `warnings` explaining why
  (no usable quadrilateral found), never a fabricated homography.
- **Player can't be detected / tracking fails** — an honest empty `tracks: []` with a warning ("No
  people were detected in any sampled frame"), never an invented trajectory.
- **cv-service unreachable, times out, or returns a non-2xx response** —
  `PythonCvEngine.analyze` (`src/lib/video/python-cv-engine.ts`) catches all three distinctly and
  returns `status: "failed"` with a specific message (connection error text, "did not respond
  within Ns," or the HTTP status/body) — never throws uncaught into the job runner, and never
  reports `"completed"` for a call that didn't actually complete. All four paths are unit-tested
  (`python-cv-engine.test.ts`).
- **Storage backend has no local filesystem path** (a future non-local `VideoStorageProvider`) —
  `PythonCvEngine` returns `status: "unavailable"` (not `"failed"` — this is a configuration
  limitation, not a broken attempt) before ever calling the service.

## Observability

`cv-service/app/main.py`'s logger never logs frame pixel data or full file path contents — only
video ids, statuses, and error summaries — since request paths can include filesystem layout
information not meant for a log aggregator. `GET /health` reports real, checked state
(`model_loaded`) rather than a static "ok."

## Performance

Measured in this environment (CPU-only, 4 cores, no GPU) against the synthetic fixture (5 s,
1280×720, 24 fps, sampled at 2 fps → 10 frames):

- Person-detector inference: ~90 ms/frame (measured during model verification this session).
- Full pipeline (`run_analysis`, includes preprocessing, quality, calibration across 8 frames,
  detection across 10 frames, tracking, checksum): **0.855 s**, per real `processing_metadata`
  output from a live `/analyze` call in this session.
- Model load (once, at service startup): a few hundred ms, not separately profiled — happens once
  per service process lifetime, not per request.

These numbers are for a 5-second clip; they scale roughly linearly with `frames_sampled`, which
itself scales with video duration at the configured sampling fps (default 2 fps, capped at 600
frames — see "Processing pipeline"). **Not yet measured: performance on a full-length (30–90
minute) match recording.** At 2 fps that's 3,600–10,800 requested samples, capped at 600 by
`DEFAULT_MAX_SAMPLED_FRAMES` — meaning a long match is effectively sub-sampled to a sparser
effective rate than 2 fps, a real accuracy/cost trade worth revisiting once real long-form footage
exists to test against.

**Known limitation carried from M4, now actually triggered (see "Known limitations" below):**
`job-runner.ts` invokes `CVAnalysisEngine.analyze()` inline, in the same request that triggered
analysis — this was honest in M4 because `NullCvEngine` resolved instantly, and is explicitly
flagged in `job-runner.ts`'s own module comment as the trigger condition for moving to a real
queue. A ~1 s clip is fine inline; a multi-minute real match recording, at real-world sampling
volumes, would not be. M5 adds a client-side timeout (`PythonCvEngine`, default 10 minutes) so a
slow or hung call fails honestly rather than hanging the request forever, but does not build a real
background queue — that's a bigger architectural decision than this milestone should make
unilaterally (see "Recommended M6" in the final report).

## Deployment

Running `cv-service` locally:

```bash
cd cv-service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then set `CV_SERVICE_URL="http://127.0.0.1:8000"` in the Next.js app's `.env` (see
`.env.example`) — `getCvEngine()` (`src/lib/video/cv-engine.ts`) uses `PythonCvEngine` when this is
set, and falls back to `NullCvEngine` (the honest "unavailable" default) when it isn't, so CI and
any environment that hasn't started `cv-service` are unaffected by its absence.

**Single-host assumption, stated explicitly (not yet solved for multi-host deployment):**
`AnalyzeRequest.video_path` is an absolute filesystem path, not an uploaded file or a URL —
`PythonCvEngine` resolves it via `VideoStorageProvider.getLocalFilesystemPath` (a new method added
this milestone, replacing job-runner.ts's previous hand-rolled, duplicated path-join logic for
ffprobe) and passes it directly to `cv-service`, which reads the file straight off disk. This means
Next.js and `cv-service` must share a filesystem (same host, or a shared volume) — a real
constraint for a future multi-host deployment, where either the video would need to be streamed to
`cv-service` over HTTP or both services would need access to shared object storage. Not solved here;
flagged as a real deployment decision for whenever this moves off a single host.

**The 14 MB model file (`cv-service/models/efficientdet_lite0.tflite`) is committed to the repo**,
not fetched at runtime or via a package registry. This is a deliberate choice: the spec requires CI
not depend on unreliable external model downloads, and no artifact/package hosting is set up for
this project. Revisit if the model set grows large enough that this stops being the pragmatic
choice (e.g. Git LFS, or a dedicated model-artifact store).

The Python venv (`cv-service/.venv/`), pytest cache, and `__pycache__` directories are gitignored;
only source, tests, `eval/`, the committed synthetic fixture (60 KB), and the model file are
tracked.

## Known limitations

- **Real-footage accuracy is unvalidated** — see "Test fixtures and the real-footage gap" above.
  This is the single biggest open item.
- **No learned court detector** — the classical approach is explainable and correctness-tested on
  synthetic geometry, but is expected to often return `LOW_CONFIDENCE` or `FAILED` on real,
  textured, unevenly-lit court footage (shadows, ad boards, worn lines all break Hough-line
  assumptions in ways a learned detector would handle better).
- **Bbox-centre trajectory, not foot position** — a documented proxy per spec instruction, with
  unmeasured real-world court-position error.
- **Identity is never heuristically assigned** — every track starts `UNKNOWN` until a human
  confirms it; there is no court-side or tracking-continuity heuristic yet (a deliberate,
  documented "reliable subset now, note the gap" choice — see "Player detection and tracking"
  above).
- **CV analysis still runs inline in the HTTP request that triggers it** (inherited from M4's
  job-runner design, now genuinely exercised by real model latency) — bounded by a client timeout,
  not yet moved behind a real background queue.
- **No performance data on full-length match recordings** — only a 5-second synthetic clip has been
  measured end-to-end.
- **Single-host filesystem-sharing assumption** between Next.js and `cv-service` — see
  "Deployment" above.
- **Acceptance thresholds are provisional**, not derived from a labeled badminton-footage dataset —
  see "Acceptance thresholds" above.
- **Player-tracking ground-truth evaluation has no real fixture** — the evaluation framework
  supports it structurally, but only court-calibration metrics have an actual fixture to run
  against today.

## Future CV roadmap (M6+)

In rough dependency order: (1) collect and hand-label a small real-footage evaluation set across
the spec's required diverse conditions, and re-run/re-tune acceptance thresholds against it —
unblocks validating everything above; (2) court-side/tracking-continuity identity heuristics, now
that there's real data to evaluate them against; (3) move CV analysis invocation behind a real
background queue once real-match-length processing times are actually measured; (4) shuttle and
racket tracking; (5) shot classification; (6) rally boundary detection, building on the now-real
`Rally`/`Event` writer this unlocks (schema already exists from M4).
