# Manual Download Required

_Generated 2026-09-12T07:36:06+00:00_

**5 of 5 candidate sources could not be acquired automatically.**

Nothing in this list was blocked by a provider access control. No authentication, paywall, DRM, rate limit or robots restriction was encountered or circumvented.

## pexels_35087073

- **Source page**: https://www.pexels.com/video/boys-playing-badminton-on-indoor-court-35087073/
- **Provider**: Pexels
- **Licence terms**: https://www.pexels.com/license/
- **Licence status**: `LICENSE_REVIEW_REQUIRED`

**Exact reason automated retrieval is not possible**  
`EGRESS_POLICY_DENIED: proxy refused CONNECT tunnel: Tunnel connection failed: 403 Forbidden`

This session's network egress proxy refused the CONNECT tunnel with HTTP 403. The host is not on the allowlist for this environment. This is a restriction on *our* sandbox, not an access control on the provider: no login, paywall, DRM or rate limit was encountered, and nothing was bypassed.

**Normal user action required**  
Open the page in a normal browser on your own machine and use the provider's own Free Download button. Choose the highest resolution offered.

**Where to put the resulting file**  
`dataset_v1/incoming/pexels_35087073.mp4`

Any filename works -- the inspector reads every video in `incoming/` -- but using the name above keeps the file matched to its source record and licence metadata.

---

## pexels_8052834

- **Source page**: https://www.pexels.com/video/badminton-player-playing-indoors-8052834/
- **Provider**: Pexels
- **Licence terms**: https://www.pexels.com/license/
- **Licence status**: `LICENSE_REVIEW_REQUIRED`

**Exact reason automated retrieval is not possible**  
`EGRESS_POLICY_DENIED: proxy refused CONNECT tunnel: Tunnel connection failed: 403 Forbidden`

This session's network egress proxy refused the CONNECT tunnel with HTTP 403. The host is not on the allowlist for this environment. This is a restriction on *our* sandbox, not an access control on the provider: no login, paywall, DRM or rate limit was encountered, and nothing was bypassed.

**Normal user action required**  
Open the page in a normal browser on your own machine and use the provider's own Free Download button. Choose the highest resolution offered.

**Where to put the resulting file**  
`dataset_v1/incoming/pexels_8052834.mp4`

Any filename works -- the inspector reads every video in `incoming/` -- but using the name above keeps the file matched to its source record and licence metadata.

---

## pexels_8053646

- **Source page**: https://www.pexels.com/video/people-playing-badminton-8053646/
- **Provider**: Pexels
- **Licence terms**: https://www.pexels.com/license/
- **Licence status**: `LICENSE_REVIEW_REQUIRED`

**Exact reason automated retrieval is not possible**  
`EGRESS_POLICY_DENIED: proxy refused CONNECT tunnel: Tunnel connection failed: 403 Forbidden`

This session's network egress proxy refused the CONNECT tunnel with HTTP 403. The host is not on the allowlist for this environment. This is a restriction on *our* sandbox, not an access control on the provider: no login, paywall, DRM or rate limit was encountered, and nothing was bypassed.

**Normal user action required**  
Open the page in a normal browser on your own machine and use the provider's own Free Download button. Choose the highest resolution offered.

**Where to put the resulting file**  
`dataset_v1/incoming/pexels_8053646.mp4`

Any filename works -- the inspector reads every video in `incoming/` -- but using the name above keeps the file matched to its source record and licence metadata.

---

## pexels_8053653

- **Source page**: https://www.pexels.com/video/teammates-playing-badminton-8053653/
- **Provider**: Pexels
- **Licence terms**: https://www.pexels.com/license/
- **Licence status**: `LICENSE_REVIEW_REQUIRED`

**Exact reason automated retrieval is not possible**  
`EGRESS_POLICY_DENIED: proxy refused CONNECT tunnel: Tunnel connection failed: 403 Forbidden`

This session's network egress proxy refused the CONNECT tunnel with HTTP 403. The host is not on the allowlist for this environment. This is a restriction on *our* sandbox, not an access control on the provider: no login, paywall, DRM or rate limit was encountered, and nothing was bypassed.

**Normal user action required**  
Open the page in a normal browser on your own machine and use the provider's own Free Download button. Choose the highest resolution offered.

**Where to put the resulting file**  
`dataset_v1/incoming/pexels_8053653.mp4`

Any filename works -- the inspector reads every video in `incoming/` -- but using the name above keeps the file matched to its source record and licence metadata.

---

## pexels_35087074

- **Source page**: https://www.pexels.com/video/dynamic-indoor-badminton-match-with-youths-35087074/
- **Provider**: Pexels
- **Licence terms**: https://www.pexels.com/license/
- **Licence status**: `LICENSE_REVIEW_REQUIRED`

**Exact reason automated retrieval is not possible**  
`EGRESS_POLICY_DENIED: proxy refused CONNECT tunnel: Tunnel connection failed: 403 Forbidden`

This session's network egress proxy refused the CONNECT tunnel with HTTP 403. The host is not on the allowlist for this environment. This is a restriction on *our* sandbox, not an access control on the provider: no login, paywall, DRM or rate limit was encountered, and nothing was bypassed.

**Normal user action required**  
Open the page in a normal browser on your own machine and use the provider's own Free Download button. Choose the highest resolution offered.

**Where to put the resulting file**  
`dataset_v1/incoming/pexels_35087074.mp4`

Any filename works -- the inspector reads every video in `incoming/` -- but using the name above keeps the file matched to its source record and licence metadata.

---

## After you have downloaded the files

Run one command. Everything downstream is automatic:

```bash
python -m eval dataset-v1
```

That hashes each file, reads its real metadata with ffprobe, decodes and measures frames, writes contact sheets to `dataset_v1/contact_sheets/`, classifies each candidate, and regenerates `DATASET_V1_SELECTION_REPORT.md`.

## Licence check you must do yourself

Read the terms URL for each source before the footage is used for anything beyond local evaluation, and record the outcome in `dataset_v1/sources.json` by setting `license_status` to `PERMITTED` or `REFERENCE_ONLY` and `license_verified` to `true`. Until then every source stays `LICENSE_REVIEW_REQUIRED`. Free to download is not the same as cleared for a redistributed or commercial dataset, and this tooling makes no claim either way.
