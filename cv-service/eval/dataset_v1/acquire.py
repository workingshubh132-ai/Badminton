"""Automated acquisition for dataset v1 candidate sources.

Rules this module obeys, without exception:

* Only ordinary HTTP GETs against the public page and any direct asset URL that page
  itself exposes.
* No authentication, DRM, paywall, rate-limit, robots or access-control circumvention.
* A proxy/egress denial is reported, never retried against an alternate route.

If a source cannot be acquired legitimately it is recorded as blocked with the exact
reason, and the run continues with the remaining sources.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .sources import Source, dataset_root, ensure_layout, load_registry, save_registry

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) badminton-m5.5-dataset-tooling/1.0"
TIMEOUT_SECONDS = 30

# Blocked-reason codes
EGRESS_POLICY_DENIED = "EGRESS_POLICY_DENIED"
NO_DIRECT_ASSET_EXPOSED = "NO_DIRECT_ASSET_EXPOSED"
REQUIRES_AUTHENTICATION = "REQUIRES_AUTHENTICATION"
NETWORK_ERROR = "NETWORK_ERROR"

_ASSET_RE = re.compile(r'https://[\w.-]*pexels\.com/[^\s"\'<>\\]+?\.mp4[^\s"\'<>\\]*')
_OG_VIDEO_RE = re.compile(
    r'<meta[^>]+property=["\']og:video["\'][^>]+content=["\']([^"\']+)["\']', re.I
)


@dataclass
class FetchResult:
    ok: bool
    body: str = ""
    reason_code: str = ""
    reason_detail: str = ""


def fetch_page(url: str) -> FetchResult:
    """GET a page through the environment's normal HTTP path."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return FetchResult(ok=True, body=response.read().decode(charset, "replace"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403, 407):
            # 403/407 from the egress proxy is an organisation policy denial; 401 from
            # the origin means the asset sits behind authentication. Neither is ours to
            # work around.
            code = EGRESS_POLICY_DENIED if exc.code in (403, 407) else REQUIRES_AUTHENTICATION
            return FetchResult(
                ok=False,
                reason_code=code,
                reason_detail=f"HTTP {exc.code} {exc.reason}",
            )
        return FetchResult(
            ok=False, reason_code=NETWORK_ERROR, reason_detail=f"HTTP {exc.code} {exc.reason}"
        )
    except urllib.error.URLError as exc:
        detail = str(exc.reason)
        if "403" in detail or "CONNECT" in detail.upper() or "tunnel" in detail.lower():
            return FetchResult(
                ok=False,
                reason_code=EGRESS_POLICY_DENIED,
                reason_detail=f"proxy refused CONNECT tunnel: {detail}",
            )
        return FetchResult(ok=False, reason_code=NETWORK_ERROR, reason_detail=detail)
    except Exception as exc:  # noqa: BLE001 - report, never crash the batch
        return FetchResult(ok=False, reason_code=NETWORK_ERROR, reason_detail=repr(exc))


def extract_asset_urls(html: str) -> list[str]:
    """Collect direct video asset URLs the page itself exposes.

    Looks at inline asset links, the og:video meta tag, and JSON-LD contentUrl. Only
    URLs already present in the page response are returned -- nothing is guessed or
    constructed.
    """
    urls: list[str] = list(_ASSET_RE.findall(html))
    urls += [u for u in _OG_VIDEO_RE.findall(html) if ".mp4" in u]

    for blob in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.S | re.I,
    ):
        try:
            payload = json.loads(blob)
        except json.JSONDecodeError:
            continue
        for node in payload if isinstance(payload, list) else [payload]:
            if isinstance(node, dict) and isinstance(node.get("contentUrl"), str):
                urls.append(node["contentUrl"])

    seen, unique = set(), []
    for url in urls:
        url = url.replace("&amp;", "&")
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def _asset_sort_key(url: str) -> int:
    """Rank candidate assets so the highest advertised resolution is preferred."""
    heights = [int(h) for h in re.findall(r"_(\d{3,4})p?[_.]", url)]
    heights += [int(h) for h in re.findall(r"[?&]h=(\d{3,4})", url)]
    return max(heights) if heights else 0


def download_asset(url: str, destination: Path) -> FetchResult:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as handle:
                while chunk := response.read(1 << 20):
                    handle.write(chunk)
        return FetchResult(ok=True)
    except Exception as exc:  # noqa: BLE001
        if destination.exists():
            destination.unlink()
        return FetchResult(ok=False, reason_code=NETWORK_ERROR, reason_detail=repr(exc))


def acquire_source(source: Source, root: Path) -> Source:
    """Attempt one source. Mutates and returns the source record."""
    print(f"\n[{source.source_id}] {source.source_url}")

    page = fetch_page(source.source_url)
    if not page.ok:
        source.automated_download_possible = False
        source.automated_download_blocked_reason = f"{page.reason_code}: {page.reason_detail}"
        print(f"  BLOCKED  {source.automated_download_blocked_reason}")
        return source

    assets = extract_asset_urls(page.body)
    if not assets:
        source.automated_download_possible = False
        source.automated_download_blocked_reason = (
            f"{NO_DIRECT_ASSET_EXPOSED}: page returned {len(page.body)} bytes but exposed "
            "no direct .mp4 asset URL in markup, og:video or JSON-LD"
        )
        print(f"  BLOCKED  {source.automated_download_blocked_reason}")
        return source

    best = sorted(assets, key=_asset_sort_key, reverse=True)[0]
    destination = root / "incoming" / source.expected_filename
    print(f"  asset    {best}")

    result = download_asset(best, destination)
    if not result.ok:
        source.automated_download_possible = False
        source.automated_download_blocked_reason = (
            f"{result.reason_code}: asset URL exposed but fetch failed -- {result.reason_detail}"
        )
        print(f"  BLOCKED  {source.automated_download_blocked_reason}")
        return source

    source.automated_download_possible = True
    source.automated_download_blocked_reason = ""
    source.downloaded_filename = destination.name
    print(f"  OK       {destination} ({destination.stat().st_size:,} bytes)")
    return source


def acquire_all(root: str | Path | None = None) -> list[Source]:
    dataset = dataset_root(root)
    ensure_layout(dataset)
    sources = load_registry(dataset)

    for source in sources:
        existing = dataset / "incoming" / source.expected_filename
        if existing.exists() and existing.stat().st_size > 0:
            source.downloaded_filename = existing.name
            if source.automated_download_possible is None:
                source.automated_download_possible = False
                source.automated_download_blocked_reason = (
                    "file supplied manually; automated acquisition not attempted"
                )
            print(f"\n[{source.source_id}] already present: {existing.name}")
            continue
        acquire_source(source, dataset)

    save_registry(dataset, sources)

    acquired = sum(1 for s in sources if s.downloaded_filename)
    print(f"\n{acquired}/{len(sources)} source(s) present in {dataset / 'incoming'}")
    return sources


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Acquire dataset v1 candidate footage.")
    parser.add_argument("--dataset-dir", default=None)
    args = parser.parse_args()
    acquire_all(args.dataset_dir)
    return 0
