"""Orchestrates the full M5 pipeline: preprocessing -> quality -> court
calibration -> player detection -> tracking -> structured AnalysisResult."""

from __future__ import annotations

import time
from pathlib import Path

from app.config import (
    COURT_CALIBRATION_MAX_FRAMES,
    ENGINE_VERSION,
    PERSON_DETECTOR_MODEL_VERSION,
    SERVICE_NAME,
)
from app.court import calibrate_court, video_point_to_court
from app.detection import PersonDetector
from app.participants import classify_participants, infer_match_format
from app.preprocessing import probe_video, sample_frames, sha256_file
from app.quality import assess_quality
from app.schemas import AnalysisResult, PlayerTrack, ProcessingMetadata
from app.tracking import track_players


def run_analysis(
    video_path: Path,
    detector: PersonDetector,
    sampling_fps: float,
    max_sampled_frames: int,
) -> AnalysisResult:
    start = time.monotonic()

    video_info = probe_video(video_path)
    requested_frame_count = (
        int(video_info.duration_seconds * sampling_fps)
        if video_info.duration_seconds
        else max_sampled_frames
    )
    requested_frame_count = min(requested_frame_count, max_sampled_frames) or max_sampled_frames

    sampled = list(sample_frames(video_path, sampling_fps, max_sampled_frames))

    quality = assess_quality(video_info, sampled, requested_frame_count)

    if quality.status == "UNUSABLE":
        return AnalysisResult(
            status="completed",
            message="Recording quality is insufficient for reliable analysis. See `quality.reasons`.",
            video=video_info,
            quality=quality,
            calibration=calibrate_court([]),  # NOT_ATTEMPTED, honestly
            tracks=[],
            warnings=["Court calibration and player detection were skipped because quality is UNUSABLE."],
            processing_metadata=_metadata(sampling_fps, len(sampled), start, video_path),
        )

    # Court calibration only needs a spread subset of sampled frames.
    calibration_frames = sampled[:: max(1, len(sampled) // COURT_CALIBRATION_MAX_FRAMES)][:COURT_CALIBRATION_MAX_FRAMES]
    calibration = calibrate_court(calibration_frames)

    frame_w = video_info.width or (sampled[0].frame.shape[1] if sampled else 1)
    frame_h = video_info.height or (sampled[0].frame.shape[0] if sampled else 1)

    frame_detections = [(sf.timestamp_seconds, detector.detect(sf.frame)) for sf in sampled]
    tracks = track_players(frame_detections, frame_w, frame_h)
    if calibration.homography is not None:
        tracks = [_enrich_with_court_coords(t, calibration.homography, frame_w, frame_h) for t in tracks]

    # Which of those people were actually playing, rather than watching.
    tracks = classify_participants(tracks, calibration.homography, frame_w, frame_h, len(sampled))
    match_format = infer_match_format(tracks)

    warnings: list[str] = []
    if not tracks:
        warnings.append("No people were detected in any sampled frame.")
    elif calibration.homography is None:
        warnings.append(
            "Court calibration did not produce a homography, so detected people could not be "
            "separated into players and bystanders. Every track's participation is UNKNOWN and "
            "match format was not inferred."
        )
    else:
        unresolved = sum(1 for t in tracks if t.participant and t.participant.status == "UNKNOWN")
        if unresolved:
            warnings.append(
                f"{unresolved} of {len(tracks)} track(s) could not be resolved as players or "
                "bystanders. They are reported as UNKNOWN rather than assumed either way."
            )

    return AnalysisResult(
        status="completed",
        video=video_info,
        quality=quality,
        calibration=calibration,
        tracks=tracks,
        match_format=match_format,
        warnings=warnings,
        processing_metadata=_metadata(sampling_fps, len(sampled), start, video_path),
    )


def _enrich_with_court_coords(
    track: PlayerTrack, homography: list[list[float]], frame_w: int, frame_h: int
) -> PlayerTrack:
    """Projects each detection's bbox *centre* (spec M5's documented proxy —
    not the feet/contact point) through the calibration homography. Only
    called when calibration produced a homography; `video_point_to_court`
    itself still returns None per-point for anything outside a reasonable
    court margin, so off-court detections correctly stay court_x/y=None
    rather than a fabricated position."""
    enriched_detections = []
    for det in track.detections:
        cx_px = (det.bbox.x + det.bbox.width / 2) * frame_w
        cy_px = (det.bbox.y + det.bbox.height / 2) * frame_h
        court_point = video_point_to_court(homography, cx_px, cy_px)
        if court_point is None:
            enriched_detections.append(det)
        else:
            enriched_detections.append(det.model_copy(update={"court_x": court_point[0], "court_y": court_point[1]}))
    return track.model_copy(update={"detections": enriched_detections})


def _metadata(sampling_fps: float, frames_sampled: int, start: float, video_path: Path) -> ProcessingMetadata:
    return ProcessingMetadata(
        engine_name=SERVICE_NAME,
        engine_version=ENGINE_VERSION,
        model_versions={"person_detector": PERSON_DETECTOR_MODEL_VERSION},
        sampling_fps=sampling_fps,
        frames_sampled=frames_sampled,
        processing_seconds=round(time.monotonic() - start, 3),
        config={},
        video_checksum_sha256=sha256_file(video_path),
    )
