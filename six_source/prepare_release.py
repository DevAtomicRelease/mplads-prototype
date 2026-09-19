"""Build, validate and activate a new versioned release (audit item 4).

Builds the whole dataset into a fresh, timestamped release directory under
`six_source/releases/`, then runs patterns, offline A/B validation and the Excel
workbook against that release. Only if every step succeeds is the release ACTIVATED
by copying its artifacts into `local/`. The previous `local/` is left untouched if any
step fails (the previous working release is retained), and review records
(`reviews.sqlite3`) are never overwritten, so they survive a rebuild and stay tied to
their own dataset version.

Raw source files are read only; they are never modified. Nothing is pushed or uploaded.

    python prepare_release.py
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import patterns
import validate
import workbook
from build import build as build_dataset
from common import AS_OF, COHORTS, ROOT

HERE = Path(__file__).parent
LOCAL = HERE / "local"
RELEASES = HERE / "releases"
PRESERVE = {"reviews.sqlite3"}  # review records are independent of analytical outputs


def activate(rel: Path, local: Path, version: str):
    local.mkdir(parents=True, exist_ok=True)
    for src in rel.iterdir():
        if src.is_file() and src.name not in PRESERVE:
            shutil.copy2(src, local / src.name)
    (local / "active_release.json").write_text(
        json.dumps({"release": rel.name, "version": version,
                    "activated": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n",
        encoding="utf-8")


def main(input_dir: Path = ROOT / "Dataset", as_of: str = AS_OF):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = RELEASES / stamp
    cohorts = list(COHORTS)
    print(f"Preparing release {stamp} in an isolated directory (previous release retained until this succeeds).", flush=True)
    meta = build_dataset(input_dir, rel, as_of=as_of, cohorts=cohorts)  # 21 reconciliation checks; fails closed
    if not meta.get("all_checks_passed"):
        raise SystemExit("Release build failed reconciliation; previous release retained.")
    print("Building patterns, A/B validation and Excel workbook for the release...", flush=True)
    (rel / "DATA_PATTERNS.md").write_text(patterns.report(rel), encoding="utf-8")
    validate.build(rel)
    workbook.build(rel)
    for required in ("Work_Features.csv", "audit.json", "ab_metrics.json", "MPLADS_Review.xlsx"):
        if not (rel / required).is_file():
            raise SystemExit(f"Release is incomplete ({required} missing); not activating. Previous release retained.")
    print(f"Validation complete. Activating release {stamp} (review records preserved).", flush=True)
    activate(rel, LOCAL, meta["version"])
    print(f"ACTIVATED release {stamp}. Version {meta['version']}.", flush=True)
    return meta


if __name__ == "__main__":
    main()
