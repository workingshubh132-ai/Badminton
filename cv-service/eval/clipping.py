"""
Clipping utility for M5.5 dataset.

Usage:
    python -m eval.clipping video_001 --start 10 --end 20 --court-visible --players 2
"""

from __future__ import annotations

import argparse

from .dataset import DatasetManager


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create an evaluation clip from a source video."
    )
    parser.add_argument("source_video_id", help="Source video ID (e.g., 'video_20260906_000000_...')")
    parser.add_argument(
        "--start",
        type=float,
        required=True,
        help="Start time in seconds",
    )
    parser.add_argument(
        "--end",
        type=float,
        required=True,
        help="End time in seconds",
    )
    parser.add_argument(
        "--camera",
        dest="camera_view",
        help="Camera angle/view description",
    )
    parser.add_argument(
        "--court-visible",
        action="store_true",
        default=True,
        help="Is court fully visible in this clip?",
    )
    parser.add_argument(
        "--players",
        type=int,
        dest="players_visible",
        default=2,
        help="Number of players visible (0, 1, or 2)",
    )
    parser.add_argument(
        "--notes",
        help="Clip notes",
    )
    parser.add_argument(
        "--dataset-dir",
        default="cv-service/eval/datasets",
        help="Dataset root directory",
    )

    args = parser.parse_args()

    manager = DatasetManager(args.dataset_dir)

    if args.source_video_id not in manager.list_videos():
        print(f"ERROR: Source video not found: {args.source_video_id}")
        print(f"Available videos: {', '.join(manager.list_videos())}")
        return

    print(f"Creating clip from {args.source_video_id}...")
    print(f"  Start: {args.start}s")
    print(f"  End: {args.end}s")
    print(f"  Duration: {args.end - args.start}s")

    try:
        clip_id = manager.create_clip(
            source_video_id=args.source_video_id,
            start_seconds=args.start,
            end_seconds=args.end,
            camera_view=args.camera_view,
            court_visible=args.court_visible,
            players_visible=args.players_visible,
            notes=args.notes,
        )
        print(f"✓ Clip created: {clip_id}")

        metadata = manager.get_clip_metadata(clip_id)
        print(f"  - Court visible: {metadata['court_visible']}")
        print(f"  - Players visible: {metadata['players_visible']}")
    except Exception as e:
        print(f"ERROR: {e}")
        return


if __name__ == "__main__":
    main()
