"""Dataset manifest: what footage is in the evaluation set and what we know about it.

The manifest is the licence and provenance record. It answers, per source video:
where it came from, what its licence status is, who verified that, what shape the
video is, whether graphics are burned into the pixels, and whether evaluating it
counts as real-world validation.

Anything not established is reported as not established. A blank provenance field
is a finding, not a formatting problem.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .dataset import DatasetManager
from .schemas import LicenseType, ValidationKind

UNKNOWN = "—"


def _cell(value) -> str:
    if value is None or value == "":
        return UNKNOWN
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def build_manifest(dataset_dir: str | Path) -> dict:
    dataset = DatasetManager(dataset_dir)
    entries = []
    for video_id in dataset.list_videos():
        meta = dataset.get_video_metadata(video_id) or {}
        clips = dataset.list_clips_for_video(video_id)
        entries.append(
            {
                "video_id": video_id,
                "filename": meta.get("filename"),
                "provenance": meta.get("provenance"),
                "source_url": meta.get("source_url"),
                "source_description": meta.get("source_description"),
                "license_status": meta.get("license"),
                "license_terms_url": meta.get("license_terms_url"),
                "license_verified_by": meta.get("license_verified_by"),
                "validation_kind": meta.get("validation_kind"),
                "resolution": (
                    f"{meta.get('width')}x{meta.get('height')}" if meta.get("width") else None
                ),
                "fps": meta.get("fps"),
                "duration_seconds": meta.get("duration_seconds"),
                "codec": meta.get("codec"),
                "camera_description": meta.get("camera_description"),
                "has_burned_in_overlays": meta.get("has_burned_in_overlays"),
                "match_format": meta.get("match_format"),
                "clip_count": len(clips),
                "annotated_clip_count": sum(
                    1 for c in clips if dataset.get_annotation_path(c).exists()
                ),
                "evaluated_clip_count": sum(
                    1 for c in clips if dataset.get_evaluation_path(c).exists()
                ),
            }
        )

    real = [e for e in entries if e["validation_kind"] == ValidationKind.REAL_WORLD.value]
    needs_review = [
        e for e in entries if e["license_status"] == LicenseType.LICENSE_REVIEW_REQUIRED.value
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "video_count": len(entries),
        "real_world_video_count": len(real),
        "synthetic_video_count": len(entries) - len(real),
        "license_review_required_count": len(needs_review),
        "real_world_seconds_available": round(
            sum(e["duration_seconds"] or 0 for e in real), 1
        ),
        "videos": entries,
    }


def render_markdown(manifest: dict) -> str:
    lines = [
        "# Dataset Manifest",
        "",
        f"_Generated {manifest['generated_at']}_",
        "",
        f"- Source videos: **{manifest['video_count']}**",
        f"- Real-world: **{manifest['real_world_video_count']}** "
        f"({manifest['real_world_seconds_available']}s total)",
        f"- Synthetic fixtures: **{manifest['synthetic_video_count']}**",
        f"- Awaiting licence review: **{manifest['license_review_required_count']}**",
        "",
    ]

    if manifest["real_world_video_count"] == 0:
        lines += [
            "> **No real-world footage is present.** Every source below is a synthetic "
            "fixture, which can verify that the harness runs but can never validate M5's "
            "accuracy on real badminton.",
            "",
        ]

    lines += [
        "## Sources",
        "",
        "| Video | Provenance | Licence | Verified by | Validates | Resolution | FPS | "
        "Duration | Codec | Camera | Overlays | Format | Clips (annotated/evaluated) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for e in manifest["videos"]:
        lines.append(
            f"| `{e['video_id']}` "
            f"| {_cell(e['provenance'] or e['source_description'] or e['source_url'])} "
            f"| `{_cell(e['license_status'])}` "
            f"| {_cell(e['license_verified_by'])} "
            f"| {_cell(e['validation_kind'])} "
            f"| {_cell(e['resolution'])} "
            f"| {_cell(e['fps'])} "
            f"| {_cell(e['duration_seconds'])}s "
            f"| {_cell(e['codec'])} "
            f"| {_cell(e['camera_description'])} "
            f"| {_cell(e['has_burned_in_overlays'])} "
            f"| {_cell(e['match_format'])} "
            f"| {e['clip_count']} ({e['annotated_clip_count']}/{e['evaluated_clip_count']}) |"
        )

    if manifest["license_review_required_count"]:
        lines += [
            "",
            "## Licence review outstanding",
            "",
            f"{manifest['license_review_required_count']} source(s) are "
            "`LICENSE_REVIEW_REQUIRED`. That is the default for anything whose terms nobody "
            "has read, and it is not a claim that the footage is unusable — only that the "
            "question is open. Read the terms, then re-ingest with `--license` and "
            "`--license-verified-by`. Free to download is not the same as cleared for use.",
        ]

    lines += [
        "",
        "## Fields that are blank",
        "",
        f"`{UNKNOWN}` means the fact was never recorded, not that it is absent. Provenance and "
        "overlay status in particular must be filled in before footage is trusted: burned-in "
        "graphics (pose skeletons, drawn court lines, scoreboards) corrupt court evaluation, "
        "and unrecorded provenance cannot be licence-reviewed.",
        "",
    ]
    return "\n".join(lines)


def write_manifest(dataset_dir: str | Path, output_dir: str | Path | None = None) -> tuple[Path, Path]:
    manifest = build_manifest(dataset_dir)
    out = Path(output_dir) if output_dir else Path(dataset_dir)
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / "DATASET_MANIFEST.md"
    json_path = out / "DATASET_MANIFEST.json"
    md_path.write_text(render_markdown(manifest))
    json_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return md_path, json_path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate the dataset manifest.")
    parser.add_argument("--dataset-dir", default="cv-service/eval/datasets")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    md_path, json_path = write_manifest(args.dataset_dir, args.output_dir)
    print(f"✓ Manifest written: {md_path}")
    print(f"✓ Manifest written: {json_path}")
