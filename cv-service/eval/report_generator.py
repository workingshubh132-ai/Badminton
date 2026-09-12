"""
M5.5 Evaluation Report Generator

Generates comprehensive markdown report with metrics, classifications,
and decision-gate recommendation.
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .dataset import DatasetManager
from .schemas import (
    ComponentReadiness,
    ComponentStatus,
    EvaluationReport,
    ValidationKind,
)


class ReportGenerator:
    """Generates M5.5 evaluation reports."""

    def __init__(self, dataset_dir: str | Path = "cv-service/eval/datasets"):
        self.dataset = DatasetManager(dataset_dir)
        self.dataset_dir = Path(dataset_dir)

    def generate_report(self, clips_to_include: Optional[list[str]] = None) -> EvaluationReport:
        """Generate aggregate report for all evaluated clips."""
        if clips_to_include is None:
            clips_to_include = self.dataset.list_annotated_clips()

        # Collect evaluation results
        clip_results = []
        for clip_id in clips_to_include:
            eval_data = self.dataset.load_evaluation(clip_id)
            if eval_data:
                clip_results.append(eval_data)

        if not clip_results:
            raise ValueError("No evaluated clips found")

        # Partition the evidence. Readiness and the decision gate are computed
        # from real-world clips alone; a synthetic fixture can never move them.
        real_world = [
            r for r in clip_results if r.get("validation_kind") == ValidationKind.REAL_WORLD.value
        ]
        synthetic = [r for r in clip_results if r not in real_world]

        # Aggregate metrics -- real-world only.
        court_metrics = self._aggregate_court_metrics(real_world)
        detection_metrics = self._aggregate_detection_metrics(real_world)
        tracking_metrics = self._aggregate_tracking_metrics(real_world)
        quality_metrics = self._aggregate_quality_metrics(real_world)
        participant_metrics = self._aggregate_participant_metrics(real_world)

        # Classify components
        if real_world:
            court_readiness = self._classify_court(court_metrics)
            detection_readiness = self._classify_detection(detection_metrics)
            tracking_readiness = self._classify_tracking(tracking_metrics)
            quality_readiness = self._classify_quality(quality_metrics)
            participant_readiness = self._classify_participant(participant_metrics)
            decision, rationale = self._determine_decision_gate(
                court_readiness,
                detection_readiness,
                tracking_readiness,
                quality_readiness,
            )
        else:
            # No real footage has been evaluated. Every component is unproven,
            # and no decision gate is reachable -- including gate A.
            court_readiness = self._unproven("Court calibration")
            detection_readiness = self._unproven("Player detection")
            tracking_readiness = self._unproven("Player tracking")
            quality_readiness = self._unproven("Quality assessment")
            participant_readiness = self._unproven("Participant classification")
            decision = "NO_REAL_WORLD_EVIDENCE"
            rationale = (
                f"{len(synthetic)} synthetic clip(s) evaluated and 0 real-world clips. "
                "Synthetic fixtures verify that the evaluation machinery runs and computes "
                "the metrics it claims; they say nothing about accuracy on real badminton "
                "footage. No component readiness can be asserted and no decision gate -- "
                "including gate A -- can be reached until real footage is evaluated."
            )

        # Collect failures
        failures = self._collect_failures(clip_results)

        return EvaluationReport(
            generated_at=datetime.utcnow(),
            clips_evaluated=clip_results,
            real_world_clips=real_world,
            synthetic_clips=synthetic,
            has_real_world_evidence=bool(real_world),
            failures=failures,
            participant_readiness=participant_readiness,
            court_readiness=court_readiness,
            detection_readiness=detection_readiness,
            tracking_readiness=tracking_readiness,
            quality_readiness=quality_readiness,
            decision_gate=decision,
            decision_rationale=rationale,
            summary_metrics={
                "court": court_metrics,
                "detection": detection_metrics,
                "tracking": tracking_metrics,
                "quality": quality_metrics,
                "participant": participant_metrics,
            },
        )

    def _unproven(self, component_name: str) -> ComponentReadiness:
        """Readiness for a component no real footage has exercised.

        UNRELIABLE is the honest classification here: not "we measured it and it
        failed", but "nothing supports using this downstream yet". The rationale
        says which, so nobody reads it as a measured failure.
        """
        return ComponentReadiness(
            component=component_name,
            status=ComponentStatus.UNRELIABLE,
            reasoning=(
                f"{component_name} has never been evaluated against real badminton footage. "
                "This is an absence of evidence, not a measured failure -- the component may "
                "work well or badly, and we do not know which."
            ),
            metric_summary={"real_world_clips_evaluated": 0},
            critical_issues=["No real-world evidence exists for this component."],
            recommended_improvements=[
                "Evaluate real, licensed footage with ground-truth annotations before relying "
                "on this component."
            ],
        )

    def _aggregate_participant_metrics(self, clip_results: list[dict]) -> dict[str, Any]:
        """Aggregate participant-classification accuracy across clips."""
        scored = [
            r["participant_accuracy"]
            for r in clip_results
            if r.get("participant_accuracy")
        ]
        if not scored:
            return {"clips_with_participant_labels": 0}

        def mean_of(key: str) -> Optional[float]:
            values = [s[key] for s in scored if s.get(key) is not None]
            return statistics.mean(values) if values else None

        return {
            "clips_with_participant_labels": len(scored),
            "total_scored_people": sum(s.get("scored_people", 0) for s in scored),
            "total_false_participants": sum(s.get("false_positives", 0) for s in scored),
            "mean_precision": mean_of("precision"),
            "mean_recall": mean_of("recall"),
            "mean_f1": mean_of("f1"),
            "mean_false_participant_rate": mean_of("false_participant_rate"),
            "mean_unresolved_rate": mean_of("unresolved_rate"),
        }

    def _classify_participant(self, metrics: dict[str, Any]) -> ComponentReadiness:
        """Classify participant separation.

        The false-participant rate is weighted above precision on purpose: a
        spectator promoted to a player corrupts every downstream inference, so it
        is a worse failure than leaving someone unresolved.
        """
        if not metrics.get("clips_with_participant_labels"):
            return ComponentReadiness(
                component="Participant classification",
                status=ComponentStatus.UNRELIABLE,
                reasoning=(
                    "No evaluated clip carries participant annotations, so the separation of "
                    "players from spectators and officials has never been scored."
                ),
                metric_summary={"clips_with_participant_labels": 0},
                recommended_improvements=[
                    "Annotate participant status on real footage and re-evaluate."
                ],
            )

        false_rate = metrics.get("mean_false_participant_rate")
        unresolved = metrics.get("mean_unresolved_rate")
        precision = metrics.get("mean_precision")
        recall = metrics.get("mean_recall")
        summary = {
            "precision": precision,
            "recall": recall,
            "false_participant_rate": false_rate,
            "unresolved_rate": unresolved,
            "people_scored": metrics.get("total_scored_people", 0),
            "clips_with_participant_labels": metrics["clips_with_participant_labels"],
        }

        if false_rate is not None and false_rate > 0.10:
            status = ComponentStatus.UNRELIABLE
            reasoning = (
                f"{false_rate:.0%} of annotated bystanders were promoted to participants. "
                "Spectators entering player analysis corrupt everything downstream."
            )
        elif precision is not None and recall is not None and precision >= 0.9 and recall >= 0.85:
            status = ComponentStatus.PRODUCTION_READY
            reasoning = "Participants separated from bystanders accurately on real footage."
        elif unresolved is not None and unresolved > 0.5:
            status = ComponentStatus.NEEDS_IMPROVEMENT
            reasoning = (
                f"{unresolved:.0%} of people were left UNKNOWN. Safe, but too often undecided "
                "to support downstream analysis."
            )
        else:
            status = ComponentStatus.VALIDATION_READY
            reasoning = "Participant separation works on real footage but needs monitoring."

        return ComponentReadiness(
            component="Participant classification",
            status=status,
            reasoning=reasoning,
            metric_summary=summary,
            recommended_improvements=(
                []
                if status == ComponentStatus.PRODUCTION_READY
                else ["Improve before relying on participant-derived inferences."]
            ),
        )

    def _aggregate_court_metrics(self, clip_results: list[dict]) -> dict[str, Any]:
        """Aggregate court calibration metrics."""
        success_count = 0
        corner_errors = []
        ious = []

        for result in clip_results:
            court = result.get("court_accuracy", {})
            if court.get("succeeded"):
                success_count += 1
                if court.get("mean_corner_error_px"):
                    corner_errors.append(court["mean_corner_error_px"])
                if court.get("iou_with_ground_truth"):
                    ious.append(court["iou_with_ground_truth"])

        return {
            "success_rate": success_count / len(clip_results) if clip_results else 0.0,
            "mean_corner_error_px": statistics.mean(corner_errors) if corner_errors else None,
            "median_corner_error_px": statistics.median(corner_errors) if corner_errors else None,
            "max_corner_error_px": max(corner_errors) if corner_errors else None,
            "mean_iou": statistics.mean(ious) if ious else None,
            "min_iou": min(ious) if ious else None,
            "failures": [r for r in clip_results if not r.get("court_accuracy", {}).get("succeeded")],
        }

    def _aggregate_detection_metrics(self, clip_results: list[dict]) -> dict[str, Any]:
        """Aggregate player detection metrics."""
        precisions = []
        recalls = []
        total_fp = 0
        total_fn = 0
        total_gt = 0
        total_detected = 0

        for result in clip_results:
            detection = result.get("detection_accuracy", {})
            if detection.get("precision") is not None:
                precisions.append(detection["precision"])
            if detection.get("recall") is not None:
                recalls.append(detection["recall"])
            total_fp += detection.get("false_positives", 0)
            total_fn += detection.get("false_negatives", 0)
            total_gt += detection.get("ground_truth_count", 0)
            total_detected += detection.get("detected_count", 0)

        overall_precision = (
            (total_detected - total_fp) / total_detected if total_detected > 0 else 0.0
        )
        overall_recall = (total_gt - total_fn) / total_gt if total_gt > 0 else 0.0

        return {
            "mean_precision": statistics.mean(precisions) if precisions else None,
            "mean_recall": statistics.mean(recalls) if recalls else None,
            "overall_precision": overall_precision,
            "overall_recall": overall_recall,
            "total_false_positives": total_fp,
            "total_false_negatives": total_fn,
            "total_ground_truth": total_gt,
            "total_detected": total_detected,
        }

    def _aggregate_tracking_metrics(self, clip_results: list[dict]) -> dict[str, Any]:
        """Aggregate tracking metrics."""
        track_counts = []
        mean_lengths = []
        total_gaps = 0
        total_switches = 0

        for result in clip_results:
            tracking = result.get("tracking_accuracy", {})
            track_counts.append(tracking.get("tracks_found", 0))
            if tracking.get("mean_track_length"):
                mean_lengths.append(tracking["mean_track_length"])
            total_gaps += tracking.get("gaps_observed", 0)
            total_switches += tracking.get("identity_switches", 0)

        return {
            "total_tracks_found": sum(track_counts),
            "mean_tracks_per_clip": statistics.mean(track_counts) if track_counts else 0.0,
            "mean_track_length_frames": statistics.mean(mean_lengths) if mean_lengths else 0.0,
            "total_tracking_gaps": total_gaps,
            "total_identity_switches": total_switches,
        }

    def _aggregate_quality_metrics(self, clip_results: list[dict]) -> dict[str, Any]:
        """Aggregate quality assessment accuracy."""
        accuracies = []
        total_correct = 0
        total_frames = 0

        for result in clip_results:
            quality = result.get("quality_accuracy", {})
            if quality.get("accuracy"):
                accuracies.append(quality["accuracy"])
            total_correct += quality.get("correct_classifications", 0)
            total_frames += quality.get("total_frames", 0)

        return {
            "mean_accuracy": statistics.mean(accuracies) if accuracies else None,
            "overall_accuracy": total_correct / total_frames if total_frames > 0 else 0.0,
            "total_correct": total_correct,
            "total_frames": total_frames,
        }

    def _classify_court(self, metrics: dict[str, Any]) -> ComponentReadiness:
        """Classify court calibration component."""
        success_rate = metrics.get("success_rate", 0.0)
        mean_error = metrics.get("mean_corner_error_px")
        mean_iou = metrics.get("mean_iou")

        if success_rate >= 0.9 and mean_error and mean_error < 10 and mean_iou and mean_iou > 0.95:
            status = ComponentStatus.PRODUCTION_READY
            reasoning = "Consistent court detection with excellent accuracy"
        elif success_rate >= 0.7 and mean_error and mean_error < 20 and mean_iou and mean_iou > 0.90:
            status = ComponentStatus.VALIDATION_READY
            reasoning = "Good court detection with minor occasional errors"
        elif success_rate >= 0.5:
            status = ComponentStatus.NEEDS_IMPROVEMENT
            reasoning = "Court detection works but has reliability issues"
        else:
            status = ComponentStatus.UNRELIABLE
            reasoning = "Court detection fails too frequently"

        return ComponentReadiness(
            component="COURT_CALIBRATION",
            status=status,
            metric_summary={
                "success_rate": f"{success_rate:.1%}",
                "mean_corner_error_px": f"{mean_error:.2f}" if mean_error else "N/A",
                "mean_iou": f"{mean_iou:.4f}" if mean_iou else "N/A",
            },
            reasoning=reasoning,
            critical_issues=["Court detection unreliable"] if success_rate < 0.5 else [],
            recommended_improvements=[
                "Improve edge detection robustness",
                "Handle perspective distortion better",
            ],
        )

    def _classify_detection(self, metrics: dict[str, Any]) -> ComponentReadiness:
        """Classify player detection component."""
        precision = metrics.get("overall_precision", 0.0)
        recall = metrics.get("overall_recall", 0.0)

        if precision >= 0.9 and recall >= 0.85:
            status = ComponentStatus.PRODUCTION_READY
            reasoning = "Excellent precision and recall on real footage"
        elif precision >= 0.8 and recall >= 0.75:
            status = ComponentStatus.VALIDATION_READY
            reasoning = "Good detection with occasional false positives/negatives"
        elif precision >= 0.7 or recall >= 0.6:
            status = ComponentStatus.NEEDS_IMPROVEMENT
            reasoning = "Detection works but accuracy is inconsistent"
        else:
            status = ComponentStatus.UNRELIABLE
            reasoning = "Detection accuracy too low for downstream use"

        return ComponentReadiness(
            component="PLAYER_DETECTION",
            status=status,
            metric_summary={
                "precision": f"{precision:.1%}",
                "recall": f"{recall:.1%}",
                "false_positives": metrics.get("total_false_positives", 0),
                "false_negatives": metrics.get("total_false_negatives", 0),
            },
            reasoning=reasoning,
            critical_issues=["Low recall"] if recall < 0.5 else [],
            recommended_improvements=[
                "Improve confidence threshold tuning",
                "Handle small/occluded players",
            ],
        )

    def _classify_tracking(self, metrics: dict[str, Any]) -> ComponentReadiness:
        """Classify player tracking component."""
        mean_length = metrics.get("mean_track_length_frames", 0.0)
        gaps = metrics.get("total_tracking_gaps", 0)
        switches = metrics.get("total_identity_switches", 0)

        if mean_length >= 30 and gaps == 0 and switches == 0:
            status = ComponentStatus.PRODUCTION_READY
            reasoning = "Stable tracking with no gaps or switches"
        elif mean_length >= 20 and gaps <= 2 and switches <= 2:
            status = ComponentStatus.VALIDATION_READY
            reasoning = "Good tracking with occasional gaps"
        elif mean_length >= 10:
            status = ComponentStatus.NEEDS_IMPROVEMENT
            reasoning = "Tracking works but is fragmented"
        else:
            status = ComponentStatus.UNRELIABLE
            reasoning = "Tracking too fragmented for downstream analysis"

        return ComponentReadiness(
            component="PLAYER_TRACKING",
            status=status,
            metric_summary={
                "mean_track_length_frames": f"{mean_length:.1f}",
                "total_gaps": gaps,
                "total_switches": switches,
            },
            reasoning=reasoning,
            critical_issues=["Frequent tracking gaps"] if gaps > 5 else [],
            recommended_improvements=[
                "Increase IoU matching threshold",
                "Improve gap-bridging logic",
            ],
        )

    def _classify_quality(self, metrics: dict[str, Any]) -> ComponentReadiness:
        """Classify video quality assessment."""
        accuracy = metrics.get("overall_accuracy", 0.0)

        if accuracy >= 0.85:
            status = ComponentStatus.PRODUCTION_READY
            reasoning = "Accurate quality assessment"
        elif accuracy >= 0.75:
            status = ComponentStatus.VALIDATION_READY
            reasoning = "Good quality assessment with occasional misclassifications"
        elif accuracy >= 0.6:
            status = ComponentStatus.NEEDS_IMPROVEMENT
            reasoning = "Quality assessment works but has accuracy issues"
        else:
            status = ComponentStatus.UNRELIABLE
            reasoning = "Quality assessment too inaccurate"

        return ComponentReadiness(
            component="QUALITY_ASSESSMENT",
            status=status,
            metric_summary={"accuracy": f"{accuracy:.1%}"},
            reasoning=reasoning,
            critical_issues=[] if accuracy >= 0.6 else ["Low accuracy"],
            recommended_improvements=[
                "Tune quality thresholds against real footage",
                "Consider additional quality signals",
            ],
        )

    def _determine_decision_gate(
        self,
        court: ComponentReadiness,
        detection: ComponentReadiness,
        tracking: ComponentReadiness,
        quality: ComponentReadiness,
    ) -> tuple[str, str]:
        """Determine which decision gate to recommend."""
        # Implement decision logic based on spec
        if (
            court.status == ComponentStatus.PRODUCTION_READY
            and detection.status in (ComponentStatus.PRODUCTION_READY, ComponentStatus.VALIDATION_READY)
            and tracking.status in (ComponentStatus.PRODUCTION_READY, ComponentStatus.VALIDATION_READY)
        ):
            return (
                "A",
                "All core components are production or validation ready. Proceed to M6 (shot detection).",
            )

        if court.status == ComponentStatus.UNRELIABLE:
            return (
                "B",
                "Court detection is unreliable. Must improve before M6 can work.",
            )

        if detection.status == ComponentStatus.UNRELIABLE:
            return (
                "C",
                "Player detection is unreliable. Needs threshold tuning or model evaluation.",
            )

        if tracking.status == ComponentStatus.UNRELIABLE:
            return (
                "D",
                "Player tracking is unreliable. Improve IoU matching and gap-bridging.",
            )

        if quality.status == ComponentStatus.UNRELIABLE:
            return (
                "E",
                "Quality assessment is unreliable. Retune thresholds.",
            )

        return (
            "B",
            "Multiple components need improvement. Prioritize court detection.",
        )

    def _collect_failures(self, clip_results: list[dict]) -> list[dict]:
        """Collect all recorded failures."""
        failures = []
        for result in clip_results:
            for failure in result.get("failures", []):
                failure_copy = failure.copy()
                failure_copy["clip_id"] = result.get("clip_id")
                failures.append(failure_copy)
        return failures

    def render_markdown(self, report: EvaluationReport) -> str:
        """Render report as markdown."""
        real_n = len(report.real_world_clips)
        synth_n = len(report.synthetic_clips)
        banner = (
            "> **This report contains NO real-world validation.**\n>\n"
            f"> {synth_n} synthetic clip(s) were evaluated and {real_n} real-world clip(s). "
            "Synthetic fixtures are rendered images: they verify that the evaluation "
            "machinery runs and computes the metrics it claims, and prove nothing about "
            "accuracy on real badminton footage. Every component below is classified "
            "UNRELIABLE for absence of evidence, which is not the same as a measured "
            "failure.\n"
            if not report.has_real_world_evidence
            else
            "> **Evidence basis: real-world footage.**\n>\n"
            f"> Component readiness and the decision gate below are computed from the "
            f"{real_n} real-world clip(s) ONLY. {synth_n} synthetic clip(s) were also "
            "evaluated; they are reported separately as machinery verification and are "
            "excluded from every metric, classification and gate decision below.\n"
        )

        md = f"""# M5.5 EVALUATION REPORT

Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

