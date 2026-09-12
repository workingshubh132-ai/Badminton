"""End-to-end tests for the M5.5 real-world validation harness (M5.5.2).

The harness must be ready to run the moment legitimate footage arrives, so these
tests drive the actual path a real video takes -- ingest, clip, annotate,
evaluate, report, manifest -- rather than testing the pieces in isolation. They
use the synthetic fixture, and assert throughout that synthetic evidence is
never allowed to masquerade as real-world validation.
"""

import json
from types import SimpleNamespace

import pytest

from eval.dataset import DatasetManager
from eval.evaluate_real import RealFootageEvaluator
from eval.manifest import build_manifest, write_manifest
from eval.report_generator import ReportGenerator
from eval.schemas import (
    AnnotationMetadata,
    BoundingBox,
    LicenseType,
    MatchFormatLabel,
    ParticipantStatus,
    ValidationKind,
)

FIXTURE = "eval/fixtures/synthetic_court_01.mp4"


def _annotation(clip_id, people):
    """people: list of (identity, participant, (x1,y1,x2,y2))"""
    return {
        "clip_id": clip_id,
        "version": "1.0",
        "annotator": "synthetic-harness-test",
        "frames": [
            {
                "frame_index": 0,
                "timestamp_seconds": 0.0,
                "quality": "good",
                "court_corners": {
                    "top_left": [0.15, 0.15],
                    "top_right": [0.85, 0.15],
                    "bottom_right": [0.95, 0.85],
                    "bottom_left": [0.05, 0.85],
                },
                "players": [
                    {
                        "identity": identity,
                        "participant": participant,
                        "bbox": {"x1": b[0], "y1": b[1], "x2": b[2], "y2": b[3]},
                    }
                    for identity, participant, b in people
                ],
            }
        ],
    }


@pytest.fixture(scope="module")
def walked(tmp_path_factory):
    """Drive the whole harness once; every workflow test asserts on the result."""
    if True:
        root = tmp_path_factory.mktemp("harness")
        dataset = DatasetManager(root)

        video_id = dataset.ingest_video(
            video_path=FIXTURE,
            license_type=LicenseType.LICENSE_REVIEW_REQUIRED,
            source_url="synthetic://fixture",
            camera_description="synthetic",
            provenance="Rendered by eval/fixtures/generate_synthetic_fixture.py",
            has_burned_in_overlays=False,
            match_format=MatchFormatLabel.UNKNOWN,
        )
        clip_id = dataset.create_clip(video_id, start_seconds=0.0, end_seconds=5.0)
        dataset.save_annotation(
            clip_id,
            _annotation(
                clip_id,
                [
                    ("athlete", "participant", (0.45, 0.35, 0.55, 0.60)),
                    ("unknown", "non_participant", (0.02, 0.05, 0.08, 0.18)),
                ],
            ),
        )

        evaluator = RealFootageEvaluator(root)
        result = evaluator.evaluate_clip(clip_id)
        evaluator.close()

        report = ReportGenerator(root).generate_report()
        return SimpleNamespace(
            root=root, dataset=dataset, video_id=video_id, clip_id=clip_id,
            result=result, report=report,
        )


