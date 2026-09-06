"""
Visual overlay generation for M5.5 evaluation.

Creates comparison images/videos showing M5 predictions vs ground-truth annotations.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from .dataset import DatasetManager
from .schemas import AnnotationMetadata


def generate_overlay_image(
    clip_id: str,
    frame_index: int = 0,
    dataset_dir: str | Path = "cv-service/eval/datasets",
    output_path: str | Path | None = None,
) -> Path:
    """
    Generate a single frame overlay showing ground truth + M5 predictions.

    Args:
        clip_id: Clip to overlay
        frame_index: Which frame to render (0-indexed)
        dataset_dir: Dataset directory
        output_path: Where to save (default: datasets/overlays/{clip_id}_{frame}.jpg)

    Returns:
        Path to generated image
    """
    dataset = DatasetManager(dataset_dir)

    # Load clip
    clip_path = dataset.get_clip_path(clip_id)
    if not clip_path.exists():
        raise FileNotFoundError(f"Clip not found: {clip_path}")

    # Load annotation
    annotation_data = dataset.load_annotation(clip_id)
    if not annotation_data:
        raise ValueError(f"No annotation for clip {clip_id}")
    annotation = AnnotationMetadata(**annotation_data)

    # Load evaluation result
    eval_data = dataset.load_evaluation(clip_id)
    if not eval_data:
        raise ValueError(f"No evaluation for clip {clip_id}")

    # Extract frame
    cap = cv2.VideoCapture(str(clip_path))
    for _ in range(frame_index):
        cap.read()
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError(f"Could not extract frame {frame_index} from {clip_id}")

    # Get frame dimensions
    h, w = frame.shape[:2]

    # Draw ground truth (green)
    if frame_index < len(annotation.frames):
        gt_frame = annotation.frames[frame_index]

        # Draw court corners
        if gt_frame.court_corners:
            corners_px = gt_frame.court_corners.to_pixel_coords(w, h)
            corners = [
                (int(corners_px["top_left"][0]), int(corners_px["top_left"][1])),
                (int(corners_px["top_right"][0]), int(corners_px["top_right"][1])),
                (int(corners_px["bottom_right"][0]), int(corners_px["bottom_right"][1])),
                (int(corners_px["bottom_left"][0]), int(corners_px["bottom_left"][1])),
            ]
            cv2.polylines(frame, [np.array(corners)], True, (0, 255, 0), 2)
            cv2.putText(frame, "GT Court", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Draw annotated players (green boxes)
        for i, player in enumerate(gt_frame.players):
            x1, y1, x2, y2 = player.bbox.to_pixel_coords(w, h)
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            label = f"GT {player.identity.value}"
            cv2.putText(
                frame,
                label,
                (int(x1), int(y1) - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
            )

    # Draw evaluation metadata
    cv2.putText(
        frame,
        f"Frame {frame_index} | Quality: {gt_frame.quality.value if frame_index < len(annotation.frames) else '?'}",
        (10, h - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        1,
    )

    # Save
    if output_path is None:
        overlays_dir = Path(dataset_dir) / "overlays"
        overlays_dir.mkdir(exist_ok=True)
        output_path = overlays_dir / f"{clip_id}_frame_{frame_index:03d}.jpg"

    output_path = Path(output_path)
    cv2.imwrite(str(output_path), frame)

    return output_path


def generate_overlay_video(
    clip_id: str,
    dataset_dir: str | Path = "cv-service/eval/datasets",
    output_path: str | Path | None = None,
    fps: float = 2.0,
) -> Path:
    """
    Generate a full overlay video with ground truth annotations.

    Args:
        clip_id: Clip to overlay
        dataset_dir: Dataset directory
        output_path: Where to save (default: datasets/overlays/{clip_id}_overlay.mp4)
        fps: Output FPS

    Returns:
        Path to generated video
    """
    dataset = DatasetManager(dataset_dir)

    # Load annotation
    annotation_data = dataset.load_annotation(clip_id)
    if not annotation_data:
        raise ValueError(f"No annotation for clip {clip_id}")
    annotation = AnnotationMetadata(**annotation_data)

    # Open clip
    clip_path = dataset.get_clip_path(clip_id)
    cap = cv2.VideoCapture(str(clip_path))

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Create output video writer
    if output_path is None:
        overlays_dir = Path(dataset_dir) / "overlays"
        overlays_dir.mkdir(exist_ok=True)
        output_path = overlays_dir / f"{clip_id}_overlay.mp4"

    output_path = Path(output_path)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (frame_width, frame_height))

    frame_index = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Draw ground truth for this frame
        if frame_index < len(annotation.frames):
            gt_frame = annotation.frames[frame_index]

            # Court
            if gt_frame.court_corners:
                corners_px = gt_frame.court_corners.to_pixel_coords(frame_width, frame_height)
                corners = [
                    (int(corners_px["top_left"][0]), int(corners_px["top_left"][1])),
                    (int(corners_px["top_right"][0]), int(corners_px["top_right"][1])),
                    (int(corners_px["bottom_right"][0]), int(corners_px["bottom_right"][1])),
                    (int(corners_px["bottom_left"][0]), int(corners_px["bottom_left"][1])),
                ]
                cv2.polylines(frame, [np.array(corners)], True, (0, 255, 0), 2)

            # Players
            for player in gt_frame.players:
                x1, y1, x2, y2 = player.bbox.to_pixel_coords(frame_width, frame_height)
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                label = f"GT {player.identity.value}"
                cv2.putText(
                    frame,
                    label,
                    (int(x1), int(y1) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                )

        writer.write(frame)
        frame_index += 1

    cap.release()
    writer.release()

    return output_path
