"""Adversarial tests for participant classification (M5.5.1).

These encode the failure that motivated the module: on real broadcast singles
footage, a raw person count reported 4.5-7 people per frame because it was
counting line judges and crowd, and every clip was mislabelled doubles.

Scenes are built by inverse-projecting known court coordinates through a real
homography, so "this person is standing 2.5m outside the sideline" is exact
rather than approximate.
"""

import cv2
import numpy as np
import pytest

from app.config import COURT_LENGTH_M, COURT_WIDTH_M
from app.participants import classify_participants, infer_match_format
from app.schemas import BBox, Detection, PlayerTrack

FRAME_W, FRAME_H = 1280, 720
# A plausible broadcast-style trapezoid: near edge wide, far edge narrow.
_COURT_CORNERS_PX = np.array(
    [[440.0, 150.0], [840.0, 150.0], [1140.0, 650.0], [140.0, 650.0]], dtype=np.float32
)
_COURT_CORNERS_M = np.array(
    [[0.0, 0.0], [COURT_WIDTH_M, 0.0], [COURT_WIDTH_M, COURT_LENGTH_M], [0.0, COURT_LENGTH_M]],
    dtype=np.float32,
)


@pytest.fixture(scope="module")
def homography():
    h, _ = cv2.findHomography(_COURT_CORNERS_PX, _COURT_CORNERS_M)
    return h.tolist()


@pytest.fixture(scope="module")
def to_pixels(homography):
    inverse = np.linalg.inv(np.array(homography, dtype=np.float64))

    def convert(court_x: float, court_y: float) -> tuple[float, float]:
        mapped = inverse @ np.array([court_x, court_y, 1.0])
        return float(mapped[0] / mapped[2]), float(mapped[1] / mapped[2])

    return convert


def _track(to_pixels, track_id, court_positions, *, box_h_px=120, box_w_px=50, start=0.0, step=0.5):
    """A track whose bbox footpoints sit exactly on the given court positions."""
    detections = []
    for index, (court_x, court_y) in enumerate(court_positions):
        foot_x, foot_y = to_pixels(court_x, court_y)
        detections.append(
            Detection(
                timestamp_seconds=start + index * step,
                bbox=BBox(
                    x=(foot_x - box_w_px / 2) / FRAME_W,
                    y=(foot_y - box_h_px) / FRAME_H,
                    width=box_w_px / FRAME_W,
                    height=box_h_px / FRAME_H,
                ),
                score=0.8,
                confidence="HIGH",
            )
        )
    return PlayerTrack(track_id=track_id, confidence="HIGH", detections=detections)


def _rally(steps=10):
    """A player working the court — moves several metres, present throughout."""
    return [(1.2 + 0.35 * i, 2.0 + 0.8 * i) for i in range(steps)]


def _far_rally(steps=10):
    return [(4.8 - 0.3 * i, 11.0 - 0.7 * i) for i in range(steps)]


def _stationary(court_x, court_y, steps=10):
    """Someone who does not move: a seated official or spectator."""
    return [(court_x, court_y)] * steps


def _status(tracks, track_id):
    return next(t for t in tracks if t.track_id == track_id).participant.status


