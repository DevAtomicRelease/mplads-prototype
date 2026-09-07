"""Verify the frozen team release using only Python's standard library."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "TEAM_DATA_MANIFEST.json"
ARTIFACTS = [
    "Dataset/Works Sanctioned.xlsx",
    "Dataset/Allocated Limit for Honble MPs.xlsx",
    "Dataset/Amount consented for Calamity.xlsx",
    *[f"pipeline_research/artifacts/{name}" for name in (
        "snapshot.json", "audit.json", "QA_REPORT.md", "Work_Features.csv",
        "MP_Features.csv", "IDA_Features.csv", "Calamity_Features.csv",
        "Duplicate_Candidates.csv", "Feature_Dictionary.csv",
    )],
    "pipeline_research/workbook/verification.json",
    *[f"validation_research/{name}" for name in (
        "metrics.json", "actual_test_scores.csv", "controlled_benchmark.csv",
        "split_manifest.csv", "AB_Validation_Report.md", "reproducibility_check.json",
    )],
    "outputs/01a06d6b-9b94-7a61-b28b-6f9116f20942/MPLADS_Final_Core_Dataset_2026-09-06.xlsx",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def describe_files():
    static = ROOT / "mplads-prototype/dist/local"
    require((static / "index.html").is_file(), "The prebuilt local app is missing.")
    names = ARTIFACTS + [p.relative_to(ROOT).as_posix()
                         for p in static.rglob("*") if p.is_file()]
    files = []
    for name in sorted(names):
        path = ROOT / name
        require(path.is_file(), f"Missing release artifact: {name}")
        require(path.stat().st_size < 100 * 1024 * 1024,
                f"Release artifact exceeds 100 MiB: {name}")
        files.append({"path": name, "bytes": path.stat().st_size, "sha256": digest(path)})
    return files


def verify_lineage():
    snapshot_path = ROOT / "pipeline_research/artifacts/snapshot.json"
    snapshot = read_json(snapshot_path)
    for source in snapshot["meta"]["sourceFiles"].values():
        require(digest(ROOT / "Dataset" / source["file"]) == source["sha256"],
                f"Original workbook hash mismatch: {source['file']}")
    metrics_path = ROOT / "validation_research/metrics.json"
    metrics = read_json(metrics_path)
    require(metrics["source"]["snapshot_sha256"] == digest(snapshot_path),
            "A/B metrics refer to a different feature snapshot.")
    rerun = read_json(ROOT / "validation_research/reproducibility_check.json")
    require(rerun["all_equal"] and all(rerun["checks"].values()),
            "The saved independent rerun checks did not all pass.")
    require(rerun["core_snapshot_sha256"] == digest(snapshot_path),
            "The rerun record refers to a different feature snapshot.")
    require(rerun["ab_metrics_sha256"] == digest(metrics_path),
            "The rerun record refers to different A/B metrics.")
    workbook = read_json(ROOT / "pipeline_research/workbook/verification.json")
    require(workbook["all_passed"], "The saved final workbook checks did not pass.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true",
                        help="Maintainer only: record current verified release artifact hashes.")
    args = parser.parse_args()
    verify_lineage()
    files = describe_files()
    if args.write_manifest:
        payload = {
            "schema_version": 1,
            "release_date": "2026-09-07",
            "scope": "Owner-authorized real-data and ready-to-run local team release",
            "note": "Frozen artifact integrity, not a new A/B run or an independent source-authenticity assessment. Private review stores are excluded.",
            "hash_algorithm": "SHA-256",
            "files": files,
        }
        with MANIFEST.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    expected = read_json(MANIFEST)["files"]
    require(files == expected,
            "Released files differ from TEAM_DATA_MANIFEST.json. If you rebuilt, use the independent reproducibility checks for those new outputs.")
    print(json.dumps({"all_passed": True, "artifacts": len(files),
                      "total_bytes": sum(f["bytes"] for f in files),
                      "raw_sources_and_validation_lineage_match": True}, indent=2))


if __name__ == "__main__":
    main()
