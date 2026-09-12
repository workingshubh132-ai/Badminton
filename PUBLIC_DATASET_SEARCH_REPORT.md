# Public Dataset Search Report — badminton footage, licence-first

_Search date: 2026-09-12. Filed as `PUBLIC_DATASET_SEARCH_REPORT.md`; the brief named
`GITHUB/PUBLIC_DATASET_SEARCH_REPORT.md`, and this covers both the four public sources
and the GitHub avenue._

## Outcome

**Zero videos acquired. Nothing was added to the dataset.**

Not because the footage does not exist — Pixabay alone indexes hundreds of badminton
clips — but because this environment cannot reach any of the four sources, and the one
route that *can* fetch bytes only ever turns up broadcast footage.

No acquisition is claimed, no licence is asserted as verified, and no frames were
accepted sight-unseen.

---

## 1. Route availability (tested, not assumed)

Two days ago these hosts were blocked. I re-probed rather than trusting that, because
the environment could have changed. It has not.

| Route | Status | Evidence |
|---|---|---|
| `curl` via egress proxy | **BLOCKED** for all four sources | `403` to `CONNECT`, logged per host in the proxy's own failure log |
| `WebFetch` | **BLOCKED** | `EGRESS_BLOCKED` on `commons.wikimedia.org` |
| `WebSearch` | **WORKS** | Returned real results throughout |
| `git clone` of public GitHub repos | **WORKS** | Cloned 4 repos this session |

Hosts confirmed denied by policy, each with a logged `403 CONNECT`:

`commons.wikimedia.org`, `upload.wikimedia.org`, `api.wikimedia.org`, `pixabay.com`,
`cdn.pixabay.com`, `www.pexels.com`, `videos.pexels.com`, `openverse.org`,
`api.openverse.org`, `search.creativecommons.org`, `drive.google.com`

Control: `api.github.com` returned `200` in the same run, so the proxy works — these are
targeted policy denials, not a broken network. This is **our** egress allowlist, not any
provider's access control. No login, paywall, DRM or rate limit was encountered, and
nothing was bypassed.

**The consequence for this task:** WebSearch returns titles, URLs and summaries. It does
not return video bytes, and it cannot open a licence page. So for all four sources I can
identify candidates but can neither verify a licence at its source nor download a file.

---

## 2. Source-by-source findings

### 1. Wikimedia Commons — no gameplay video found

Searches surfaced only SVG court diagrams, static photographs, and footwork *animations*
("steps used to reach the front right and rear left corners in singles play"). Those
animations are instructional graphics, not match footage with a visible court and players.

Commons is the source with the cleanest licensing (CC BY-SA / public domain, stated
per-file), so it remains the best place to look if the allowlist changes — but nothing in
these results meets the target.

- Category pages could not be enumerated: `WebFetch` on
  `commons.wikimedia.org/wiki/Category:Videos_of_badminton` was blocked, so I cannot say
  whether such a category exists or what is in it.

### 2. Pixabay — content exists, unreachable

This is the richest source by a wide margin. Search listings report:

| Listing | Clips reported |
|---|---|
| `pixabay.com/videos/search/badminton%20game/` | 761+ |
| `pixabay.com/videos/search/sport%20badminton/` | 1,579+ |
| `pixabay.com/videos/search/badminton%20player/` | 167+ |
| `pixabay.com/videos/search/badminton%20rally/` | 35+ |

Search snippets describe the content as royalty-free with no attribution required.
**I am not recording that as the licence.** That phrasing comes from a search engine's
summary of Pixabay's own marketing copy, not from the Pixabay Content Licence text, which
I could not open. The actual licence carries conditions (notably on redistributing files
as-is, and on identifiable people) that a snippet does not capture. Status stays
`LICENSE_REVIEW_REQUIRED` for every Pixabay item.

I also could not obtain **individual** video page URLs — only search-listing URLs — because
resolving a listing to specific clips requires fetching the page.

### 3. Pexels — unreachable, previously documented

Blocked identically. The five specific candidates from the earlier hunt remain listed in
`MANUAL_DOWNLOAD_REQUIRED.md` with per-source download instructions; nothing has changed.

### 4. Openverse / CC Search — wrong medium

Openverse indexes **images and audio**. Its own description is "indexing and providing
Creative Commons licensed photos and audio files". It is not a video index, so it is a
dead end for this target regardless of reachability.

---

## 3. GitHub avenue — reachable, and the reason it still failed

GitHub is the only reachable host that can serve video bytes, so I searched it properly
and cloned every plausible candidate.