class TestSpectatorsAreNotPlayers:
    def test_two_players_and_five_spectators(self, homography, to_pixels):
        # Spectators sit well behind the baseline, in the stands.
        tracks = [
            _track(to_pixels, "player_near", _rally()),
            _track(to_pixels, "player_far", _far_rally()),
            *[
                _track(to_pixels, f"spectator_{i}", _stationary(-4.0 + i * 2.0, -5.0))
                for i in range(5)
            ],
        ]
        classified = classify_participants(tracks, homography, FRAME_W, FRAME_H, 10)

        assert _status(classified, "player_near") == "PARTICIPANT"
        assert _status(classified, "player_far") == "PARTICIPANT"
        for i in range(5):
            assert _status(classified, f"spectator_{i}") == "NON_PARTICIPANT"

        inference = infer_match_format(classified)
        assert inference.format == "SINGLES"
        assert inference.max_concurrent_participants == 2
        assert inference.non_participant_track_count == 5

    def test_two_players_and_line_judges_just_outside_the_lines(self, homography, to_pixels):
        # The hard case: officials seated close enough to the sideline that a
        # position-only rule could sweep them in. They must never become players.
        tracks = [
            _track(to_pixels, "player_near", _rally()),
            _track(to_pixels, "player_far", _far_rally()),
            _track(to_pixels, "judge_left", _stationary(-1.2, 4.0)),
            _track(to_pixels, "judge_right", _stationary(COURT_WIDTH_M + 1.2, 9.0)),
            _track(to_pixels, "judge_baseline", _stationary(3.0, COURT_LENGTH_M + 1.2)),
        ]
        classified = classify_participants(tracks, homography, FRAME_W, FRAME_H, 10)

        assert _status(classified, "player_near") == "PARTICIPANT"
        assert _status(classified, "player_far") == "PARTICIPANT"
        for judge in ("judge_left", "judge_right", "judge_baseline"):
            assert _status(classified, judge) != "PARTICIPANT", f"{judge} was promoted to player"

        # Judges 1.2m out sit INSIDE the 1.5m play-area margin, so position alone
        # does not exclude them -- only the stationarity rule does, leaving them
        # UNKNOWN. Three unresolved tracks against two confirmed players is then
        # enough to withhold the format entirely. That is the conservative
        # direction on purpose: the alternative is claiming a format while three
        # people on screen are unaccounted for.
        inference = infer_match_format(classified)
        assert inference.participant_track_count == 2
        assert inference.unknown_track_count == 3
        assert inference.format == "UNKNOWN"
        assert inference.format != "DOUBLES"

    def test_singles_with_many_visible_people_is_not_called_doubles(self, homography, to_pixels):
        # The exact regression: two players plus a crowd. A person-count
        # heuristic reported doubles here.
        tracks = [
            _track(to_pixels, "player_near", _rally()),
            _track(to_pixels, "player_far", _far_rally()),
            *[
                _track(to_pixels, f"crowd_{i}", _stationary(-6.0 + i * 1.5, -7.0))
                for i in range(12)
            ],
        ]
        classified = classify_participants(tracks, homography, FRAME_W, FRAME_H, 10)
        inference = infer_match_format(classified)

        assert inference.format == "SINGLES"
        assert inference.format != "DOUBLES"
        assert inference.participant_track_count == 2
        assert inference.non_participant_track_count == 12


class TestTransientAndPartialTracks:
    def test_person_briefly_entering_frame_is_not_a_participant(self, homography, to_pixels):
        # Someone crossing the court for 2 of 20 sampled frames.
        tracks = [
            _track(to_pixels, "player_near", _rally()),
            _track(to_pixels, "player_far", _far_rally()),
            _track(to_pixels, "walker", [(2.0, 6.0), (2.6, 6.4)]),
        ]
        classified = classify_participants(tracks, homography, FRAME_W, FRAME_H, 20)

        assert _status(classified, "walker") == "UNKNOWN"
        walker = next(t for t in classified if t.track_id == "walker")
        assert walker.participant.timeline_coverage_ratio == pytest.approx(0.1)
        assert any("sampled frames" in r for r in walker.participant.reasons)

    def test_partial_player_detection_stays_unknown_not_rejected(self, homography, to_pixels):
        # A real player the detector only caught a few times. The safe answer is
        # UNKNOWN -- we must not assert they were a bystander.
        tracks = [_track(to_pixels, "flickering_player", _rally(steps=3))]
        classified = classify_participants(tracks, homography, FRAME_W, FRAME_H, 20)

        assert _status(classified, "flickering_player") == "UNKNOWN"
        assert _status(classified, "flickering_player") != "NON_PARTICIPANT"

    def test_unresolved_tracks_outnumbering_participants_block_a_format_claim(
        self, homography, to_pixels
    ):
        tracks = [
            _track(to_pixels, "player_near", _rally()),
            _track(to_pixels, "player_far", _far_rally()),
            *[
                _track(to_pixels, f"ambiguous_{i}", _stationary(2.0 + i, 5.0), start=0.0)
                for i in range(3)
            ],
        ]
        classified = classify_participants(tracks, homography, FRAME_W, FRAME_H, 10)
        inference = infer_match_format(classified)

        assert inference.unknown_track_count == 3
        assert inference.format == "UNKNOWN"


