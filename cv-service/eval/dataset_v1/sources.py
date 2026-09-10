"""Candidate source registry for dataset v1.

A source is a page we intend to obtain footage from. Nothing here asserts what a
provider's licence permits -- only where the licence text lives, so a human can read it.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Licence status vocabulary. These are *our* handling rules, not legal conclusions.
#   PERMITTED              -- licence text has been read and permits the intended use
#   REFERENCE_ONLY         -- licence text has been read and restricts use to reference
#   LICENSE_REVIEW_REQUIRED-- licence text has NOT been read/verified; default
PERMITTED = "PERMITTED"
REFERENCE_ONLY = "REFERENCE_ONLY"
LICENSE_REVIEW_REQUIRED = "LICENSE_REVIEW_REQUIRED"


@dataclass
class Source:
    source_id: str
    source_url: str
    provider: str
    license_terms_url: str
    license_status: str = LICENSE_REVIEW_REQUIRED
    license_verified: bool = False
    page_title_as_published: str = ""
    expected_filename: str = ""
    notes: str = ""

    # Populated by acquire.py
    automated_download_possible: bool | None = None
    automated_download_blocked_reason: str = ""
    downloaded_filename: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _s(source_id: str, url: str, title: str, filename: str) -> Source:
    return Source(
        source_id=source_id,
        source_url=url,
        provider="Pexels",
        license_terms_url="https://www.pexels.com/license/",
        license_status=LICENSE_REVIEW_REQUIRED,
        license_verified=False,
        page_title_as_published=title,
        expected_filename=filename,
        notes=(
            "Licence text was NOT retrievable from this environment; status stays "
            "LICENSE_REVIEW_REQUIRED until a human reads the terms URL."
        ),
    )


# The five candidate pages supplied for dataset v1. Titles are recorded as published by
# the provider and are explicitly NOT used to judge footage content -- see inspect.py.
SOURCES: list[Source] = [
    _s(
        "pexels_35087073",
        "https://www.pexels.com/video/boys-playing-badminton-on-indoor-court-35087073/",
        "Boys Playing Badminton on Indoor Court",
        "pexels_35087073.mp4",
    ),
    _s(
        "pexels_8052834",
        "https://www.pexels.com/video/badminton-player-playing-indoors-8052834/",
        "Badminton Player Playing Indoors",
        "pexels_8052834.mp4",
    ),
    _s(
        "pexels_8053646",
        "https://www.pexels.com/video/people-playing-badminton-8053646/",
        "People Playing Badminton",
        "pexels_8053646.mp4",
    ),
    _s(
        "pexels_8053653",
        "https://www.pexels.com/video/teammates-playing-badminton-8053653/",
        "Teammates Playing Badminton",
        "pexels_8053653.mp4",
    ),
    _s(
        "pexels_35087074",
        "https://www.pexels.com/video/dynamic-indoor-badminton-match-with-youths-35087074/",
        "Dynamic Indoor Badminton Match with Youths",
        "pexels_35087074.mp4",
    ),
]


def dataset_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    # repo_root/dataset_v1 -- this file lives at repo_root/cv-service/eval/dataset_v1/
    return Path(__file__).resolve().parents[3] / "dataset_v1"


def ensure_layout(root: Path) -> None:
    for sub in ("incoming", "contact_sheets", "frames", "metadata", "analysis"):
        (root / sub).mkdir(parents=True, exist_ok=True)


def load_registry(root: Path) -> list[Source]:
    path = root / "sources.json"
    if not path.exists():
        return [Source(**s.to_dict()) for s in SOURCES]
    raw = json.loads(path.read_text())
    return [Source(**entry) for entry in raw["sources"]]


def save_registry(root: Path, sources: list[Source]) -> None:
    path = root / "sources.json"
    path.write_text(
        json.dumps(
            {
                "schema": "dataset_v1.sources/1",
                "license_status_vocabulary": [
                    PERMITTED,
                    REFERENCE_ONLY,
                    LICENSE_REVIEW_REQUIRED,
                ],
                "sources": [s.to_dict() for s in sources],
            },
            indent=2,
        )
        + "\n"
    )
