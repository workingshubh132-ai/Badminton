"""
Classical, explainable IoU-based greedy tracker. No learned model, no
license question. Turns a sequence of per-frame person detections into
trajectories (PlayerTrack), explicitly marking gaps rather than silently
bridging unrelated detections into one track — see spec M5 section 11.

Identity (ATHLETE/OPPONENT/UNKNOWN) is deliberately NOT assigned here — see
schemas.PlayerTrack. Every track starts UNKNOWN; the product decides identity
via user confirmation (spec section 9's explicit MVP recommendation).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.detection import RawDetection, score_to_confidence
from app.schemas import BBox, Detection, PlayerTrack, TrackingGap

IOU_MATCH_THRESHOLD = 0.25
# How many *sampling intervals* a track may go unmatched before it's closed
# rather than bridged with a gap. Beyond this, a reappearing detection
# starts a new track — bridging further than this risks silently stitching
# together two different people (spec's explicit "never silently connect
# unrelated detections" rule).
MAX_GAP_SAMPLES = 3


def _iou(a: RawDetection, b: RawDetection) -> float:
    ax2, ay2 = a.x_px + a.width_px, a.y_px + a.height_px
    bx2, by2 = b.x_px + b.width_px, b.y_px + b.height_px
    inter_x1, inter_y1 = max(a.x_px, b.x_px), max(a.y_px, b.y_px)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    inter_w, inter_h = max(0.0, inter_x2 - inter_x1), max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0
    union = a.width_px * a.height_px + b.width_px * b.height_px - inter_area
    return inter_area / union if union > 0 else 0.0


@dataclass
class _ActiveTrack:
    track_id: str
    last_detection: RawDetection
    last_sample_index: int
    detections: list[tuple[float, RawDetection]] = field(default_factory=list)
    gaps: list[TrackingGap] = field(default_factory=list)
    gap_start_ts: float | None = None


def track_players(
    frame_detections: list[tuple[float, list[RawDetection]]],
    frame_width: int,
    frame_height: int,
) -> list[PlayerTrack]:
    """`frame_detections` is a time-ordered list of (timestamp, detections-in-that-frame)."""
    active: list[_ActiveTrack] = []
    finished: list[_ActiveTrack] = []

    for sample_index, (timestamp, detections) in enumerate(frame_detections):
        unmatched_detections = list(detections)
        # Greedy: for each active track, take its best-IoU unmatched detection.
        for track in sorted(active, key=lambda t: t.last_sample_index, reverse=True):
            if not unmatched_detections:
                break
            best_iou, best_det = 0.0, None
            for det in unmatched_detections:
                iou = _iou(track.last_detection, det)
                if iou > best_iou:
                    best_iou, best_det = iou, det
            if best_det is not None and best_iou >= IOU_MATCH_THRESHOLD:
                if track.gap_start_ts is not None:
                    track.gaps.append(
                        TrackingGap(
                            start_seconds=track.gap_start_ts,
                            end_seconds=timestamp,
                            reason="Not reliably detected (occlusion, motion blur, or left frame).",
                        )
                    )
                    track.gap_start_ts = None
                track.last_detection = best_det
                track.last_sample_index = sample_index
                track.detections.append((timestamp, best_det))
                unmatched_detections.remove(best_det)

        # Tracks not matched this frame: start (or continue) a gap, or close.
        for track in active:
            if track.last_sample_index != sample_index:
                if track.gap_start_ts is None:
                    track.gap_start_ts = timestamp
                if sample_index - track.last_sample_index > MAX_GAP_SAMPLES:
                    if track.gap_start_ts is not None:
                        track.gaps.append(
                            TrackingGap(
                                start_seconds=track.gap_start_ts,
                                end_seconds=track.detections[-1][0] if track.detections else timestamp,
                                reason="Track ended — not re-detected within the gap-tolerance window.",
                            )
                        )
                    finished.append(track)

        active = [t for t in active if t not in finished]

        # Unmatched detections start new tracks.
        for det in unmatched_detections:
            active.append(
                _ActiveTrack(
                    track_id=str(uuid.uuid4()),
                    last_detection=det,
                    last_sample_index=sample_index,
                    detections=[(timestamp, det)],
                )
            )

    finished.extend(active)

    tracks: list[PlayerTrack] = []
    for t in finished:
        if not t.detections:
            continue
        scores = [d.score for _, d in t.detections]
        avg_score = sum(scores) / len(scores)
        tracks.append(
            PlayerTrack(
                track_id=t.track_id,
                confidence=score_to_confidence(avg_score),
                detections=[
                    Detection(
                        timestamp_seconds=ts,
                        bbox=BBox(
                            x=det.x_px / frame_width,
                            y=det.y_px / frame_height,
                            width=det.width_px / frame_width,
                            height=det.height_px / frame_height,
                        ),
                        score=det.score,
                        confidence=score_to_confidence(det.score),
                    )
                    for ts, det in t.detections
                ],
                gaps=t.gaps,
            )
        )
    return tracks
