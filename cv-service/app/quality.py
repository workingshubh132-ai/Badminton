"""
First-stage quality assessment (spec M5 section 5). Every signal here is
something actually measured against the sampled frames — no invented score.
"""

from __future__ import annotations

import numpy as np

from app.config import (
    MAX_BLANK_FRAME_RATIO,
    MAX_DECODE_FAILURE_RATIO,
    MIN_ACCEPTABLE_FPS,
    MIN_ACCEPTABLE_WIDTH,
    MIN_GOOD_FPS,
    MIN_GOOD_WIDTH,
)
from app.preprocessing import SampledFrame
from app.schemas import QualityAssessment, VideoInfo

# A frame is "blank" for our purposes if its luminance standard deviation is
# very low — a near-solid color (all-black, all-white, or a static title
# card), not a real court/player scene. This threshold is provisional (see
# docs/CV_ARCHITECTURE.md "Acceptance thresholds") — it is deliberately
# permissive so real, low-texture court surfaces aren't misflagged.
BLANK_FRAME_STD_THRESHOLD = 6.0


def is_blank_frame(frame: np.ndarray) -> bool:
    gray = frame.mean(axis=2) if frame.ndim == 3 else frame
    return bool(gray.std() < BLANK_FRAME_STD_THRESHOLD)


def assess_quality(
    video: VideoInfo,
    sampled: list[SampledFrame],
    requested_frame_count: int,
) -> QualityAssessment:
    reasons: list[str] = []
    metrics: dict = {}

    if video.width and video.height:
        metrics["resolution"] = f"{video.width}x{video.height}"
    metrics["fps"] = video.fps
    metrics["duration_seconds"] = video.duration_seconds

    decode_failure_ratio = (
        1.0 - (len(sampled) / requested_frame_count) if requested_frame_count > 0 else 1.0
    )
    decode_failure_ratio = max(0.0, decode_failure_ratio)
    metrics["decode_failure_ratio"] = round(decode_failure_ratio, 3)
    metrics["sampled_frame_count"] = len(sampled)

    blank_count = sum(1 for s in sampled if is_blank_frame(s.frame))
    blank_ratio = blank_count / len(sampled) if sampled else 1.0
    metrics["blank_frame_ratio"] = round(blank_ratio, 3)

    # --- Hard failures -------------------------------------------------
    if not video.duration_seconds or video.duration_seconds <= 0:
        return QualityAssessment(
            status="UNUSABLE",
            reasons=["Video duration could not be determined or is zero."],
            metrics=metrics,
        )
    if not sampled:
        return QualityAssessment(
            status="UNUSABLE",
            reasons=["No frames could be decoded from this video."],
            metrics=metrics,
        )
    if decode_failure_ratio > MAX_DECODE_FAILURE_RATIO * 3:
        return QualityAssessment(
            status="UNUSABLE",
            reasons=[
                f"{round(decode_failure_ratio * 100)}% of requested frames failed to decode — "
                "the file is likely corrupt or truncated."
            ],
            metrics=metrics,
        )

    # --- Graded signals --------------------------------------------------
    score_penalties = 0

    if video.width and video.width < MIN_ACCEPTABLE_WIDTH:
        reasons.append(f"Resolution ({video.width}px wide) is below the {MIN_ACCEPTABLE_WIDTH}px floor for reliable analysis.")
        score_penalties += 3
    elif video.width and video.width < MIN_GOOD_WIDTH:
        reasons.append(f"Resolution ({video.width}px wide) is usable but below {MIN_GOOD_WIDTH}px.")
        score_penalties += 1
    elif video.width:
        reasons.append(f"{video.width}x{video.height} resolution.")

    if video.fps and video.fps < MIN_ACCEPTABLE_FPS:
        reasons.append(f"Frame rate ({video.fps:.1f} FPS) is low enough to risk missed fast movement.")
        score_penalties += 3
    elif video.fps and video.fps < MIN_GOOD_FPS:
        reasons.append(f"Frame rate ({video.fps:.1f} FPS) is usable but not ideal.")
        score_penalties += 1
    elif video.fps:
        reasons.append(f"{video.fps:.0f} FPS.")

    if blank_ratio > MAX_BLANK_FRAME_RATIO:
        reasons.append(
            f"{round(blank_ratio * 100)}% of sampled frames were blank/near-solid color — "
            "camera may have been covered, pointed away, or recording in very low light."
        )
        score_penalties += 3
    elif blank_ratio > 0:
        reasons.append(f"{round(blank_ratio * 100)}% of sampled frames were blank or near-solid color.")
        score_penalties += 1

    if decode_failure_ratio > MAX_DECODE_FAILURE_RATIO:
        reasons.append(f"{round(decode_failure_ratio * 100)}% of requested frames failed to decode.")
        score_penalties += 1

    if score_penalties == 0:
        status = "GOOD"
    elif score_penalties <= 2:
        status = "ACCEPTABLE"
    elif score_penalties <= 4:
        status = "POOR"
    else:
        status = "UNUSABLE"

    if not reasons:
        reasons.append("No quality issues detected in sampled frames.")

    return QualityAssessment(status=status, reasons=reasons, metrics=metrics)