class TestDoubles:
    def test_four_participants_are_recognised_as_doubles(self, homography, to_pixels):
        tracks = [
            _track(to_pixels, "near_left", [(1.0 + 0.3 * i, 3.0 + 0.5 * i) for i in range(10)]),
            _track(to_pixels, "near_right", [(4.5 - 0.25 * i, 3.5 + 0.6 * i) for i in range(10)]),
            _track(to_pixels, "far_left", [(1.5 + 0.3 * i, 11.0 - 0.5 * i) for i in range(10)]),
            _track(to_pixels, "far_right", [(4.8 - 0.3 * i, 10.5 - 0.6 * i) for i in range(10)]),
        ]
        classified = classify_participants(tracks, homography, FRAME_W, FRAME_H, 10)
        inference = infer_match_format(classified)

        assert all(t.participant.status == "PARTICIPANT" for t in classified)
        assert inference.format == "DOUBLES"
        assert inference.max_concurrent_participants == 4

    def test_doubles_with_spectators_still_reads_as_doubles(self, homography, to_pixels):
        tracks = [
            _track(to_pixels, "near_left", [(1.0 + 0.3 * i, 3.0 + 0.5 * i) for i in range(10)]),
            _track(to_pixels, "near_right", [(4.5 - 0.25 * i, 3.5 + 0.6 * i) for i in range(10)]),
            _track(to_pixels, "far_left", [(1.5 + 0.3 * i, 11.0 - 0.5 * i) for i in range(10)]),
            _track(to_pixels, "far_right", [(4.8 - 0.3 * i, 10.5 - 0.6 * i) for i in range(10)]),
            *[_track(to_pixels, f"crowd_{i}", _stationary(-5.0 + i, -6.0)) for i in range(6)],
        ]
        classified = classify_participants(tracks, homography, FRAME_W, FRAME_H, 10)
        assert infer_match_format(classified).format == "DOUBLES"


class TestNoCalibration:
    def test_without_a_homography_everything_is_unknown(self, to_pixels):
        tracks = [
            _track(to_pixels, "player_near", _rally()),
            _track(to_pixels, "spectator", _stationary(-4.0, -5.0)),
        ]
        classified = classify_participants(tracks, None, FRAME_W, FRAME_H, 10)

        assert all(t.participant.status == "UNKNOWN" for t in classified)
        assert all(t.participant.basis == "NO_CALIBRATION" for t in classified)
        # Crucially: not being placeable is not evidence of being a spectator.
        assert all(t.participant.status != "NON_PARTICIPANT" for t in classified)

    def test_format_is_unknown_without_calibration_even_with_exactly_two_people(self, to_pixels):
        tracks = [
            _track(to_pixels, "player_near", _rally()),
            _track(to_pixels, "player_far", _far_rally()),
        ]
        classified = classify_participants(tracks, None, FRAME_W, FRAME_H, 10)
        inference = infer_match_format(classified)

        # Two people on screen is exactly the count that tempted the old
        # heuristic into saying "singles". Without court geometry it must not.
        assert inference.format == "UNKNOWN"
        assert inference.confidence == "VERY_LOW"


class TestNoSizeOrCountShortcuts:
    def test_largest_bbox_is_not_assumed_to_be_a_player(self, homography, to_pixels):
        # A spectator close to camera renders much larger than a far-court
        # player. Size must not override position.
        tracks = [
            _track(to_pixels, "big_spectator", _stationary(-4.0, -5.0), box_h_px=400, box_w_px=170),
            _track(to_pixels, "small_far_player", _far_rally(), box_h_px=55, box_w_px=22),
        ]
        classified = classify_participants(tracks, homography, FRAME_W, FRAME_H, 10)

        assert _status(classified, "big_spectator") == "NON_PARTICIPANT"
        assert _status(classified, "small_far_player") == "PARTICIPANT"

    def test_many_people_alone_never_produces_doubles(self, homography, to_pixels):
        # Eight people, none of them established on court.
        tracks = [
            _track(to_pixels, f"bystander_{i}", _stationary(-5.0 + i * 1.4, -6.0)) for i in range(8)
        ]
        classified = classify_participants(tracks, homography, FRAME_W, FRAME_H, 10)
        inference = infer_match_format(classified)

        assert inference.format == "UNKNOWN"
        assert inference.participant_track_count == 0


