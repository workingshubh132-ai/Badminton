"""
Separates "a person we detected" from "a person playing on this court".

Real-footage inspection (see GITHUB_DATASET_ACQUISITION_REPORT.md) showed why
this has to exist: on broadcast singles clips a raw person count reported a
median of 4.5-7 people per frame, because it was counting seated line judges
and crowd. Any inference built on a bare person count -- match format above
all -- is therefore unsound.

The rule here is that participation must be *established*, never assumed:

* A track is a PARTICIPANT only on positive court-geometry evidence.
* A track is NON_PARTICIPANT only on positive evidence of being off-court.
* Everything else is UNKNOWN, including every track when there is no
  calibration at all. Absence of court geometry is not evidence that someone
  is a spectator.

Deliberately *not* used as signals:

* Bounding-box size. A near-court spectator is larger in frame than a far-court
  player, so "biggest box is the athlete" is backwards as often as it is right.
* Person count. That is the heuristic this module exists to replace.

Participation is orthogonal to identity. This module never writes
PlayerTrack.identity -- ATHLETE/OPPONENT remains a human confirmation
(see schemas.PlayerTrack), and a confirmed identity is never overwritten here.
"""

from __future__ import annotations

from app.config import (
    COURT_LENGTH_M,
    COURT_WIDTH_M,
    NON_PARTICIPANT_MAX_INSIDE_RATIO,
    PARTICIPANT_MIN_COURT_DISPLACEMENT_M,
    PARTICIPANT_MIN_INSIDE_RATIO,
    PARTICIPANT_MIN_TIMELINE_COVERAGE,
    PLAY_AREA_MARGIN_M,
)
from app.court import project_point
from app.schemas import Detection, MatchFormatInference, ParticipantEvidence, PlayerTrack


def _footpoint_px(detection: Detection, frame_w: int, frame_h: int) -> tuple[float, float]:
    """Bottom-centre of the bbox, in pixels.

    The homography maps the court *plane*. A standing player's feet are on that
    plane, so the footpoint projects correctly; the bbox centre sits at roughly
    torso height and projects with a systematic error that grows with distance
    from the camera. Court-position reasoning therefore uses the footpoint, not
    the centre proxy that Detection.court_x/court_y carry.
    """
    return (
        (detection.bbox.x + detection.bbox.width / 2) * frame_w,
        (detection.bbox.y + detection.bbox.height) * frame_h,
    )


def _inside_play_area(court_x: float, court_y: float) -> bool:
    m = PLAY_AREA_MARGIN_M
    return -m <= court_x <= COURT_WIDTH_M + m and -m <= court_y <= COURT_LENGTH_M + m


def _court_displacement(points: list[tuple[float, float]]) -> float:
    """Diagonal of the court-space bounding box of a track's footpoints.

    Extent rather than path length, so detection jitter does not accumulate into
    apparent movement.
    """
    if len(points) < 2:
        return 0.0
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5


def _no_calibration_evidence(track: PlayerTrack, sampled_frame_count: int) -> ParticipantEvidence:
    return ParticipantEvidence(
        status="UNKNOWN",
        confidence="VERY_LOW",
        basis="NO_CALIBRATION",
        reasons=[
            "No court calibration was available, so there is no way to tell whether this "
            "person was on court. Not being able to place someone is not evidence that "
            "they are a spectator."
        ],
        detections_total=len(track.detections),
        detections_with_court_position=0,
        inside_play_area_ratio=None,
        timeline_coverage_ratio=(
            round(len(track.detections) / sampled_frame_count, 3) if sampled_frame_count else 0.0
        ),
        court_displacement_m=None,
    )


