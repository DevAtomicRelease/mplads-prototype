"""Check that the frozen A/B experiment reproduces byte-identical artifacts."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
names = ["metrics.json", "AB_Validation_Report.md", "actual_test_scores.csv", "controlled_benchmark.csv", "split_manifest.csv"]


def hashes():
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}


before = hashes()
completed = subprocess.run([sys.executable, str(root / "run_ab_validation.py")], capture_output=True, text=True, check=True)
after = hashes()
assert before == after, "The repeated experiment produced different artifact content"
metrics = json.loads((root / "metrics.json").read_text(encoding="utf-8"))
assert all(metrics["checks"].values())
for result in metrics["synthetic_benchmark"]["budgets"]:
    assert result["review_count"] == round(metrics["synthetic_benchmark"]["rows"] * result["review_fraction"])
    for model in ["a", "b"]:
        row = result[model]
        assert row["recovered"] + row["unchanged_cases_selected"] == result["review_count"]
        assert sum(v["recovered"] for v in row["scenario_recovery"].values()) == row["recovered"]
result = {"byte_identical_on_rerun": True, "all_experiment_assertions_passed": True,
          "budget_and_scenario_totals_reconcile": True, "artifact_sha256": after}
(root / "reproducibility_check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
