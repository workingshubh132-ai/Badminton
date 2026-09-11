# Dataset v1 Selection Report

_Generated 2026-09-11T17:12:31+00:00_

Scope: acquire real badminton footage and triage it for the M5.5 validation gate. No M5 evaluation is run here, and no real-world accuracy claim is made.

**Every verdict below comes from decoded frames.** Page titles and provider descriptions are recorded for traceability and are never inputs to a classification. Where no file was acquired, no verdict is given.

### Tooling status

The acquisition and inspection pipeline has been run end to end against `cv-service/eval/fixtures/synthetic_court_01.mp4` to confirm it works before anyone spends effort downloading: ffprobe metadata, SHA-256, frame decoding, all measurements, both contact sheets, per-file JSON and this report were produced. That is a **tooling self-test only**; it validates nothing about M5's real-world accuracy and the fixture is not part of the candidate set.

**Known weakness — read this before trusting any person count.** The triage person detector was probed against the public-domain NASA astronaut photo that ships with scikit-image. Single-scale HOG fired at 1.0x and 2.0x input scale but found nothing at 1.5x, so it is sharply scale-brittle; the detector now sweeps several scales and merges with non-max suppression, which closed that blind spot. Detection still fell off sharply once the figure dropped below roughly 80% of frame height — though that sample is a head-and-torso portrait, off-distribution for a full-body pedestrian detector, so it understates real performance and is not a calibrated floor.

It over-counts too, and that has now been observed on real footage. On broadcast badminton clips inspected for `GITHUB_DATASET_ACQUISITION_REPORT.md` it reported a median of 4.5-7 people per frame and labelled every clip "doubles"; the annotated contact sheets showed it boxing seated line judges and crowd in the stands. All of those clips were singles. Treat `likely_format` as unreliable wherever spectators or officials are visible.

The honest position: **the person detector is not calibrated against real players**, because no footage containing people was reachable from this environment. Person counts should be read as a lower bound, never as truth. That is exactly why zero detections cannot produce a REJECT — only hard technical facts (resolution, duration, no continuous segment) can. On the first real run, compare the `_annotated` contact sheet against the raw one and correct the verdicts by eye.

---

## 1. Sources inspected

| Source | Provider | Page | Automated download |
|---|---|---|---|
| `pexels_35087073` | Pexels | https://www.pexels.com/video/boys-playing-badminton-on-indoor-court-35087073/ | no |
| `pexels_8052834` | Pexels | https://www.pexels.com/video/badminton-player-playing-indoors-8052834/ | no |
| `pexels_8053646` | Pexels | https://www.pexels.com/video/people-playing-badminton-8053646/ | no |
| `pexels_8053653` | Pexels | https://www.pexels.com/video/teammates-playing-badminton-8053653/ | no |
| `pexels_35087074` | Pexels | https://www.pexels.com/video/dynamic-indoor-badminton-match-with-youths-35087074/ | no |

## 2. Sources successfully acquired

**None.** No candidate footage is present in the evaluation dataset. See section 3.

## 3. Sources requiring manual download

5 of 5. Full instructions: [`MANUAL_DOWNLOAD_REQUIRED.md`](MANUAL_DOWNLOAD_REQUIRED.md)

| Source | Reason |
|---|---|
| `pexels_35087073` | `EGRESS_POLICY_DENIED: proxy refused CONNECT tunnel: Tunnel connection failed: 403 Forbidden` |
| `pexels_8052834` | `EGRESS_POLICY_DENIED: proxy refused CONNECT tunnel: Tunnel connection failed: 403 Forbidden` |
| `pexels_8053646` | `EGRESS_POLICY_DENIED: proxy refused CONNECT tunnel: Tunnel connection failed: 403 Forbidden` |
| `pexels_8053653` | `EGRESS_POLICY_DENIED: proxy refused CONNECT tunnel: Tunnel connection failed: 403 Forbidden` |
| `pexels_35087074` | `EGRESS_POLICY_DENIED: proxy refused CONNECT tunnel: Tunnel connection failed: 403 Forbidden` |

## 4. Actual video metadata

No files acquired, so no metadata could be measured.

## 5. Frame and contact-sheet observations

No frames could be inspected, because no footage was acquired. **No classification is offered for any candidate.** Producing ACCEPT/MANUAL_REVIEW/REJECT verdicts from page titles would be a guess, and the point of this step is to judge the actual pixels.

## 6. Best candidate clips

None available — no footage has been acquired or inspected yet.

## 7. Licensing status

| Source | Terms URL | Status | Verified by a human |
|---|---|---|---|
| `pexels_35087073` | https://www.pexels.com/license/ | `LICENSE_REVIEW_REQUIRED` | no |
| `pexels_8052834` | https://www.pexels.com/license/ | `LICENSE_REVIEW_REQUIRED` | no |
| `pexels_8053646` | https://www.pexels.com/license/ | `LICENSE_REVIEW_REQUIRED` | no |
| `pexels_8053653` | https://www.pexels.com/license/ | `LICENSE_REVIEW_REQUIRED` | no |
| `pexels_35087074` | https://www.pexels.com/license/ | `LICENSE_REVIEW_REQUIRED` | no |

All 5 source(s) are `LICENSE_REVIEW_REQUIRED`. The licence text was not retrievable from this environment, so it has not been read. This tooling therefore makes **no** statement about what the licence permits — in particular it does not treat free-to-download as cleared for redistribution or commercial dataset use. A human must read each terms URL and record the outcome in `dataset_v1/sources.json`.

Source media, extracted frames and contact sheets are git-ignored. Only measured facts (hashes, ffprobe output, scores) are committed, so no footage is redistributed through this repository.

## 8. Exact next action

1. Download the 5 file(s) listed in [`MANUAL_DOWNLOAD_REQUIRED.md`](MANUAL_DOWNLOAD_REQUIRED.md) using each provider's own download button, and save them to `dataset_v1/incoming/`.
2. Run `python -m eval dataset-v1`. Hashing, ffprobe metadata, frame measurement, contact sheets, classification and this report all regenerate automatically.
3. Read each licence terms URL and set `license_status` in `dataset_v1/sources.json`.
4. Review the contact sheets and confirm or overrule each MANUAL_REVIEW verdict.

Alternative to step 1, if you would rather not download by hand: have the environment's egress allowlist extended to the provider hosts (`www.pexels.com`, `videos.pexels.com`), then re-run `python -m eval dataset-v1`. The acquisition path is implemented and will fetch the files unattended.

A GitHub-hosted route was also investigated and rejected on licensing, not reachability -- see `GITHUB_DATASET_ACQUISITION_REPORT.md`. Public research repositories did yield real badminton video, but frame inspection showed all of it to be BWF World Tour and Olympic broadcast footage with no licence covering the video, so none of it entered the dataset.

Switching provider will not help from this sandbox. At the time this report was generated, `archive.org`, `commons.wikimedia.org`, `upload.wikimedia.org`, `openverse.org`, `pixabay.com` and `www.youtube.com` were each probed and each returned the same 403 CONNECT denial. The allowlist here covers package registries and source control, not media hosts, so either the allowlist changes or a human downloads the files.

M5 was not modified. M6 was not started. No M5.5 evaluation was run, and no real-world accuracy has been measured or claimed.