def _classify_one(
    track: PlayerTrack,
    homography: list[list[float]],
    frame_w: int,
    frame_h: int,
    sampled_frame_count: int,
) -> ParticipantEvidence:
    court_points: list[tuple[float, float]] = []
    for detection in track.detections:
        x_px, y_px = _footpoint_px(detection, frame_w, frame_h)
        projected = project_point(homography, x_px, y_px)
        if projected is not None:
            court_points.append(projected)

    total = len(track.detections)
    positioned = len(court_points)
    coverage = round(total / sampled_frame_count, 3) if sampled_frame_count else 0.0

    if positioned == 0:
        return ParticipantEvidence(
            status="UNKNOWN",
            confidence="VERY_LOW",
            basis="COURT_GEOMETRY",
            reasons=[
                "A homography was available but none of this track's footpoints could be "
                "projected onto the court plane."
            ],
            detections_total=total,
            detections_with_court_position=0,
            inside_play_area_ratio=None,
            timeline_coverage_ratio=coverage,
            court_displacement_m=None,
        )

    inside_count = sum(1 for x, y in court_points if _inside_play_area(x, y))
    inside_ratio = round(inside_count / positioned, 3)
    displacement = round(_court_displacement(court_points), 2)

    common = dict(
        basis="COURT_GEOMETRY",
        detections_total=total,
        detections_with_court_position=positioned,
        inside_play_area_ratio=inside_ratio,
        timeline_coverage_ratio=coverage,
        court_displacement_m=displacement,
    )
    positioned_note = (
        f"{inside_count}/{positioned} positioned detections fell inside the play area "
        f"(court plus {PLAY_AREA_MARGIN_M}m margin)."
    )

    if inside_ratio >= PARTICIPANT_MIN_INSIDE_RATIO:
        if coverage < PARTICIPANT_MIN_TIMELINE_COVERAGE:
            return ParticipantEvidence(
                status="UNKNOWN",
                confidence="LOW",
                reasons=[
                    positioned_note,
                    f"Present for only {coverage:.0%} of sampled frames, below the "
                    f"{PARTICIPANT_MIN_TIMELINE_COVERAGE:.0%} a participant is expected to "
                    "span. Consistent with someone crossing the court between rallies, so "
                    "participation is left unresolved rather than asserted.",
                ],
                **common,
            )
        if displacement < PARTICIPANT_MIN_COURT_DISPLACEMENT_M:
            return ParticipantEvidence(
                status="UNKNOWN",
                confidence="LOW",
                reasons=[
                    positioned_note,
                    f"Covered only {displacement}m of court across the track, below the "
                    f"{PARTICIPANT_MIN_COURT_DISPLACEMENT_M}m expected of someone playing. "
                    "A seated official just outside the lines looks like this, so this is "
                    "not promoted to participant.",
                ],
                **common,
            )
        confident = inside_ratio >= 0.9 and coverage >= 0.5
        return ParticipantEvidence(
            status="PARTICIPANT",
            confidence="HIGH" if confident else "MODERATE",
            reasons=[
                positioned_note,
                f"Present across {coverage:.0%} of sampled frames and covered {displacement}m "
                "of court, consistent with playing rather than watching.",
            ],
            **common,
        )

    if inside_ratio <= NON_PARTICIPANT_MAX_INSIDE_RATIO:
        return ParticipantEvidence(
            status="NON_PARTICIPANT",
            confidence="HIGH" if inside_ratio == 0.0 else "MODERATE",
            reasons=[
                positioned_note,
                "Consistently outside the play area, so this is a spectator, official or "
                "other bystander rather than a player.",
            ],
            **common,
        )

    return ParticipantEvidence(
        status="UNKNOWN",
        confidence="LOW",
        reasons=[
            positioned_note,
            f"That is between the {NON_PARTICIPANT_MAX_INSIDE_RATIO:.0%} and "
            f"{PARTICIPANT_MIN_INSIDE_RATIO:.0%} thresholds -- too far inside to dismiss, too "
            "far outside to confirm. Left unresolved rather than guessed.",
        ],
        **common,
    )