| Repository | Licence file | Video in repo | Finding |
|---|---|---|---|
| [Tharanpreeth4/Badminton_Dataset](https://github.com/Tharanpreeth4/Badminton_Dataset) | **none** | none | 11 JPEG frames + CSV. Frames inspected: **London 2012 Olympics broadcast** |
| [SanderP99/Badminton-Data](https://github.com/SanderP99/badminton-data) | `LICENSE.md` | none | BWF world *ranking* CSVs, not video |
| [qilimk/VideoBadminton](https://github.com/qilimk/VideoBadminton) | **none** | none | Data hosted on Google Drive (also blocked) |
| [HuangYuHsien/S2DoublesDataset](https://github.com/HuangYuHsien/S2DoublesDataset) | **none** | none | README: "videos could be fetched from BWF YouTube channel" |
| Ning-D/BFMD | none | 2 clips | Previously quarantined: BWF Petronas Malaysia Open |
| kwyoke/Badminton-hit-detection | none | none | Previously checked: no video |
| ShreyBarve/Deep-learning-…-badminton-gameplay | MIT (code) | 5 clips | Previously quarantined: BWF + Paris 2024 Olympics |

The one repository that contained any imagery, I inspected rather than inferred from its
name. The frames carry Olympic rings and "London 2012" signage throughout — Olympic
broadcast, squarely inside the exclusion.

**The pattern across seven repositories is consistent:** public badminton CV datasets are
built from BWF and Olympic broadcast, because that is the footage that exists in volume
with consistent camera geometry. They also overwhelmingly ship annotations and point at
YouTube or Drive for the video, precisely because the authors know they cannot
redistribute it.

---

## 4. Candidate record

The brief asks for direct asset URL, creator, exact licence, licence URL, resolution, FPS,
duration, codec, file size and reuse terms per candidate. **For the four public sources I
can supply none of these**, because every field requires either opening the page or
downloading the file, and both routes are blocked. Recording guessed values would be
fabrication.

What is actually known:

| Field | Wikimedia | Pixabay | Pexels | Openverse |
|---|---|---|---|---|
| Source URL | reachable by name only | search listings only | 5 known page URLs | n/a |
| Direct asset URL | — | — | — | — |
| Creator | — | — | — | — |
| Exact licence | unread | unread | unread | n/a |
| Licence URL | commons.wikimedia.org/wiki/Commons:Licensing | pixabay.com/service/license-summary/ | pexels.com/license/ | — |
| Resolution / FPS / duration / codec / size | — | — | — | — |
| Commercial/internal reuse permitted? | **unknown** | **unknown** | **unknown** | — |
| Attribution required? | **unknown** | **unknown** | **unknown** | — |
| Status | `LICENSE_REVIEW_REQUIRED` | `LICENSE_REVIEW_REQUIRED` | `LICENSE_REVIEW_REQUIRED` | n/a |

Licence URLs above are where the terms live, not statements of what they say.

---

## 5. Files placed

| Destination | Files |
|---|---|
| `cv-service/eval/dataset_v1/incoming/` | **none** |
| `cv-service/eval/dataset_v1/quarantine_license_review/` | **none added** |

Nothing was acquired, so nothing was placed. The six previously-quarantined broadcast
clips were neither touched nor re-examined; they remain outside the candidate path with
unchanged checksums.

A note on paths: the harness reads from `dataset_v1/incoming/` at the repo root.
`cv-service/eval/dataset_v1/` is the Python package that implements the tooling, so
dropping footage inside it would place data in a source package. Both paths are
git-ignored against video either way. If you prefer the package-relative path, the
harness accepts `--dataset-dir`.

---

## 6. Answers to the closing questions

**1. How many legitimate videos were actually acquired?**
**Zero.** No file was downloaded, and none was placed in `incoming/` or quarantine.

**2. Exact licences**
None, because no licence text was read. Every candidate is `LICENSE_REVIEW_REQUIRED`.
The only licence file encountered across seven repositories was `LICENSE.md` on a
*ranking-data* repo and MIT on a code repo — and a code licence is not a video licence.

**3. Do they meet the M5.5 minimum?**
No. The minimum is 3 source videos, 5–8 clips, 2–5 minutes, ≥150 annotated frames,
≥100 person-instances and **≥30 annotated bystanders**. Against that: 0 videos,
0 seconds, 0 clips.

**4. Which requirement remains the bottleneck?**
**Network egress, not licensing and not availability.** Suitable, clearly-licensed footage
demonstrably exists — Pixabay indexes hundreds of clips under a real licence that a human
can read in seconds. This environment simply cannot reach it. Licensing is the *second*
bottleneck and only bites on the one reachable host: GitHub serves bytes, but everything
it holds is broadcast.

Behind both sits a requirement neither source can satisfy well: **≥30 annotated
bystanders**. Stock clips are usually a clean court with two players and nobody else, so
even a successful Pixabay download may not validate the participant classifier. Broadcast
has crowds in abundance — and is excluded.

**5. If zero usable footage was found, explain why**
Three independent reasons, each sufficient on its own:

- **All four sources are blocked by our own egress policy** (`403 CONNECT`, verified this
  session, GitHub control passing). Not a provider restriction; nothing to legitimately
  work around.
- **Openverse is the wrong medium** — images and audio, not video.
- **Every public GitHub badminton dataset is broadcast-derived**, which the brief excludes.
  Seven repositories checked, seven confirmed broadcast, absent, or non-video. The frames
  I could inspect were London 2012 Olympics.

---

## 7. What would actually unblock this

1. **Allowlist `pixabay.com` + `cdn.pixabay.com`** (and optionally
   `commons.wikimedia.org` + `upload.wikimedia.org`). Pixabay has the volume; Commons has
   the cleanest per-file licensing. The acquisition path in `eval/dataset_v1/acquire.py`
   is implemented and will run unattended once a host is reachable.
2. **Download by hand** from the Pixabay listings above, then
   `python -m eval ingest … --real-footage --license … --license-verified-by "<name>"`.
   The harness is ready end to end (M5.5.2).
3. **Record your own.** A phone on a tripod at a club court is the only option that
   satisfies every requirement at once — including the bystanders, which stock footage
   usually lacks — with unambiguous ownership and no licence question. It also matches the
   deployment domain far better than either broadcast or stock.

**Status:** no footage acquired, no licence verified, no M5.5 evaluation run, M6 still
blocked. Gate remains `NO_REAL_WORLD_EVIDENCE`.