class TestFullWorkflow:
    """incoming -> ingest -> clip -> annotation -> evaluation -> report, no code changes."""

    def test_ingest_records_the_video(self, walked):
        assert walked.video_id in walked.dataset.list_videos()

    def test_clip_is_created_and_listed(self, walked):
        assert walked.clip_id in walked.dataset.list_clips()
        assert walked.dataset.get_clip_path(walked.clip_id).exists()

    def test_annotation_round_trips_with_participant_labels(self, walked):
        loaded = AnnotationMetadata(**walked.dataset.load_annotation(walked.clip_id))
        people = loaded.frames[0].players
        assert len(people) == 2
        assert {p.participant for p in people} == {
            ParticipantStatus.PARTICIPANT,
            ParticipantStatus.NON_PARTICIPANT,
        }
        assert loaded.frames[0].court_corners is not None

    def test_evaluation_runs_and_persists(self, walked):
        assert walked.dataset.get_evaluation_path(walked.clip_id).exists()
        assert walked.result.source_video_id == walked.video_id

    def test_evaluation_scores_participants(self, walked):
        assert walked.result.participant_accuracy is not None
        pa = walked.result.participant_accuracy
        assert pa.annotated_participants == 1
        assert pa.annotated_non_participants == 1
        assert pa.scored_people == 2

    def test_report_generates_and_renders(self, walked):
        markdown = ReportGenerator(walked.root).render_markdown(walked.report)
        assert "M5.5 EVALUATION REPORT" in markdown
        assert "EVIDENCE BASIS" in markdown

    def test_status_counts_are_honest(self, walked):
        assert walked.dataset.list_annotated_clips() == [walked.clip_id]
        assert walked.dataset.list_evaluated_clips() == [walked.clip_id]
        assert walked.dataset.list_unevaluated_clips() == []


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    """A dataset containing only synthetic evidence."""
    if True:
        root = tmp_path_factory.mktemp("synthonly")
        dataset = DatasetManager(root)
        video_id = dataset.ingest_video(
            video_path=FIXTURE, license_type=LicenseType.LICENSE_REVIEW_REQUIRED
        )
        clip_id = dataset.create_clip(video_id, 0.0, 5.0)
        dataset.save_annotation(
            clip_id, _annotation(clip_id, [("athlete", "participant", (0.45, 0.35, 0.55, 0.60))])
        )
        evaluator = RealFootageEvaluator(root)
        evaluator.evaluate_clip(clip_id)
        evaluator.close()
        generated = ReportGenerator(root).generate_report()
        return SimpleNamespace(
            report=generated, markdown=ReportGenerator(root).render_markdown(generated)
        )


class TestSyntheticIsNeverRealWorldValidation:
    def test_default_ingest_is_synthetic_not_real(self, report):
        assert report.report.synthetic_clips
        assert report.report.real_world_clips == []
        assert report.report.has_real_world_evidence is False

    def test_no_decision_gate_is_reachable(self, report):
        assert report.report.decision_gate == "NO_REAL_WORLD_EVIDENCE"
        assert report.report.decision_gate != "A"

    def test_every_component_is_unproven(self, report):
        for readiness in (
            report.report.court_readiness,
            report.report.detection_readiness,
            report.report.tracking_readiness,
            report.report.quality_readiness,
            report.report.participant_readiness,
        ):
            assert readiness.status.value == "unreliable"
            assert "never been evaluated against real" in readiness.reasoning

    def test_markdown_says_so_plainly(self, report):
        assert "NO real-world validation" in report.markdown
        assert "Machinery verification only" in report.markdown

    def test_real_world_flag_is_what_promotes_footage(self, tmp_path):
        # Same fixture, but explicitly asserted as real footage: it must land in
        # the real-world bucket. The flag, not the content, is the switch -- so
        # nothing is silently promoted.
        dataset = DatasetManager(tmp_path)
        video_id = dataset.ingest_video(
            video_path=FIXTURE,
            license_type=LicenseType.LICENSED,
            validation_kind=ValidationKind.REAL_WORLD,
        )
        meta = dataset.get_video_metadata(video_id)
        assert meta["validation_kind"] == "real_world"


