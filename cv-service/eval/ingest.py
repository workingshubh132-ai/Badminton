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
from .schemas import LicenseType


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest a badminton video for M5.5 evaluation."
    )
    parser.add_argument("video_path", help="Path to video file")
    parser.add_argument(
        "--license",
        choices=["licensed", "reference"],
        required=True,
        help="License type (licensed=we can use/retain, reference=elite footage for research)",
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
    license_type = LicenseType.LICENSED if args.license == "licensed" else LicenseType.REFERENCE

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
        )
        print(f"✓ Video ingested: {video_id}")

        # Display metadata
        metadata = manager.get_video_metadata(video_id)
        print(f"  - Resolution: {metadata['width']}x{metadata['height']}")
        print(f"  - FPS: {metadata['fps']}")
        print(f"  - Duration: {metadata['duration_seconds']:.1f}s")
        print(f"  - License: {metadata['license']}")
        if args.source_url:
            print(f"  - Source: {args.source_url}")
    except Exception as e:
        print(f"ERROR: {e}")
        return


if __name__ == "__main__":
    main()
