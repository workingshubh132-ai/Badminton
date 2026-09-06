# M5.5: Real-World CV Validation

M5.5 is a validation gate for the M5 computer-vision pipeline. It provides infrastructure for:

1. **Dataset ingestion** — Import real badminton videos with proper licensing metadata
2. **Clipping** — Create short evaluation clips from source videos
3. **Annotation** — Web UI for marking court corners and player bounding boxes
4. **Evaluation** — Run M5 pipeline against annotated clips and compute accuracy metrics
5. **Reporting** — Generate comprehensive evaluation reports with component readiness classifications

## What M5.5 Does NOT Do

- Shuttle/racket tracking
- Shot classification
- Rally reconstruction
- Tactical analysis
- Game-state reasoning
- Decision intelligence
- AI coaching

M5.5 is **perception validation only**. It answers: "Does the existing M5 pipeline work reliably on real badminton footage?"

## Workflow

```
1. Ingest real video
   ↓
2. Create clips from video
   ↓
3. Annotate clips (ground truth)
   ↓
4. Run M5 pipeline on clips
   ↓
5. Calculate accuracy metrics
   ↓
6. Generate evaluation report
   ↓
7. Recommend next step (A-F)
```

## Quick Start

### 1. Ingest a Video

```bash
python -m eval.ingest path/to/badminton.mp4 \
  --license licensed \
  --source-url "https://example.com/video" \
  --camera "sideline" \
  --players "Alice" "Bob" \
  --notes "Tournament match, good lighting"
```

This creates a unique video ID and stores metadata.

### 2. Create Evaluation Clips

```bash
python -m eval.clipping video_20260906_120000_badminton \
  --start 10.0 \
  --end 25.0 \
  --camera "sideline" \
  --court-visible \
  --players 2
```

Clips should be:
- 10-30 seconds long
- Full court visible
- Both players visible
- Variety of player positions and movements

Target: **5-10 clips** from different videos/angles.

### 3. Annotate Clips

Start the annotation server:

```bash
python -m eval.annotation_server --port 5000 --dataset-dir cv-service/eval/datasets
```

Then visit http://localhost:5000 to annotate:
- Mark court corners (4 points)
- Draw player bounding boxes
- Assign identity (athlete/opponent/unknown)
- Mark frame quality (good/acceptable/poor/unusable)

### 4. Run Evaluation

```bash
python -m eval.evaluate_real clip_20260906_120015_video_001_10-25 \
  --sampling-fps 2.0
```

This runs the M5 pipeline and computes:
- Court detection accuracy (corner error, IoU)
- Player detection accuracy (precision, recall)
- Player tracking accuracy (continuity, gaps)
- Quality assessment accuracy

### 5. Generate Report

```bash
python -m eval.report_generator --dataset-dir cv-service/eval/datasets
```

Produces:
- `M5.5_EVALUATION_REPORT.md` — human-readable summary
- `M5.5_EVALUATION_REPORT.json` — machine-readable data

## Dataset Structure

```
cv-service/eval/datasets/
├── inventory.json          # Central dataset registry
├── videos/                 # Source videos
│   ├── video_001.mp4
│   └── video_002.mp4
├── clips/                  # Evaluation clips
│   ├── clip_001_10-25.mp4
│   └── clip_002_15-30.mp4
├── annotations/            # Ground-truth annotations
│   ├── clip_001_10-25.json
│   └── clip_002_15-30.json
├── evaluations/            # M5 evaluation results
│   ├── clip_001_10-25.json
│   └── clip_002_15-30.json
└── overlays/               # Visual comparison outputs
    ├── clip_001_10-25_overlay.mp4
    └── clip_001_10-25_frame_000.jpg
```

## Annotation Format

Annotations are stored as JSON (`v1` schema):