{banner}
## EVIDENCE BASIS

| Kind | Clips | Counts toward readiness |
|------|-------|-------------------------|
| Real-world footage | {real_n} | yes |
| Synthetic fixtures | {synth_n} | no — machinery verification only |

## EXECUTIVE SUMMARY

**Decision Gate: {report.decision_gate}**

{report.decision_rationale}

## COMPONENT READINESS

### Participant Classification: {report.participant_readiness.status.value if report.participant_readiness else "not assessed"}

{report.participant_readiness.reasoning if report.participant_readiness else "No participant readiness was computed."}

### Court Calibration: {report.court_readiness.status.value}

{report.court_readiness.reasoning}

| Metric | Value |
|--------|-------|
"""
        for key, value in report.court_readiness.metric_summary.items():
            md += f"| {key} | {value} |\n"

        md += f"""
### Player Detection: {report.detection_readiness.status.value}

{report.detection_readiness.reasoning}

| Metric | Value |
|--------|-------|
"""
        for key, value in report.detection_readiness.metric_summary.items():
            md += f"| {key} | {value} |\n"

        md += f"""
### Player Tracking: {report.tracking_readiness.status.value}

{report.tracking_readiness.reasoning}

| Metric | Value |
|--------|-------|
"""
        for key, value in report.tracking_readiness.metric_summary.items():
            md += f"| {key} | {value} |\n"

        md += f"""
