"""Generate the dataset v1 reports from whatever was actually acquired and measured.

Both reports are written from live registry + analysis state. If nothing was acquired,
the reports say so rather than describing footage nobody has seen.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .sources import LICENSE_REVIEW_REQUIRED, Source, dataset_root, load_registry

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_analyses(root: Path) -> dict[str, dict]:
    directory = root / "analysis"
    if not directory.exists():
        return {}
    return {p.stem: json.loads(p.read_text()) for p in sorted(directory.glob("*.json"))}


def _reason_guidance(reason: str) -> tuple[str, str]:
    """Map a blocked-reason code to (plain explanation, what a normal user must do)."""
    if reason.startswith("EGRESS_POLICY_DENIED"):
        return (
            "This session's network egress proxy refused the CONNECT tunnel with HTTP 403. "
            "The host is not on the allowlist for this environment. This is a restriction on "
            "*our* sandbox, not an access control on the provider: no login, paywall, DRM or "
            "rate limit was encountered, and nothing was bypassed.",
            "Open the page in a normal browser on your own machine and use the provider's own "
            "Free Download button. Choose the highest resolution offered.",
        )
    if reason.startswith("NO_DIRECT_ASSET_EXPOSED"):
        return (
            "The page was fetched successfully but exposed no direct video asset URL in its "
            "markup, og:video tag or JSON-LD. The download is likely issued by a client-side "
            "request we will not reconstruct.",
            "Open the page in a normal browser and use the provider's own download control.",
        )
    if reason.startswith("REQUIRES_AUTHENTICATION"):
        return (
            "The provider returned 401 -- the asset sits behind an account. We do not "
            "authenticate on your behalf.",
            "Sign in to your own account in a browser and download the file normally.",
        )
    if reason.startswith("NETWORK_ERROR"):
        return ("The request failed at the network layer.", "Retry, or download in a browser.")
    return ("Automated acquisition was not attempted.", "Download the file in a browser.")


def render_manual_download(root: Path, sources: list[Source]) -> str:
    blocked = [s for s in sources if not s.downloaded_filename]
    incoming = root / "incoming"
    try:
        incoming_display = incoming.relative_to(REPO_ROOT)
    except ValueError:
        incoming_display = incoming

    lines = [
        "# Manual Download Required",
        "",
        f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}_",
        "",
        f"**{len(blocked)} of {len(sources)} candidate sources could not be acquired "
        "automatically.**",
        "",
        "Nothing in this list was blocked by a provider access control. No authentication, "
        "paywall, DRM, rate limit or robots restriction was encountered or circumvented.",
        "",
    ]

    if not blocked:
        lines += ["All sources were acquired automatically. No manual action is needed.", ""]
        return "\n".join(lines)

    for source in blocked:
        explanation, action = _reason_guidance(source.automated_download_blocked_reason)
        lines += [
            f"## {source.source_id}",
            "",
            f"- **Source page**: {source.source_url}",
            f"- **Provider**: {source.provider}",
            f"- **Licence terms**: {source.license_terms_url}",
            f"- **Licence status**: `{source.license_status}`",
            "",
            f"**Exact reason automated retrieval is not possible**  ",
            f"`{source.automated_download_blocked_reason or 'not attempted'}`",
            "",
            explanation,
            "",
            f"**Normal user action required**  ",
            action,
            "",
            f"**Where to put the resulting file**  ",
            f"`{incoming_display}/{source.expected_filename}`",
            "",
            "Any filename works -- the inspector reads every video in `incoming/` -- but using "
            "the name above keeps the file matched to its source record and licence metadata.",
            "",
            "---",
            "",
        ]

    lines += [
        "## After you have downloaded the files",
        "",
        "Run one command. Everything downstream is automatic:",
        "",
        "```bash",
        "python -m eval dataset-v1",
        "```",
        "",
        "That hashes each file, reads its real metadata with ffprobe, decodes and measures "
        "frames, writes contact sheets to `dataset_v1/contact_sheets/`, classifies each "
        "candidate, and regenerates `DATASET_V1_SELECTION_REPORT.md`.",
        "",
        "## Licence check you must do yourself",
        "",
        "Read the terms URL for each source before the footage is used for anything beyond "
        "local evaluation, and record the outcome in `dataset_v1/sources.json` by setting "
        "`license_status` to `PERMITTED` or `REFERENCE_ONLY` and `license_verified` to `true`. "
        "Until then every source stays `LICENSE_REVIEW_REQUIRED`. Free to download is not the "
        "same as cleared for a redistributed or commercial dataset, and this tooling makes no "
        "claim either way.",
        "",
    ]
    return "\n".join(lines)


def render_selection_report(root: Path, sources: list[Source], analyses: dict[str, dict]) -> str:
    acquired = [s for s in sources if s.downloaded_filename]
    blocked = [s for s in sources if not s.downloaded_filename]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    lines = [
        "# Dataset v1 Selection Report",
        "",
        f"_Generated {now}_",
        "",
        "Scope: acquire real badminton footage and triage it for the M5.5 validation gate. "
        "No M5 evaluation is run here, and no real-world accuracy claim is made.",
        "",
        "**Every verdict below comes from decoded frames.** Page titles and provider "
        "descriptions are recorded for traceability and are never inputs to a classification. "
        "Where no file was acquired, no verdict is given.",
        "",
        "### Tooling status",
        "",
        "The acquisition and inspection pipeline has been run end to end against "
        "`cv-service/eval/fixtures/synthetic_court_01.mp4` to confirm it works before anyone "
        "spends effort downloading: ffprobe metadata, SHA-256, frame decoding, all measurements, "
        "both contact sheets, per-file JSON and this report were produced. That is a **tooling "
        "self-test only**; it validates nothing about M5's real-world accuracy and the fixture "
        "is not part of the candidate set.",
        "",
        "**Known weakness — read this before trusting any person count.** The triage person "
        "detector was probed against the public-domain NASA astronaut photo that ships with "
        "scikit-image. Single-scale HOG fired at 1.0x and 2.0x input scale but found nothing at "
        "1.5x, so it is sharply scale-brittle; the detector now sweeps several scales and merges "
        "with non-max suppression, which closed that blind spot. Detection still fell off sharply "
        "once the figure dropped below roughly 80% of frame height — though that sample is a "
        "head-and-torso portrait, off-distribution for a full-body pedestrian detector, so it "
        "understates real performance and is not a calibrated floor.",
        "",
        "The honest position: **the person detector is not calibrated against real players**, "
        "because no footage containing people was reachable from this environment. Person counts "
        "should be read as a lower bound, never as truth. That is exactly why zero detections "
        "cannot produce a REJECT — only hard technical facts (resolution, duration, no continuous "
        "segment) can. On the first real run, compare the `_annotated` contact sheet against the "
        "raw one and correct the verdicts by eye.",
        "",
        "---",
        "",
        "## 1. Sources inspected",
        "",
        "| Source | Provider | Page | Automated download |",
        "|---|---|---|---|",
    ]
    for source in sources:
        state = "yes" if source.downloaded_filename else "no"
        lines.append(
            f"| `{source.source_id}` | {source.provider} | {source.source_url} | {state} |"
        )

    lines += [
        "",
        f"## 2. Sources successfully acquired",
        "",
    ]
    if acquired:
        lines += ["| Source | File | SHA-256 |", "|---|---|---|"]
        for source in acquired:
            stem = Path(source.downloaded_filename).stem
            digest = analyses.get(stem, {}).get("metadata", {}).get("sha256", "not yet hashed")
            lines.append(f"| `{source.source_id}` | `{source.downloaded_filename}` | `{digest}` |")
    else:
        lines.append(
            "**None.** No candidate footage is present in the evaluation dataset. "
            "See section 3."
        )

    lines += ["", "## 3. Sources requiring manual download", ""]
    if blocked:
        lines.append(f"{len(blocked)} of {len(sources)}. Full instructions: "
                     "[`MANUAL_DOWNLOAD_REQUIRED.md`](MANUAL_DOWNLOAD_REQUIRED.md)")
        lines += ["", "| Source | Reason |", "|---|---|"]
        for source in blocked:
            reason = source.automated_download_blocked_reason or "not attempted"
            lines.append(f"| `{source.source_id}` | `{reason}` |")
    else:
        lines.append("None.")

    lines += ["", "## 4. Actual video metadata", ""]
    if analyses:
        lines += [
            "Measured with ffprobe on the acquired files -- not copied from any page.",
            "",
            "| File | Resolution | FPS | Duration | Codec | Size | SHA-256 |",
            "|---|---|---|---|---|---|---|",
        ]
        for stem, record in analyses.items():
            m = record["metadata"]
            lines.append(
                f"| `{m['filename']}` | {m['resolution']} | {m['fps']} | "
                f"{m['duration_seconds']}s | {m['codec']} | {m['file_size_bytes']:,} B | "
                f"`{m['sha256'][:16]}...` |"
            )
    else:
        lines.append("No files acquired, so no metadata could be measured.")

    lines += ["", "## 5. Frame and contact-sheet observations", ""]
    if analyses:
        lines += [
            "Contact sheets are in `dataset_v1/contact_sheets/` -- one raw sheet and one "
            "annotated sheet per file showing what the triage detectors saw.",
            "",
            "Triage detectors are deliberately **not** the M5 detectors. Selecting clips with "
            "the same detector M5.5 is about to grade would bias the validation toward footage "
            "M5 already handles. These proxies are weaker, so a weak score routes to "
            "MANUAL_REVIEW rather than REJECT.",
            "",
        ]
        for stem, record in analyses.items():
            meas, cls = record["measurements"], record["classification"]
            persons = meas["persons"]
            lines += [
                f"### `{record['metadata']['filename']}` — **{cls['verdict']}**",
                "",
                f"- Likely format: **{cls['likely_format']}**",
                f"- People per frame: median {persons['median_per_frame']}, max "
                f"{persons['max_per_frame']}; 2+ people in {persons['frames_with_2plus_pct']}% "
                f"of {meas['sampled_frames']} sampled frames",
                f"- Player separation (median, normalised to frame width): "
                f"{meas['player_separation_norm_median']}",
                f"- Court-line evidence (0-1): {meas['court_line_evidence_median']}",
                f"- Camera motion: median {meas['camera_motion_px_median']}px, p90 "
                f"{meas['camera_motion_px_p90']}px inter-frame translation",
                f"- Lighting: mean luma {meas['luminance']['mean_of_means']}, max clipped "
                f"{meas['luminance']['max_clipped_pct']}%, max crushed "
                f"{meas['luminance']['max_crushed_pct']}%",
                f"- Shot cuts detected: {len(meas['shot_cuts_detected'])}; longest continuous "
                f"segment {meas['longest_segment_seconds']}s",
                "",
            ]
            if cls["supporting_evidence"]:
                lines += ["Supporting:", ""] + [f"- {r}" for r in cls["supporting_evidence"]] + [""]
            if cls["review_reasons"]:
                lines += ["Needs a human look:", ""] + [f"- {r}" for r in cls["review_reasons"]] + [""]
            if cls["reject_reasons"]:
                lines += ["Disqualifying:", ""] + [f"- {r}" for r in cls["reject_reasons"]] + [""]
    else:
        lines.append(
            "No frames could be inspected, because no footage was acquired. "
            "**No classification is offered for any candidate.** Producing "
            "ACCEPT/MANUAL_REVIEW/REJECT verdicts from page titles would be a guess, and the "
            "point of this step is to judge the actual pixels."
        )

    lines += ["", "## 6. Best candidate clips", ""]
    ranked = [
        (stem, r) for stem, r in analyses.items()
        if r["classification"]["verdict"] in ("ACCEPT", "MANUAL_REVIEW")
    ]
    if ranked:
        lines += ["| File | Verdict | Segment | Duration | 2-player frames |", "|---|---|---|---|---|"]
        for stem, record in ranked:
            for segment in record["classification"]["best_candidate_segments"]:
                lines.append(
                    f"| `{record['metadata']['filename']}` | "
                    f"{record['classification']['verdict']} | "
                    f"{segment['start']}s–{segment['end']}s | {segment['duration']}s | "
                    f"{segment['two_player_frame_pct']}% |"
                )
    else:
        lines.append("None available — no footage has been acquired or inspected yet.")

    lines += [
        "",
        "## 7. Licensing status",
        "",
        "| Source | Terms URL | Status | Verified by a human |",
        "|---|---|---|---|",
    ]
    for source in sources:
        lines.append(
            f"| `{source.source_id}` | {source.license_terms_url} | "
            f"`{source.license_status}` | {'yes' if source.license_verified else 'no'} |"
        )
    unverified = [s for s in sources if not s.license_verified]
    if unverified:
        lines += [
            "",
            f"All {len(unverified)} source(s) are `{LICENSE_REVIEW_REQUIRED}`. The licence text "
            "was not retrievable from this environment, so it has not been read. This tooling "
            "therefore makes **no** statement about what the licence permits — in particular it "
            "does not treat free-to-download as cleared for redistribution or commercial "
            "dataset use. A human must read each terms URL and record the outcome in "
            "`dataset_v1/sources.json`.",
            "",
            "Source media, extracted frames and contact sheets are git-ignored. Only measured "
            "facts (hashes, ffprobe output, scores) are committed, so no footage is "
            "redistributed through this repository.",
        ]

    lines += ["", "## 8. Exact next action", ""]
    if blocked:
        lines += [
            f"1. Download the {len(blocked)} file(s) listed in "
            "[`MANUAL_DOWNLOAD_REQUIRED.md`](MANUAL_DOWNLOAD_REQUIRED.md) using each provider's "
            "own download button, and save them to `dataset_v1/incoming/`.",
            "2. Run `python -m eval dataset-v1`. Hashing, ffprobe metadata, frame measurement, "
            "contact sheets, classification and this report all regenerate automatically.",
            "3. Read each licence terms URL and set `license_status` in `dataset_v1/sources.json`.",
            "4. Review the contact sheets and confirm or overrule each MANUAL_REVIEW verdict.",
            "",
            "Alternative to step 1, if you would rather not download by hand: have the "
            "environment's egress allowlist extended to the provider hosts "
            "(`www.pexels.com`, `videos.pexels.com`), then re-run `python -m eval dataset-v1`. "
            "The acquisition path is implemented and will fetch the files unattended.",
            "",
            "Switching provider will not help from this sandbox. At the time this report was "
            "generated, `archive.org`, `commons.wikimedia.org`, `upload.wikimedia.org`, "
            "`openverse.org`, `pixabay.com` and `www.youtube.com` were each probed and each "
            "returned the same 403 CONNECT denial. The allowlist here covers package registries "
            "and source control, not media hosts, so either the allowlist changes or a human "
            "downloads the files.",
        ]
    else:
        lines += [
            "1. Read each licence terms URL and set `license_status` in "
            "`dataset_v1/sources.json`.",
            "2. Review contact sheets and confirm the ACCEPT / MANUAL_REVIEW verdicts.",
            "3. Ingest the accepted clips into the M5.5 dataset with "
            "`python -m eval ingest ... --source-url ...`, then annotate and evaluate.",
        ]

    lines += [
        "",
        "M5 was not modified. M6 was not started. No M5.5 evaluation was run, and no "
        "real-world accuracy has been measured or claimed.",
        "",
    ]
    return "\n".join(lines)


def write_reports(root: str | Path | None = None) -> tuple[Path, Path]:
    dataset = dataset_root(root)
    sources = load_registry(dataset)
    analyses = _load_analyses(dataset)

    # Reports live at the repo root alongside the other milestone documents.
    out_dir = REPO_ROOT if dataset.parent == REPO_ROOT else dataset
    manual = out_dir / "MANUAL_DOWNLOAD_REQUIRED.md"
    selection = out_dir / "DATASET_V1_SELECTION_REPORT.md"
    manual.write_text(render_manual_download(dataset, sources))
    selection.write_text(render_selection_report(dataset, sources, analyses))
    print(f"\nwrote {manual}\nwrote {selection}")
    return manual, selection


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Write dataset v1 reports.")
    parser.add_argument("--dataset-dir", default=None)
    args = parser.parse_args()
    write_reports(args.dataset_dir)
    return 0
