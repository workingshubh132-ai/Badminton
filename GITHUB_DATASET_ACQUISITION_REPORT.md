# GitHub Dataset Acquisition Report

_Generated 2026-09-11 · M5.5 dataset sourcing · investigation only, no M5.5 evaluation run_

## Headline

Three GitHub repositories were inspected. Video bytes **were** legitimately retrievable
from two of them, so the technical objective succeeded: real badminton footage reached
this machine through ordinary anonymous `git clone` of public repositories, with nothing
bypassed.

**But every single video turned out to be professional broadcast footage** — BWF World
Tour events and the Paris 2024 Olympic Games — and none of it carries a licence that
covers the video. **Nothing has been added to the evaluation dataset, and I do not
recommend using any of it.**

This was established by looking at the frames, not by reading filenames. The branding is
plainly visible in the contact sheets.

---

## 1. Candidates inspected

| # | Repository | Repo licence | Video assets in repo | Bytes retrievable |
|---|---|---|---|---|
| 1 | [Ning-D/BFMD](https://github.com/Ning-D/BFMD) | **none** | 2 × `.mp4` | yes |
| 2 | [kwyoke/Badminton-hit-detection](https://github.com/kwyoke/Badminton-hit-detection) | **none** | none | n/a |
| 3 | [ShreyBarve/Deep-learning-based-temporal-analysis-of-badminton-gameplay](https://github.com/ShreyBarve/Deep-learning-based-temporal-analysis-of-badminton-gameplay) | MIT (code) | 5 × `.mp4` (4 unique) | yes |

Access method: anonymous shallow `git clone` over HTTPS of public repositories, via this
session's git proxy, with `GIT_LFS_SKIP_SMUDGE=1`. No authentication, no paywall, no DRM,
no rate-limit evasion, no YouTube download. None of the video was Git-LFS backed, so the
real bytes are present in the repositories themselves.

### Repository 2 has no video at all

`kwyoke/Badminton-hit-detection` is 204 MB, but that is a 94 MB ResNet checkpoint plus
notebooks and PNG screenshots. There is no video of any format in the tree. Its rally
videos are distributed via Google Drive, outside GitHub, and its README describes them as
"professional broadcast singles videos". Nothing to acquire here.

---

## 2. Candidates successfully acquired

Six files were retrieved and inspected (4 unique clips from repo 3 — `rally_2.mp4` and
`match_4_rally_49047.mp4` are byte-identical, SHA-256 `15d92def…`, so the duplicate was
dropped).

**All six are now held in `dataset_v1/quarantine_license_review/`, deliberately *outside*
the `incoming/` candidate path, so `python -m eval dataset-v1` will not pick them up.**
Raw video is git-ignored from every staging path and none of it is committed.

## 3. Exact provenance

Provenance below is what is *visible in the frames*, not what the filename claims.

| File | Repo path | Event identified from frames |
|---|---|---|
| `bfmd_demo_petronas.mp4` | `Ning-D/BFMD` → `demo_petronas.mp4` | BWF **PETRONAS Malaysia Open** — PETRONAS/HSBC/YONEX/Etihad boards, "KUALA LUMPUR" signage, courtside officials |
| `bfmd_demo_all_petronasm.mp4` | `Ning-D/BFMD` → `demo_all_petronasm.mp4` | Same match, with burned-in pose/box/caption overlays |
| `shreybarve_rally_1.mp4` | repo 3 → `rally_1.mp4` | **BWF World Superseries** — "BWF WORLD SUPERSERIES" painted on court, MetLife/YONEX/UNISYS/NTT boards, scoreboard "JORGENSEN" |
| `shreybarve_rally_2.mp4` | repo 3 → `rally_2.mp4` (= `match_4_rally_49047.mp4`) | **Paris 2024 Olympic Games** — Olympic rings, "PARIS 2024" branding throughout |
| `shreybarve_rally_3.mp4` | repo 3 → `rally_3.mp4` | BWF **Kumamoto Masters Japan** — TOYOTA/YONEX/HSBC boards, "KUMAMOTO" signage |
| `shreybarve_rally_4.mp4` | repo 3 → `rally_4.mp4` | Same match as `rally_1`, with burned-in overlays |

## 4. Licence status

| File | Repo licence | Separate video/data licence | Status |
|---|---|---|---|
| `bfmd_demo_petronas.mp4` | none | none | `LICENSE_REVIEW_REQUIRED` |
| `bfmd_demo_all_petronasm.mp4` | none | none | `LICENSE_REVIEW_REQUIRED` |
| `shreybarve_rally_1.mp4` | MIT (code) | none | `LICENSE_REVIEW_REQUIRED` |
| `shreybarve_rally_2.mp4` | MIT (code) | none | `LICENSE_REVIEW_REQUIRED` |
| `shreybarve_rally_3.mp4` | MIT (code) | none | `LICENSE_REVIEW_REQUIRED` |
| `shreybarve_rally_4.mp4` | MIT (code) | none | `LICENSE_REVIEW_REQUIRED` |

**BFMD has no licence file at all.** Its README states, verbatim:

> "Videos are not redistributed for copyright reasons — they can be re-downloaded from the
> official [BWF TV](https://www.youtube.com/c/bwftv) YouTube channel with the provided
> `download_youtube.py` script"

So the dataset's own authors disclaim redistributing video on copyright grounds. The two
demo clips sitting in the repository are the same broadcast material that policy is about.

**Repo 3's MIT licence covers "the Software".** Its copyright line is `Copyright (c) 2025
ShreyBarve` — a claim over the author's own work, not over Olympic or BWF broadcast
footage they did not produce. The README never mentions the videos: no source, no
attribution, no separate asset terms. An MIT `LICENSE` file in a repository does not and
cannot license third-party broadcast content that happens to sit next to the code.

---

## 5. Metadata (measured with ffprobe, not transcribed)

| File | Resolution | FPS | Duration | Codec | Size | SHA-256 |
|---|---|---|---|---|---|---|
| `bfmd_demo_petronas.mp4` | 1280×720 | 30.0 | 5.333 s | h264 | 481,202 B | `4d9a6c589776…` |
| `bfmd_demo_all_petronasm.mp4` | 1280×720 | 30.0 | 5.333 s | h264 | 878,665 B | `847948c565e2…` |
| `shreybarve_rally_1.mp4` | 1920×1080 | 16.59 | 4.150 s | h264 | 1,165,438 B | `e3977f4fe855…` |
| `shreybarve_rally_2.mp4` | 640×360 | 30.0 | 5.400 s | mpeg4 | 930,717 B | `15d92def3ac5…` |
| `shreybarve_rally_3.mp4` | 854×480 | 30.0 | 6.433 s | mpeg4 | 1,533,156 B | `5944113b2110…` |
| `shreybarve_rally_4.mp4` | 1920×1080 | 16.59 | 4.100 s | mpeg4 | 1,705,647 B | `cc34dcfcdad8…` |

Total unique footage: **~25 seconds**, against a 2–5 minute target. Even setting licensing
aside, this is an order of magnitude short.

Note the odd frame rates on `rally_1`/`rally_4` (16.59 fps) — these are re-encoded
excerpts, not original broadcast cadence.

## 6. Content inspection

Contact sheets (raw and detector-annotated) are in `dataset_v1/contact_sheets/`,
git-ignored. Per-frame measurements are in `dataset_v1/analysis/`.

| File | Real badminton | Format | Court | Camera | Continuous | Overlays | M5 suitability |
|---|---|---|---|---|---|---|---|
| `bfmd_demo_petronas.mp4` | yes | **singles** | full, excellent | static (0.05 px) | yes, no cuts | clean | technically ideal |
| `bfmd_demo_all_petronasm.mp4` | yes | singles | full | static (0.06 px) | yes | **pose + boxes + captions burned in** | unusable |
| `shreybarve_rally_1.mp4` | yes | **singles** | full, excellent | static (0.10 px) | yes | clean | technically good, 4.15 s |
| `shreybarve_rally_2.mp4` | yes | **singles** | full | static (0.00 px) | yes | clean | 360p — below CV floor |
| `shreybarve_rally_3.mp4` | yes | **singles** | full | static (0.04 px) | yes | clean | technically OK, 480p |
| `shreybarve_rally_4.mp4` | yes | singles | full | static (0.09 px) | yes | **court lines, mini-map, keypoints, shuttle trail burned in** | unusable |

Two findings worth recording:

**The automated classifier got the format wrong on all six.** It reported "doubles" with a
median of 4.5–7 people per frame (max 15). The annotated contact sheets show why: it is
boxing **seated line judges and crowd in the stands**, not extra players. Every clip is
singles — two players on court. This is the over-counting counterpart to the
under-counting weakness already recorded in `DATASET_V1_SELECTION_REPORT.md`, and it is a
concrete demonstration that the triage person count must not be trusted without looking at
the annotated sheet. The verdicts in this report are the human reading, not the
classifier's.

**Two clips carry burned-in annotations.** `bfmd_demo_all_petronasm` and `rally_4` have
pose skeletons, bounding boxes, shuttle trajectories and drawn court lines rendered into
the pixels. These would corrupt an M5 evaluation outright — the court detector could latch
onto drawn overlay lines instead of real court markings, and the person detector onto drawn
boxes. They are unusable for validation at any licence status.

## 7. Recommended clips

**None.**

The footage quality is genuinely excellent — static broadcast cameras, full court, clean
lines, good lighting, continuous rallies, exactly the singles material M5.5 wants. Were
licensing not an issue, `bfmd_demo_petronas.mp4`, `shreybarve_rally_1.mp4` and
`shreybarve_rally_3.mp4` would be the three to take.

They are not recommended, for two independent reasons, either of which is sufficient:

1. **Licensing.** All six are professional broadcast footage with no licence covering the
   video. The brief for this task was explicitly to avoid copyrighted BWF footage.
   Retrieving that same footage from a GitHub mirror rather than from YouTube does not
   change its copyright status — only the delivery channel.
2. **Volume.** ~25 seconds of unique usable footage against a 2–5 minute target, of which
   only ~16 s is clean and ≥480p.

## 8. Legal and provenance uncertainty

- **No claim of any commercial or redistribution right is made for any of this footage.**
- Every file is `LICENSE_REVIEW_REQUIRED`. I have not read a licence that grants rights to
  the video, because for these files no such licence exists in either repository.
- The repository licences that do exist (MIT on repo 3) cover source code. Whether they
  extend to bundled third-party broadcast video is exactly the assumption this task was
  told not to make, and on the evidence they do not.
- "Internal evaluation only" is a narrower and more defensible use than building a
  redistributable dataset, and that distinction may matter. **That is a judgement for you,
  not for me** — I am not making a fair-use/fair-dealing determination, and nothing here
  should be read as one.
- If you decide the internal-evaluation use is acceptable, the three clean clips are in
  `dataset_v1/quarantine_license_review/` and move into `dataset_v1/incoming/` with one
  `mv`. I have deliberately not made that move.

## 9. Recommended next action

Neither this route nor the Pexels route has produced usable footage, for different
reasons: Pexels is blocked by our own egress policy, GitHub is reachable but only carries
broadcast material. The routes that remain, best first:

1. **Unblock a stock provider.** Add `www.pexels.com` and `videos.pexels.com` to the egress
   allowlist. The five Pexels candidates are stock footage with a real licence to read, and
   the acquisition path is already implemented and will run unattended.
2. **Record your own footage.** A phone on a tripod at a club court produces 2–5 minutes of
   unambiguously-owned singles footage in one session — no licence question at all, and it
   matches the actual deployment domain better than broadcast does. For validating a system
   meant to analyse an athlete's own matches, this is arguably the *better* evaluation set,
   not merely the safer one.
3. **Approach a rights-holder.** Local clubs, coaching academies or university teams will
   often share match video for research with a short written permission.

Broadcast footage also differs systematically from the target domain: elevated fixed
camera, telephoto compression, on-screen graphics. Validating M5 on it would measure
accuracy on a domain the product does not actually operate in.

---

**Status**: investigation and inspection complete. No footage acquired into the evaluation
dataset. M5 not modified, M6 not started, no M5.5 evaluation run, no real-world accuracy
measured or claimed.
