"""Build, validate and activate a new versioned release (audit item 4).

Builds the whole dataset into a fresh, timestamped release directory under
`six_source/releases/`, then runs patterns, offline A/B validation and the Excel
workbook against that release. Only if every step succeeds is the release ACTIVATED
by atomically replacing one active-release pointer. Existing releases stay untouched if any
step fails (the previous working release is retained), and review records
(`reviews.sqlite3`) are never overwritten, so they survive a rebuild and stay tied to
their own dataset version.

Raw source files are read only; they are never modified. Nothing is pushed or uploaded.

    python prepare_release.py
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import patterns
import validate
import workbook
import forecast
from releases import activate, maintenance_lock, new_directory, seal
from build import build as build_dataset
from common import AS_OF, COHORTS, ROOT

HERE = Path(__file__).parent
LOCAL = HERE / "local"
RELEASES = HERE / "releases"
PRESERVE = {"reviews.sqlite3"}  # review records are independent of analytical outputs


def prepare(input_dir: Path = ROOT / "Dataset", as_of: str = AS_OF, local: Path = LOCAL):
    rel = new_directory(local)
    stamp = rel.name
    cohorts = list(COHORTS)
    print(f"Preparing release {stamp} in an isolated directory (previous release retained until this succeeds).", flush=True)
    meta = build_dataset(input_dir, rel, as_of=as_of, cohorts=cohorts)  # 21 reconciliation checks; fails closed
    if not meta.get("all_checks_passed"):
        raise SystemExit("Release build failed reconciliation; previous release retained.")
    print("Building patterns, A/B validation and Excel workbook for the release...", flush=True)
    (rel / "DATA_PATTERNS.md").write_text(patterns.report(rel), encoding="utf-8")
    validate.build(rel)
    forecast.build(rel)
    workbook.build(rel)
    for required in ("Work_Features.csv", "audit.json", "ab_metrics.json", "MPLADS_Review.xlsx"):
        if not (rel / required).is_file():
            raise SystemExit(f"Release is incomplete ({required} missing); not activating. Previous release retained.")
    print(f"Analyses complete. Running regression gate before activation of {stamp} (review records preserved).", flush=True)
    subprocess.run([sys.executable,str(HERE/"tests.py")],env={**os.environ,"MPLADS_DATA_DIR":str(rel),"PYTHONDONTWRITEBYTECODE":"1"},check=True,cwd=HERE)
    seal(rel)
    activate(rel, local)
    print(f"ACTIVATED release {stamp}. Version {meta['version']}.", flush=True)
    return meta


def main(input_dir: Path = ROOT / "Dataset", as_of: str = AS_OF, local: Path = LOCAL):
    with maintenance_lock(local):
        return prepare(input_dir, as_of, local)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", type=Path, default=LOCAL)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "Dataset")
    parser.add_argument("--as-of", default=AS_OF)
    args = parser.parse_args()
    main(args.input_dir, args.as_of, args.local)