### Video Quality Assessment: {report.quality_readiness.status.value}

{report.quality_readiness.reasoning}

| Metric | Value |
|--------|-------|
"""
        for key, value in report.quality_readiness.metric_summary.items():
            md += f"| {key} | {value} |\n"

        md += f"""

## PER-CLIP RESULTS

"""
        def render_clip_rows(results, heading, caveat):
            nonlocal md
            md += f"\n### {heading}\n\n{caveat}\n"
            if not results:
                md += "\n_None._\n"
                return
            md += (
                "\n| Clip | Court | Detection P/R | Tracks | Quality | "
                "Participant P/R | False-participant | Unresolved |\n"
                "|---|---|---|---|---|---|---|---|\n"
            )
            for result in results:
                def pct(value):
                    return "n/a" if value is None else f"{value:.0%}"

                det = result.detection_accuracy
                part = result.participant_accuracy
                md += (
                    f"| `{result.clip_id}` "
                    f"| {result.court_accuracy.status} "
                    f"| {pct(det.precision)} / {pct(det.recall)} "
                    f"| {result.tracking_accuracy.tracks_found} "
                    f"| {pct(result.quality_accuracy.accuracy)} "
                    f"| {pct(part.precision) if part else 'not scored'} / "
                    f"{pct(part.recall) if part else 'n/a'} "
                    f"| {pct(part.false_participant_rate) if part else 'n/a'} "
                    f"| {pct(part.unresolved_rate) if part else 'n/a'} |\n"
                )

        render_clip_rows(
            report.real_world_clips,
            "Real-world footage",
            "These results, and only these, drive the component readiness and decision gate above.",
        )
        render_clip_rows(
            report.synthetic_clips,
            "Synthetic fixtures",
            "Machinery verification only. Rendered images, not badminton. These numbers are "
            "excluded from every classification and from the decision gate, and must never be "
            "quoted as real-world accuracy.",
        )

        if report.failures:
            md += f"""
