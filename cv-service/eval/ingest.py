"""
Ingestion CLI for M5.5 dataset.

Usage:
    python -m eval.ingest video.mp4 --license licensed --source-url "https://..." --camera "overhead"
    python -m eval.ingest video.mp4 --license reference
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .dataset import DatasetManager
from .schemas import LicenseType, MatchFormatLabel, ValidationKind


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest a badminton video for M5.5 evaluation."
    )
    parser.add_argument("video_path", help="Path to video file")
    parser.add_argument(
        "--license",
        choices=["licensed", "reference", "review-required"],
        default="review-required",
        help=(
            "Licence handling status. Defaults to review-required: a licence nobody has "
            "read is not a permissive one. Use licensed/reference only after a human has "
            "actually read the terms."
        ),
    )
    parser.add_argument(
        "--license-terms-url",
        help="Where the applicable licence text lives",
    )
    parser.add_argument(
        "--license-verified-by",
        help="Who read the licence terms. Omit if nobody has.",
    )
    parser.add_argument(
        "--real-footage",
        action="store_true",
        help=(
            "Assert this is genuine real-world footage, so evaluating it counts as "
            "real-world validation. Without this flag the video is treated as SYNTHETIC "
            "and its results are kept out of the real-world section of the report."
        ),
    )
    parser.add_argument(
        "--provenance",
        help="Where this footage came from and how it was obtained",
    )
    parser.add_argument(
        "--has-overlays",
        dest="has_overlays",
        action="store_true",
        default=None,
        help="Graphics are burned into the pixels (pose skeletons, drawn lines, scoreboards)",
    )
    parser.add_argument(
        "--no-overlays",
        dest="has_overlays",
        action="store_false",
        help="Confirmed clean of burned-in graphics",
    )
    parser.add_argument(
        "--match-format",
        choices=["singles", "doubles", "unknown"],
        default="unknown",
        help="Known match format, if known",
    )
    parser.add_argument(
        "--source-url",
        help="URL where video was sourced from",
    )
    parser.add_argument(
        "--source-description",
        help="Description of how/where video was obtained",
    )
    parser.add_argument(
        "--camera",
        dest="camera_description",
        help="Camera type or view angle (e.g., 'overhead', 'sideline', 'phone')",
    )
    parser.add_argument(
        "--players",
        nargs="+",
        dest="players_named",
        help="Known player names (optional)",
    )
    parser.add_argument(
        "--notes",
        help="Annotator notes",
    )
    parser.add_argument(
        "--dataset-dir",
        default="cv-service/eval/datasets",
        help="Dataset root directory",
    )

    args = parser.parse_args()

    video_path = Path(args.video_path)
    if not video_path.exists():
        print(f"ERROR: Video not found: {video_path}")
        return

    manager = DatasetManager(args.dataset_dir)
    license_type = {
        "licensed": LicenseType.LICENSED,
        "reference": LicenseType.REFERENCE,
        "review-required": LicenseType.LICENSE_REVIEW_REQUIRED,
    }[args.license]

    print(f"Ingesting {video_path.name}...")
    try:
        video_id = manager.ingest_video(
            video_path=video_path,
            license_type=license_type,
            source_url=args.source_url,
            source_description=args.source_description,
            camera_description=args.camera_description,
            players_named=args.players_named,
            notes=args.notes,
            validation_kind=(
                ValidationKind.REAL_WORLD if args.real_footage else ValidationKind.SYNTHETIC
            ),
            license_terms_url=args.license_terms_url,
            license_verified_by=args.license_verified_by,
            provenance=args.provenance,
            has_burned_in_overlays=args.has_overlays,
            match_format=MatchFormatLabel(args.match_format),
        )
        print(f"✓ Video ingested: {video_id}")

        # Display metadata
        metadata = manager.get_video_metadata(video_id)
        print(f"  - Resolution: {metadata['width']}x{metadata['height']}")
        print(f"  - FPS: {metadata['fps']}")
        print(f"  - Duration: {metadata['duration_seconds']:.1f}s")
        print(f"  - License: {metadata['license']}")
        print(f"  - Validates: {metadata['validation_kind']}")
        print(f"  - Match format: {metadata['match_format']}")
        print(f"  - Burned-in overlays: {metadata['has_burned_in_overlays']}")
        if args.source_url:
            print(f"  - Source: {args.source_url}")
        if metadata["license"] == "license_review_required":
            print(
                "\n  NOTE: licence status is LICENSE_REVIEW_REQUIRED. Read the terms and "
                "re-ingest with --license and --license-verified-by before this footage is "
                "used for anything beyond local evaluation."
            )
        if not args.real_footage:
            print(
                "\n  NOTE: treated as SYNTHETIC. Results will be reported as machinery "
                "verification, not real-world validation. Pass --real-footage to change that."
            )
    except Exception as e:
        print(f"ERROR: {e}")
        return


if __name__ == "__main__":
    main()