class TestFootpointGeometry:
    def test_footpoint_is_bbox_bottom_centre(self):
        from app.participants import _footpoint_px

        detection = Detection(
            timestamp_seconds=0.0,
            bbox=BBox(x=0.25, y=0.10, width=0.10, height=0.40),
            score=0.9,
            confidence="HIGH",
        )
        x, y = _footpoint_px(detection, 1000, 1000)
        assert (x, y) == pytest.approx((300.0, 500.0))

    def test_bbox_height_jitter_does_not_fake_movement_for_a_stationary_person(
        self, homography, to_pixels
    ):
        # A seated official whose detected box grows and shrinks frame to frame,
        # which detectors do constantly. Their feet never move.
        #
        # This is the case that makes the footpoint choice load-bearing: measured
        # through the bbox *centre*, this same scene yields ~1.65m of spurious
        # court displacement -- past the 1.0m movement threshold -- and the
        # official gets promoted to PARTICIPANT. Through the footpoint it is 0m.
        foot_x, foot_y = to_pixels(3.0, 13.0)
        heights = [110, 150, 200, 260, 320, 150, 110, 300, 240, 180]
        detections = [
            Detection(
                timestamp_seconds=index * 0.5,
                bbox=BBox(
                    x=(foot_x - 25) / FRAME_W,
                    y=(foot_y - height) / FRAME_H,
                    width=50 / FRAME_W,
                    height=height / FRAME_H,
                ),
                score=0.8,
                confidence="HIGH",
            )
            for index, height in enumerate(heights)
        ]
        track = PlayerTrack(track_id="jittery_official", confidence="HIGH", detections=detections)

        classified = classify_participants([track], homography, FRAME_W, FRAME_H, 10)
        evidence = classified[0].participant

        assert evidence.court_displacement_m == pytest.approx(0.0, abs=0.01)
        assert evidence.status == "UNKNOWN"
        assert evidence.status != "PARTICIPANT"


class TestEvidenceAndIdentity:
    def test_every_verdict_carries_reasons_and_measurements(self, homography, to_pixels):
        tracks = [
            _track(to_pixels, "player_near", _rally()),
            _track(to_pixels, "spectator", _stationary(-4.0, -5.0)),
        ]
        classified = classify_participants(tracks, homography, FRAME_W, FRAME_H, 10)

        for track in classified:
            evidence = track.participant
            assert evidence.reasons, f"{track.track_id} has a verdict with no stated reason"
            assert evidence.basis == "COURT_GEOMETRY"
            assert evidence.detections_total == 10
            assert evidence.inside_play_area_ratio is not None
            assert evidence.court_displacement_m is not None
            assert evidence.confidence in ("VERY_LOW", "LOW", "MODERATE", "HIGH", "VERY_HIGH")

    def test_participation_never_writes_identity(self, homography, to_pixels):
        tracks = [_track(to_pixels, "player_near", _rally())]
        classified = classify_participants(tracks, homography, FRAME_W, FRAME_H, 10)

        assert classified[0].participant.status == "PARTICIPANT"
        # Being a court participant does not make someone the athlete.
        assert classified[0].identity == "UNKNOWN"
        assert classified[0].identity_source == "HEURISTIC"

    def test_human_confirmed_identity_is_preserved(self, homography, to_pixels):
        track = _track(to_pixels, "player_near", _rally()).model_copy(
            update={"identity": "ATHLETE", "identity_source": "USER_CONFIRMED"}
        )
        classified = classify_participants([track], homography, FRAME_W, FRAME_H, 10)

        assert classified[0].identity == "ATHLETE"
        assert classified[0].identity_source == "USER_CONFIRMED"

    def test_inputs_are_not_mutated(self, homography, to_pixels):
        tracks = [_track(to_pixels, "player_near", _rally())]
        classify_participants(tracks, homography, FRAME_W, FRAME_H, 10)
        assert tracks[0].participant is None