def classify_participants(
    tracks: list[PlayerTrack],
    homography: list[list[float]] | None,
    frame_w: int,
    frame_h: int,
    sampled_frame_count: int,
) -> list[PlayerTrack]:
    """Attach ParticipantEvidence to every track. Returns new tracks; inputs are
    not mutated, and PlayerTrack.identity is never touched."""
    classified = []
    for track in tracks:
        evidence = (
            _no_calibration_evidence(track, sampled_frame_count)
            if homography is None
            else _classify_one(track, homography, frame_w, frame_h, sampled_frame_count)
        )
        classified.append(track.model_copy(update={"participant": evidence}))
    return classified


def _max_concurrent(participant_tracks: list[PlayerTrack]) -> int:
    """Most participants visible in any single sampled frame.

    Track count alone over-counts: one player who is lost and re-acquired
    becomes two tracks that never coexist. Concurrency is what match format
    actually depends on.
    """
    per_timestamp: dict[float, int] = {}
    for track in participant_tracks:
        for timestamp in {d.timestamp_seconds for d in track.detections}:
            per_timestamp[timestamp] = per_timestamp.get(timestamp, 0) + 1
    return max(per_timestamp.values(), default=0)


def infer_match_format(tracks: list[PlayerTrack]) -> MatchFormatInference:
    """Match format from court participants only.

    Never counts raw detections or unresolved tracks as players, and returns
    UNKNOWN whenever the evidence does not actually settle the question.
    """
    assessed = [t for t in tracks if t.participant is not None]
    participants = [t for t in assessed if t.participant.status == "PARTICIPANT"]
    unknowns = [t for t in assessed if t.participant.status == "UNKNOWN"]
    non_participants = [t for t in assessed if t.participant.status == "NON_PARTICIPANT"]
    concurrent = _max_concurrent(participants)

    counts = dict(
        participant_track_count=len(participants),
        max_concurrent_participants=concurrent,
        unknown_track_count=len(unknowns),
        non_participant_track_count=len(non_participants),
    )

    if not assessed:
        return MatchFormatInference(
            format="UNKNOWN",
            confidence="VERY_LOW",
            reasons=["No tracks were assessed for participation."],
            **counts,
        )

    if all(t.participant.basis == "NO_CALIBRATION" for t in assessed):
        return MatchFormatInference(
            format="UNKNOWN",
            confidence="VERY_LOW",
            reasons=[
                "Court calibration failed, so participants cannot be separated from "
                "spectators and officials. Match format is not inferable from a person "
                "count alone -- that is precisely the heuristic that misread singles "
                "broadcast footage as doubles."
            ],
            **counts,
        )

    evidence = [
        f"{len(participants)} track(s) established as court participants, "
        f"{concurrent} of them visible simultaneously.",
        f"{len(non_participants)} track(s) ruled out as off-court.",
    ]

    if len(unknowns) > max(concurrent, 1):
        return MatchFormatInference(
            format="UNKNOWN",
            confidence="LOW",
            reasons=evidence
            + [
                f"{len(unknowns)} track(s) could not be resolved either way, more than the "
                "number of confirmed participants. Any of them could be a player, so the "
                "format is not settled."
            ],
            **counts,
        )

    if concurrent == 2:
        match_format = "SINGLES"
    elif concurrent == 4:
        match_format = "DOUBLES"
    else:
        return MatchFormatInference(
            format="UNKNOWN",
            confidence="LOW",
            reasons=evidence
            + [
                f"{concurrent} simultaneous participants matches neither singles (2) nor "
                "doubles (4). Likely a missed or spurious detection; not resolved to a format."
            ],
            **counts,
        )

    if unknowns:
        return MatchFormatInference(
            format=match_format,
            confidence="LOW",
            reasons=evidence
            + [
                f"{len(unknowns)} unresolved track(s) remain, so this is the best-supported "
                "format rather than a settled one."
            ],
            **counts,
        )

    return MatchFormatInference(
        format=match_format,
        confidence="HIGH" if concurrent == len(participants) else "MODERATE",
        reasons=evidence + ["All tracks resolved; no unexplained people present."],
        **counts,
    )