class TestParticipantMetrics:
    """Participant scoring maths, on constructed inputs so it is exact."""

    def _m5(self, tracks):
        return SimpleNamespace(tracks=tracks)

    def _track(self, status, box, timestamp=0.0):
        x1, y1, x2, y2 = box
        detection = SimpleNamespace(
            timestamp_seconds=timestamp,
            bbox=SimpleNamespace(x=x1, y=y1, width=x2 - x1, height=y2 - y1),
        )
        participant = SimpleNamespace(status=status) if status else None
        return SimpleNamespace(detections=[detection], participant=participant)

    def _score(self, people, tracks):
        evaluator = RealFootageEvaluator.__new__(RealFootageEvaluator)
        annotation = AnnotationMetadata(**_annotation("c", people))
        return evaluator._evaluate_participants(annotation, self._m5(tracks))

    def test_correct_participant_is_a_true_positive(self):
        box = (0.4, 0.3, 0.5, 0.6)
        accuracy = self._score([("athlete", "participant", box)], [self._track("PARTICIPANT", box)])
        assert accuracy.true_positives == 1
        assert accuracy.false_positives == 0
        assert accuracy.precision == 1.0
        assert accuracy.recall == 1.0

    def test_spectator_called_a_player_is_a_false_participant(self):
        box = (0.02, 0.05, 0.10, 0.25)
        accuracy = self._score(
            [("unknown", "non_participant", box)], [self._track("PARTICIPANT", box)]
        )
        assert accuracy.false_positives == 1
        assert accuracy.false_participant_rate == 1.0
        assert accuracy.precision == 0.0

    def test_player_called_a_spectator_is_a_false_negative(self):
        box = (0.4, 0.3, 0.5, 0.6)
        accuracy = self._score(
            [("athlete", "participant", box)], [self._track("NON_PARTICIPANT", box)]
        )
        assert accuracy.false_negatives == 1
        assert accuracy.recall == 0.0

    def test_m5_unknown_counts_as_unresolved_not_as_an_error(self):
        # "I don't know" must not score as a wrong answer, or a classifier that
        # guesses would outrank one that admits uncertainty.
        box = (0.4, 0.3, 0.5, 0.6)
        accuracy = self._score([("athlete", "participant", box)], [self._track("UNKNOWN", box)])
        assert accuracy.unresolved_rate == 1.0
        assert accuracy.false_positives == 0
        assert accuracy.false_negatives == 0

    def test_annotator_unknown_is_excluded_from_scoring(self):
        box = (0.4, 0.3, 0.5, 0.6)
        accuracy = self._score(
            [("unknown", "unknown", box)], [self._track("PARTICIPANT", box)]
        )
        # The only labelled person was unresolvable by the human, so there is
        # nothing to score them against.
        assert accuracy is None

    def test_unmatched_person_is_unresolved_not_a_bystander(self):
        # M5 saw nobody there. That is "we could not tell", not "bystander".
        accuracy = self._score([("athlete", "participant", (0.4, 0.3, 0.5, 0.6))], [])
        assert accuracy.predicted_unknown == 1
        assert accuracy.false_negatives == 0
        assert accuracy.unresolved_rate == 1.0

    def test_mixed_scene_scores_each_axis_independently(self):
        player = (0.40, 0.30, 0.50, 0.60)
        spectator = (0.02, 0.05, 0.10, 0.25)
        accuracy = self._score(
            [("athlete", "participant", player), ("unknown", "non_participant", spectator)],
            [self._track("PARTICIPANT", player), self._track("NON_PARTICIPANT", spectator)],
        )
        assert accuracy.true_positives == 1
        assert accuracy.false_positives == 0
        assert accuracy.false_participant_rate == 0.0
        assert accuracy.unresolved_rate == 0.0
        assert accuracy.f1 == 1.0


class TestManifest:
    def test_manifest_records_provenance_and_licence(self, tmp_path):
        dataset = DatasetManager(tmp_path)
        dataset.ingest_video(
            video_path=FIXTURE,
            license_type=LicenseType.LICENSE_REVIEW_REQUIRED,
            provenance="Rendered synthetic fixture",
            camera_description="synthetic",
            has_burned_in_overlays=False,
            match_format=MatchFormatLabel.UNKNOWN,
        )
        manifest = build_manifest(tmp_path)
        entry = manifest["videos"][0]

        assert manifest["real_world_video_count"] == 0
        assert manifest["license_review_required_count"] == 1
        assert entry["provenance"] == "Rendered synthetic fixture"
        assert entry["resolution"] == "1280x720"
        assert entry["fps"] == pytest.approx(24.0)
        assert entry["duration_seconds"] == pytest.approx(5.0, abs=0.1)
        assert entry["codec"] == "h264"
        assert entry["has_burned_in_overlays"] is False
        assert entry["match_format"] == "unknown"

    def test_manifest_files_are_written(self, tmp_path):
        dataset = DatasetManager(tmp_path)
        dataset.ingest_video(video_path=FIXTURE, license_type=LicenseType.LICENSE_REVIEW_REQUIRED)
        md_path, json_path = write_manifest(tmp_path)

        assert md_path.exists() and json_path.exists()
        assert "No real-world footage is present" in md_path.read_text()
        assert json.loads(json_path.read_text())["video_count"] == 1

    def test_unclear_licence_stays_license_review_required(self, tmp_path):
        dataset = DatasetManager(tmp_path)
        video_id = dataset.ingest_video(video_path=FIXTURE, license_type=LicenseType.LICENSE_REVIEW_REQUIRED)
        assert dataset.get_video_metadata(video_id)["license"] == "license_review_required"
        assert dataset.get_video_metadata(video_id)["license_verified_by"] is None
