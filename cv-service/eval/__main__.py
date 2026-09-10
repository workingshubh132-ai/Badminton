"""M5.5 CLI — Run M5.5 evaluation commands."""

import sys


def main():
    """Main entry point for M5.5 CLI."""
    if len(sys.argv) < 2:
        print("""
M5.5 Real-World CV Validation — Usage:

  python -m eval COMMAND [OPTIONS]

Commands:

  ingest VIDEO_PATH
    Ingest a video for evaluation
    Options:
      --license {licensed,reference}  [required]
      --source-url URL                Source where video was obtained
      --camera DESCRIPTION            Camera type/angle
      --source-description TEXT       How/where video was obtained
      --players NAME...               Known player names (optional)
      --notes TEXT                    Annotator notes
      --dataset-dir PATH              Dataset root (default: cv-service/eval/datasets)

  clipping VIDEO_ID
    Create an evaluation clip from source video
    Options:
      --start SECONDS                 [required] Clip start time
      --end SECONDS                   [required] Clip end time
      --camera DESCRIPTION            Camera view for this clip
      --court-visible                 Flag if court is fully visible
      --players N                     Number of visible players (0-2)
      --notes TEXT                    Clip notes
      --dataset-dir PATH              Dataset root

  annotate-server
    Start web annotation interface
    Options:
      --port PORT                     Server port (default: 5000)
      --host HOST                     Server host (default: 127.0.0.1)
      --dataset-dir PATH              Dataset root

  evaluate CLIP_ID
    Evaluate an annotated clip using M5 pipeline
    Options:
      --sampling-fps FPS              Frame sampling rate (default: 2.0)
      --dataset-dir PATH              Dataset root

  report
    Generate comprehensive evaluation report
    Options:
      --dataset-dir PATH              Dataset root
      --output PATH                   Output file path

  list
    List clips and their annotation status
    Options:
      --dataset-dir PATH              Dataset root

  dataset-v1
    Acquire candidate footage, measure it, build contact sheets, classify it,
    and regenerate DATASET_V1_SELECTION_REPORT.md + MANUAL_DOWNLOAD_REQUIRED.md
    Options:
      --dataset-dir PATH              Dataset root (default: repo_root/dataset_v1)
      --skip-acquire                  Only inspect files already in incoming/

  overlay CLIP_ID
    Generate visual overlay video/images
    Options:
      --dataset-dir PATH              Dataset root
      --frame N                       Generate single frame overlay (0-indexed)

Examples:

  # Ingest a video
  python -m eval ingest ~/badminton.mp4 \\
    --license licensed \\
    --source-url "https://example.com/video" \\
    --camera "sideline"

  # Create clips
  python -m eval clipping video_20260906_120000_badminton \\
    --start 10 --end 25 --court-visible --players 2

  # Annotate clips (web UI)
  python -m eval annotate-server --port 5000

  # Evaluate a clip
  python -m eval evaluate clip_20260906_120015_video_001_10-25

  # Generate report
  python -m eval report

  # View status
  python -m eval list
""")
        return 1

    command = sys.argv[1]

    if command == "ingest":
        from .ingest import main as ingest_main
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        ingest_main()

    elif command == "clipping":
        from .clipping import main as clipping_main
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        clipping_main()

    elif command == "annotate-server":
        from .annotation_server import main as server_main
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        server_main()

    elif command == "evaluate":
        from .evaluate_real import main as evaluate_main
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        evaluate_main()

    elif command == "report":
        from .report_generator import main as report_main
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        report_main()

    elif command == "list":
        from .dataset import DatasetManager
        from pathlib import Path
        import argparse

        parser = argparse.ArgumentParser(description="List clips and status.")
        parser.add_argument("--dataset-dir", default="cv-service/eval/datasets")
        args = parser.parse_args(sys.argv[2:])

        dataset = DatasetManager(args.dataset_dir)

        print(f"\n{'=' * 70}")
        print(f"DATASET STATUS")
        print(f"{'=' * 70}")

        videos = dataset.list_videos()
        print(f"\nVideos: {len(videos)}")
        for vid in videos[:10]:
            metadata = dataset.get_video_metadata(vid)
            print(f"  {vid}: {metadata.get('duration_seconds', '?'):.1f}s @ {metadata.get('fps', '?'):.1f} FPS")

        clips = dataset.list_clips()
        print(f"\nClips: {len(clips)}")
        annotated = dataset.list_annotated_clips()
        unevaluated = dataset.list_unevaluated_clips()
        print(f"  Annotated: {len(annotated)}")
        print(f"  Evaluated: {len(clips) - len(unevaluated)}")
        print(f"  Unevaluated: {len(unevaluated)}")

        if unevaluated:
            print(f"\n  Waiting for evaluation: {', '.join(unevaluated[:5])}")
            if len(unevaluated) > 5:
                print(f"  ... and {len(unevaluated) - 5} more")

        print(f"{'=' * 70}\n")

    elif command == "dataset-v1":
        from .dataset_v1 import run as dataset_v1_run
        import argparse

        parser = argparse.ArgumentParser(description="Acquire and triage dataset v1 footage.")
        parser.add_argument("--dataset-dir", default=None)
        parser.add_argument(
            "--skip-acquire",
            action="store_true",
            help="Only inspect files already in dataset_v1/incoming/",
        )
        args = parser.parse_args(sys.argv[2:])
        dataset_v1_run(args.dataset_dir, skip_acquire=args.skip_acquire)

    elif command == "overlay":
        from .overlay import generate_overlay_image
        import argparse

        parser = argparse.ArgumentParser(description="Generate overlay image.")
        parser.add_argument("clip_id")
        parser.add_argument("--frame", type=int, default=0, help="Frame index")
        parser.add_argument("--dataset-dir", default="cv-service/eval/datasets")
        args = parser.parse_args(sys.argv[2:])

        output_path = generate_overlay_image(args.clip_id, args.frame, args.dataset_dir)
        print(f"✓ Overlay generated: {output_path}")

    else:
        print(f"Unknown command: {command}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
