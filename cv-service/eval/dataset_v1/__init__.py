"""Dataset v1: acquire real badminton footage and triage it for the M5.5 gate.

One command runs the whole thing:

    python -m eval dataset-v1

Acquire what is legitimately downloadable, measure every file actually present,
generate contact sheets, classify each candidate, and write both reports.
"""

from __future__ import annotations

from pathlib import Path

from .acquire import acquire_all
from .inspect_candidates import ACCEPT, MANUAL_REVIEW, REJECT, inspect_all
from .report import write_reports
from .sources import dataset_root, ensure_layout

__all__ = [
    "run",
    "acquire_all",
    "inspect_all",
    "write_reports",
    "ACCEPT",
    "MANUAL_REVIEW",
    "REJECT",
]


def run(root: str | Path | None = None, skip_acquire: bool = False) -> None:
    dataset = dataset_root(root)
    ensure_layout(dataset)

    if skip_acquire:
        print("=== acquisition skipped ===")
    else:
        print("=== acquiring candidate sources ===")
        acquire_all(dataset)

    print("\n=== inspecting acquired footage ===")
    records = inspect_all(dataset)

    print("\n=== writing reports ===")
    write_reports(dataset)

    if records:
        for record in records:
            print(f"  {record['metadata']['filename']}: {record['classification']['verdict']}")
