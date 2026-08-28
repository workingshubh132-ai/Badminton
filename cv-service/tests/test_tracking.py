from app.detection import RawDetection
from app.tracking import track_players


def _det(x, y, w=50, h=100, score=0.8) -> RawDetection:
    return RawDetection(x_px=x, y_px=y, width_px=w, height_px=h, score=score)


class TestTrackPlayers:
    def test_continuous_motion_produces_one_track(self):
        # A person drifting slowly right, sampled every 0.5s — consecutive
        # boxes overlap heavily, so this must stay one track.
        frames = [(i * 0.5, [_det(100 + i * 5, 100)]) for i in range(10)]
        tracks = track_players(frames, frame_width=1280, frame_height=720)
        assert len(tracks) == 1
        assert len(tracks[0].detections) == 10
        assert tracks[0].gaps == []

    def test_two_simultaneous_people_produce_two_tracks(self):
        frames = [(i * 0.5, [_det(100, 100), _det(900, 100)]) for i in range(10)]
        tracks = track_players(frames, frame_width=1280, frame_height=720)
        assert len(tracks) == 2
        for t in tracks:
            assert len(t.detections) == 10

    def test_never_silently_bridges_two_unrelated_far_apart_detections(self):
        # A detection at x=100 then, immediately next sample, one at x=900 —
        # far too different in position to be the same person moving —
        # must NOT be treated as one continuous track.
        frames = [(0.0, [_det(100, 100)]), (0.5, [_det(900, 600)])]
        tracks = track_players(frames, frame_width=1280, frame_height=720)
        assert len(tracks) == 2
        assert all(len(t.detections) == 1 for t in tracks)

    def test_short_occlusion_is_recorded_as_a_gap_not_a_new_track(self):
        # Missing for 1 sample (within MAX_GAP_SAMPLES tolerance), then
        # reappears close to where it was — same track, with a gap recorded.
        frames = [
            (0.0, [_det(100, 100)]),
            (0.5, []),  # occluded
            (1.0, [_det(108, 100)]),
        ]
        tracks = track_players(frames, frame_width=1280, frame_height=720)
        assert len(tracks) == 1
        assert len(tracks[0].detections) == 2
        assert len(tracks[0].gaps) == 1
        assert tracks[0].gaps[0].start_seconds == 0.5
        assert tracks[0].gaps[0].end_seconds == 1.0

    def test_long_absence_ends_the_track_rather_than_bridging_indefinitely(self):
        frames = [(0.0, [_det(100, 100)])] + [(0.5 * i, []) for i in range(1, 8)] + [(4.5, [_det(110, 100)])]
        tracks = track_players(frames, frame_width=1280, frame_height=720)
        # The long gap should close the first track; the reappearance starts
        # a distinct track rather than being silently stitched on.
        assert len(tracks) == 2

    def test_detections_are_normalized_to_0_1_bbox_space(self):
        frames = [(0.0, [_det(128, 72, w=128, h=144)])]
        tracks = track_players(frames, frame_width=1280, frame_height=720)
        bbox = tracks[0].detections[0].bbox
        assert bbox.x == 0.1
        assert bbox.y == 0.1
        assert bbox.width == 0.1
        assert bbox.height == 0.2

    def test_empty_input_produces_no_tracks(self):
        assert track_players([], frame_width=1280, frame_height=720) == []
