"""
Video preprocessing: real metadata extraction (via ffprobe, matching the
Next.js side's own probing so both agree) and frame sampling (via OpenCV's
VideoCapture, which decodes on demand — this never loads a whole video into
memory, and callers can request every frame, every Nth frame, or a specific
timestamp; see sample_frames / get_frame_at_timestamp below).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.schemas import VideoInfo


def probe_video(path: Path) -> VideoInfo:
    """Real container/stream metadata via ffprobe. Never guesses — a field
    that ffprobe doesn't report stays None."""
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        data = json.loads(proc.stdout)
    except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError):
        return VideoInfo()

    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video_stream:
        return VideoInfo()

    fps = None
    avg_rate = video_stream.get("avg_frame_rate")
    if avg_rate and avg_rate != "0/0":
        num, _, den = avg_rate.partition("/")
        if den and float(den) != 0:
            fps = float(num) / float(den)

    duration = data.get("format", {}).get("duration")
    frame_count = video_stream.get("nb_frames")

    return VideoInfo(
        width=video_stream.get("width"),
        height=video_stream.get("height"),
        fps=fps,
        frame_count=int(frame_count) if frame_count and frame_count.isdigit() else None,
        duration_seconds=float(duration) if duration else None,
        codec=video_stream.get("codec_name"),
    )


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


@dataclass
class SampledFrame:
    timestamp_seconds: float
    frame: np.ndarray  # BGR, as OpenCV decodes it


def sample_frames(
    path: Path,
    sampling_fps: float,
    max_frames: int,
) -> Iterator[SampledFrame]:
    """
    Yields frames at approximately `sampling_fps`, up to `max_frames` total.
    A generator — never materializes the whole video in memory. Frames that
    fail to decode are silently skipped (their absence is what
    app/quality.py's decode-failure-ratio metric measures, from the gap
    between requested and yielded frame count).
    """
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return

    try:
        source_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        if source_fps <= 0:
            source_fps = 30.0  # OpenCV couldn't report it; fall back to a
            # conservative assumption only for *sampling stride* purposes —
            # this never becomes video.fps in the output (that comes only
            # from ffprobe in probe_video, or stays honestly null).

        frame_interval = max(1, round(source_fps / sampling_fps))
        frame_index = 0
        yielded = 0

        while yielded < max_frames:
            ok = cap.grab()
            if not ok:
                break
            if frame_index % frame_interval == 0:
                ok, frame = cap.retrieve()
                if ok and frame is not None:
                    timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                    timestamp = timestamp_ms / 1000.0 if timestamp_ms else frame_index / source_fps
                    yield SampledFrame(timestamp_seconds=timestamp, frame=frame)
                    yielded += 1
            frame_index += 1
    finally:
        cap.release()


def get_frame_at_timestamp(path: Path, timestamp_seconds: float) -> np.ndarray | None:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return None
    try:
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_seconds * 1000.0)
        ok, frame = cap.read()
        return frame if ok else None
    finally:
        cap.release()