```json
{
  "version": "1.0",
  "clip_id": "clip_20260906_120015_video_001_10-25",
  "created_at": "2026-09-06T12:00:15Z",
  "annotator": "alice",
  "frames": [
    {
      "frame_index": 0,
      "timestamp_seconds": 0.0,
      "quality": "good",
      "court_corners": {
        "top_left": [0.15, 0.10],
        "top_right": [0.85, 0.10],
        "bottom_right": [0.90, 0.90],
        "bottom_left": [0.10, 0.90]
      },
      "players": [
        {
          "identity": "athlete",
          "bbox": {"x1": 0.20, "y1": 0.30, "x2": 0.35, "y2": 0.50},
          "confidence": 0.95
        },
        {
          "identity": "opponent",
          "bbox": {"x1": 0.65, "y1": 0.40, "x2": 0.80, "y2": 0.60},
          "confidence": 0.90
        }
      ]
    }
  ]
}
```

Coordinates are **normalized to [0, 1]** where (0,0) is top-left and (1,1) is bottom-right.

## Component Readiness Classifications

Each M5 component receives exactly one status:

- **PRODUCTION_READY** — Reliable on real footage, ready for M6
- **VALIDATION_READY** — Promising, needs monitoring
- **NEEDS_IMPROVEMENT** — Works but has known issues
- **UNRELIABLE** — Cannot safely support downstream analysis

## Decision Gate (A-F)

At the end, the report recommends **exactly one** next step:

- **A** — Proceed to M6 (all components production/validation ready)
- **B** — Improve court detection (unreliable court calibration)
- **C** — Improve player detection (low precision/recall)
- **D** — Improve tracking (fragmented tracks)
- **E** — Improve quality assessment (accuracy issues)
- **F** — Redesign perception architecture (multiple critical failures)

## Important: Licensing

**Every external video MUST have proper licensing metadata.**

- **LICENSED** = We have explicit permission to download, modify, analyze, and retain
- **REFERENCE** = Elite/research footage for reference only, not distributable

Never silently treat copyrighted footage as commercially reusable training data.

## Python Dependencies

```
opencv-python
numpy
flask
pydantic
ffmpeg-python (system: apt install ffmpeg)
```

Ensure `ffprobe` and `ffmpeg` are on PATH:

```bash
apt install ffmpeg
```

## Testing M5.5

Run existing test suite to ensure no regressions:

```bash
# Python tests
cd cv-service && pytest

# TypeScript tests
npm test

# E2E tests
npm run test:e2e
```

Everything must remain green.

## Example Workflow: 5-Clip Evaluation

```bash
# 1. Get 5 different badminton videos (with licenses!)
wget https://example.com/match1.mp4
wget https://example.com/match2.mp4
# etc.

# 2. Ingest videos
for video in match*.mp4; do
  python -m eval.ingest "$video" \
    --license licensed \
    --source-url "https://example.com/$(basename $video)" \
    --camera "sideline"
done

# 3. Create clips (choose 5 good clips with different conditions)
python -m eval.clipping video_001 --start 5 --end 15 --court-visible --players 2
python -m eval.clipping video_002 --start 10 --end 25 --court-visible --players 2
python -m eval.clipping video_003 --start 15 --end 30 --court-visible --players 2
python -m eval.clipping video_004 --start 8 --end 18 --court-visible --players 2
python -m eval.clipping video_005 --start 20 --end 35 --court-visible --players 2

# 4. Annotate clips (web UI at http://localhost:5000)
python -m eval.annotation_server --port 5000

# 5. Evaluate each clip
for clip_id in clip_*; do
  python -m eval.evaluate_real "$clip_id" --sampling-fps 2.0
done

# 6. Generate report
python -m eval.report_generator

# 7. Read report
cat cv-service/eval/datasets/M5.5_EVALUATION_REPORT.md
```

## Known Limitations

- Annotation UI is minimal (accuracy matters more than beauty)
- Per-frame calibration not yet supported (uses single court fit for entire clip)
- Frame-by-frame tracking association not fully implemented (simplified greedy matching)
- No automatic multi-frame ground truth (annotate keyframes, extrapolate for simplicity)

## Architecture Note

M5.5 preserves the M5 architecture:

```
PERCEPTION (M5 — validated by M5.5)
    ↓
EVIDENCE (ground-truth annotations + M5 results)
    ↓
INTERPRETATION (future: rally reconstruction, tactics)
    ↓
COACHING (future: AI coach output)
```

M5.5 produces perception/evaluation evidence only. It does not create coaching conclusions.

---

See `docs/CV_ARCHITECTURE.md` for M5 design details.
See `README.md` for project setup.