## FAILURE ANALYSIS

{len(report.failures)} notable failures identified:

"""
            for failure in report.failures[:20]:  # Limit to 20
                md += f"""
- **{failure.get("component")}** (Severity: {failure.get("severity", "UNKNOWN")})
  - Description: {failure.get("description")}
  - Likely cause: {failure.get("likely_cause")}
  - Suggested fix: {failure.get("suggested_fix")}
"""

        md += """

## NEXT STEPS

See "Decision Gate" section above for specific recommendation.

---

*Generated by M5.5 Evaluation Suite*
"""
        return md

    def generate_and_save(
        self,
        output_path: str | Path | None = None,
        clips_to_include: Optional[list[str]] = None,
    ) -> Path:
        """Generate report and save to file."""
        report = self.generate_report(clips_to_include)
        markdown = self.render_markdown(report)

        if output_path is None:
            output_path = self.dataset_dir / "M5.5_EVALUATION_REPORT.md"

        output_path = Path(output_path)
        output_path.write_text(markdown)

        # Also save JSON report
        json_path = output_path.with_suffix(".json")
        json_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2))

        return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate M5.5 evaluation report.")
    parser.add_argument("--dataset-dir", default="cv-service/eval/datasets", help="Dataset directory")
    parser.add_argument("--output", help="Output path (default: {dataset-dir}/M5.5_EVALUATION_REPORT.md)")

    args = parser.parse_args()

    generator = ReportGenerator(args.dataset_dir)
    report_path = generator.generate_and_save(args.output)
    print(f"✓ Report generated: {report_path}")


if __name__ == "__main__":
    main()
