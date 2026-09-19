"""Independent rebuild + artifact-hash comparison for the six_source build.

Rebuilds the whole dataset into a SEPARATE release directory (default
`six_source/reproduced/`, git-ignored) using the same frozen source contract and
snapshot date as the current `local/` build, then compares every exported CSV's
SHA-256. Exit code 0 and "REPRODUCIBLE" only if all artifacts are byte-identical.

    python reproduce.py
    python reproduce.py --out release_2026-09-16      # a named release directory
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build import build
from common import COHORTS, ROOT

HERE = Path(__file__).parent


def main(local: Path, out: Path, input_dir: Path):
    if not (local / "audit.json").is_file():
        raise SystemExit("No local build to compare against — run build.py first.")
    meta = json.loads((local / "audit.json").read_text(encoding="utf-8"))
    as_of = meta["as_of"]
    cohorts = meta.get("cohorts", list(COHORTS))
    print(f"Rebuilding cohorts {cohorts} as of {as_of} into {out} ...", flush=True)
    build(input_dir, out, as_of=as_of, cohorts=cohorts)
    a = json.loads((local / "artifact_hashes.json").read_text(encoding="utf-8"))
    b = json.loads((out / "artifact_hashes.json").read_text(encoding="utf-8"))
    # Compare the build artifacts (keys the fresh rebuild produced); ancillary files
    # such as validate.py's ab_*.csv are not build outputs and are not compared.
    keys = sorted(b)
    mismatch = [k for k in keys if a.get(k) != b[k]]
    for k in keys:
        print(("  OK   " if a.get(k) == b.get(k) else "  DIFF ") + k)
    from datetime import datetime, timezone
    report = {
        "reproducible": not mismatch,
        "artifacts": {k: {"local": a.get(k), "rebuilt": b[k], "match": a.get(k) == b[k]} for k in keys},
        "generated": datetime.now(timezone.utc).isoformat(),
        "as_of": as_of, "cohorts": cohorts, "version": meta.get("version"),
        "source_fingerprint": meta.get("source_fingerprint"), "pipeline_sha256": meta.get("pipeline_sha256"),
        "common_sha256": meta.get("common_sha256"), "release_dir": str(out),
    }
    (local / "reproducibility.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if mismatch:
        raise SystemExit(f"REPRODUCIBILITY FAILED: {len(mismatch)} artifact(s) differ: {mismatch}")
    print(f"REPRODUCIBLE: all {len(keys)} artifacts byte-identical to {local}. Wrote reproducibility.json.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", type=Path, default=HERE / "local")
    parser.add_argument("--out", type=Path, default=HERE / "reproduced")
    parser.add_argument("--input-dir", type=Path, default=ROOT / "Dataset")
    args = parser.parse_args()
    main(args.local, args.out, args.input_dir)
