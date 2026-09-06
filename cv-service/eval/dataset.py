"""
Dataset management for M5.5 real-footage validation.

Handles video ingestion, clipping, annotation storage, and evaluation tracking.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .schemas import (
    ClipMetadata,
    LicenseType,
    VideoMetadata,
)


class DatasetManager:
    """Manages M5.5 evaluation datasets."""

    def __init__(self, root_dir: str | Path = "cv-service/eval/datasets"):
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.inventory_file = self.root / "inventory.json"
        self._load_inventory()

    def _load_inventory(self) -> None:
        """Load or initialize dataset inventory."""
        if self.inventory_file.exists():
            self.inventory = json.loads(self.inventory_file.read_text())
        else:
            self.inventory = {"videos": {}, "clips": {}}

    def _save_inventory(self) -> None:
        """Persist inventory to disk."""
        self.inventory_file.write_text(json.dumps(self.inventory, indent=2, default=str))

    def ingest_video(
        self,
        video_path: str | Path,
        license_type: LicenseType,
        source_url: Optional[str] = None,
        source_description: Optional[str] = None,
        camera_description: Optional[str] = None,
        players_named: Optional[list[str]] = None,
        notes: Optional[str] = None,
    ) -> str:
        """
        Ingest a video file and register it in the dataset.

        Returns:
            video_id: Unique identifier for this video
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        # Compute video metadata via ffprobe
        import subprocess

        try:
            probe_result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "stream=width,height,r_frame_rate,codec_name,duration",
                    "-of",
                    "json",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            probe_data = json.loads(probe_result.stdout)
            stream = probe_data["streams"][0]
            width = stream.get("width", 0)
            height = stream.get("height", 0)
            fps_str = stream.get("r_frame_rate", "0/1")
            fps_parts = fps_str.split("/")
            fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 0.0
            duration = float(stream.get("duration", 0))
            codec = stream.get("codec_name", "unknown")
        except Exception as e:
            raise RuntimeError(f"ffprobe failed on {video_path}: {e}")

        # Copy video to dataset storage
        video_id = f"video_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{video_path.stem}"
        storage_dir = self.root / "videos"
        storage_dir.mkdir(exist_ok=True)
        storage_path = storage_dir / f"{video_id}.mp4"
        shutil.copy(video_path, storage_path)

        # Register in inventory
        metadata = VideoMetadata(
            video_id=video_id,
            filename=video_path.name,
            license=license_type,
            source_url=source_url,
            source_description=source_description,
            camera_description=camera_description,
            players_named=players_named,
            duration_seconds=duration,
            width=width,
            height=height,
            fps=fps,
            codec=codec,
            notes=notes,
        )
        self.inventory["videos"][video_id] = json.loads(metadata.model_dump_json(default=str))
        self._save_inventory()

        return video_id

    def create_clip(
        self,
        source_video_id: str,
        start_seconds: float,
        end_seconds: float,
        camera_view: Optional[str] = None,
        court_visible: bool = True,
        players_visible: int = 2,
        notes: Optional[str] = None,
    ) -> str:
        """
        Create a clip from a source video.

        Returns:
            clip_id: Unique identifier for this clip
        """
        if source_video_id not in self.inventory["videos"]:
            raise ValueError(f"Source video not found: {source_video_id}")

        video_path = self.root / "videos" / f"{source_video_id}.mp4"
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Create clip via ffmpeg
        clip_id = (
            f"clip_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{source_video_id}_"
            f"{int(start_seconds)}-{int(end_seconds)}"
        )
        clips_dir = self.root / "clips"
        clips_dir.mkdir(exist_ok=True)
        clip_path = clips_dir / f"{clip_id}.mp4"

        import subprocess

        subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(video_path),
                "-ss",
                str(start_seconds),
                "-to",
                str(end_seconds),
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-y",
                str(clip_path),
            ],
            capture_output=True,
            timeout=120,
            check=True,
        )

        # Register in inventory
        metadata = ClipMetadata(
            clip_id=clip_id,
            source_video_id=source_video_id,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            camera_view=camera_view,
            court_visible=court_visible,
            players_visible=players_visible,
            notes=notes,
        )
        self.inventory["clips"][clip_id] = json.loads(metadata.model_dump_json(default=str))
        self._save_inventory()

        return clip_id

    def get_video_path(self, video_id: str) -> Path:
        """Get filesystem path to a video."""
        return self.root / "videos" / f"{video_id}.mp4"

    def get_clip_path(self, clip_id: str) -> Path:
        """Get filesystem path to a clip."""
        return self.root / "clips" / f"{clip_id}.mp4"

    def get_annotation_path(self, clip_id: str) -> Path:
        """Get filesystem path to annotation file for a clip."""
        annotations_dir = self.root / "annotations"
        annotations_dir.mkdir(exist_ok=True)
        return annotations_dir / f"{clip_id}.json"

    def get_evaluation_path(self, clip_id: str) -> Path:
        """Get filesystem path to evaluation result for a clip."""
        results_dir = self.root / "evaluations"
        results_dir.mkdir(exist_ok=True)
        return results_dir / f"{clip_id}.json"

    def list_videos(self) -> list[str]:
        """List all video IDs in inventory."""
        return list(self.inventory["videos"].keys())

    def list_clips(self) -> list[str]:
        """List all clip IDs in inventory."""
        return list(self.inventory["clips"].keys())

    def list_clips_for_video(self, video_id: str) -> list[str]:
        """List clip IDs for a given source video."""
        return [
            clip_id
            for clip_id, metadata in self.inventory["clips"].items()
            if metadata.get("source_video_id") == video_id
        ]

    def get_video_metadata(self, video_id: str) -> dict:
        """Get metadata for a video."""
        return self.inventory["videos"].get(video_id)

    def get_clip_metadata(self, clip_id: str) -> dict:
        """Get metadata for a clip."""
        return self.inventory["clips"].get(clip_id)

    def list_unannotated_clips(self) -> list[str]:
        """List clips that need annotation."""
        unannotated = []
        for clip_id in self.list_clips():
            ann_path = self.get_annotation_path(clip_id)
            if not ann_path.exists():
                unannotated.append(clip_id)
        return unannotated

    def list_annotated_clips(self) -> list[str]:
        """List clips with complete annotations."""
        annotated = []
        for clip_id in self.list_clips():
            ann_path = self.get_annotation_path(clip_id)
            if ann_path.exists():
                annotated.append(clip_id)
        return annotated

    def list_unevaluated_clips(self) -> list[str]:
        """List clips that have been annotated but not yet evaluated."""
        unevaluated = []
        for clip_id in self.list_annotated_clips():
            eval_path = self.get_evaluation_path(clip_id)
            if not eval_path.exists():
                unevaluated.append(clip_id)
        return unevaluated

    def save_annotation(self, clip_id: str, annotation_data: dict) -> None:
        """Save annotation data for a clip."""
        path = self.get_annotation_path(clip_id)
        path.write_text(json.dumps(annotation_data, indent=2, default=str))

    def load_annotation(self, clip_id: str) -> dict:
        """Load annotation data for a clip."""
        path = self.get_annotation_path(clip_id)
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    def save_evaluation(self, clip_id: str, evaluation_data: dict) -> None:
        """Save evaluation result for a clip."""
        path = self.get_evaluation_path(clip_id)
        path.write_text(json.dumps(evaluation_data, indent=2, default=str))

    def load_evaluation(self, clip_id: str) -> dict:
        """Load evaluation result for a clip."""
        path = self.get_evaluation_path(clip_id)
        if not path.exists():
            return {}
        return json.loads(path.read_text())
