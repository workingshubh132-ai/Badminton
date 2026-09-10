# Drop downloaded footage here

Put candidate badminton video files (`.mp4`, `.mov`, `.mkv`, `.webm`) in this folder,
then run:

```bash
cd cv-service && python -m eval dataset-v1
```

Everything downstream is automatic: SHA-256, ffprobe metadata, frame measurement,
contact sheets, ACCEPT/MANUAL_REVIEW/REJECT classification, and both reports.

See [`../../MANUAL_DOWNLOAD_REQUIRED.md`](../../MANUAL_DOWNLOAD_REQUIRED.md) for which
files are still needed, where each comes from, and the filename to use.

**Video files in this folder are never committed.** They are third-party footage; only
measured facts (`../sources.json`, `../metadata/`, `../analysis/`) are tracked. Read each
source's licence before using the footage for anything beyond local evaluation.
