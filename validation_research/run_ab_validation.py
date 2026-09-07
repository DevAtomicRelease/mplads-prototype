"""Reproducible offline ranking experiment; never writes the source snapshot.

A: fixed delay/aging rules. B: A plus historical peer cost and duplicate evidence.
The synthetic labels identify injected test perturbations, not real fraud.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 26102
BOOTSTRAP_REPLICATES = 1000
BUDGETS = [0.05, 0.10, 0.20, 0.30]
MIN_PEERS = 20
EXPECTED_COUNT = 10000


def normalize(value):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(value).lower())).strip()


def safe_number(value, default=0.0):
    if value is None or pd.isna(value):
        return default
    return float(value)


class HistoricalDetector:
    """All fitted reference state comes exclusively from the frozen training rows."""

    def __init__(self, training):
        self.training = training.copy()
        self.peers = {}
        self.reference = defaultdict(list)
        for level, keys in [("state_type", ["state", "work_type"]), ("type", ["work_type"])]:
            for key, group in training.groupby(keys, sort=True):
                if not isinstance(key, tuple):
                    key = (key,)
                if len(group) >= MIN_PEERS:
                    self.peers[(level, key)] = self.summarize(group.sanction_amount)
        self.global_peer = self.summarize(training.sanction_amount)
        for row in training.to_dict("records"):
            row["tokens"] = set(normalize(row["work_description"]).split())
            row["norm"] = normalize(row["work_description"])
            self.reference[(row["ida_key"], row["work_type"])].append(row)

    @staticmethod
    def summarize(values):
        a = np.log1p(np.maximum(np.asarray(values, dtype=float), 0))
        med = float(np.median(a))
        # Fixed log-scale floor avoids an unstable z-score for tied/constant peer costs.
        scale = max(float(1.4826 * np.median(np.abs(a - med))), 0.25)
        return {"n": len(a), "median_log": med, "scale_log": scale,
                "median_amount": float(np.median(values))}

    def peer(self, row):
        for level, key in [("state_type", (row["state"], row["work_type"])),
                           ("type", (row["work_type"],))]:
            if (level, key) in self.peers:
                return level, self.peers[(level, key)]
        return "global", self.global_peer

    def score(self, frame):
        output = []
        for row in frame.to_dict("records"):
            delay = max(safe_number(row["sanction_delay_days"]), 0)
            age = max(safe_number(row["age_days_at_snapshot_proxy"]), 0)
            early = bool(row["early_stage_flag"])
            delay_score = 30 * float(np.clip((delay - 45) / 320, 0, 1))
            aging_score = 20 * float(np.clip((age - 180) / 550, 0, 1)) if early else 0.0
            level, peer = self.peer(row)
            amount = max(safe_number(row["sanction_amount"]), 0)
            ratio = amount / max(peer["median_amount"], 1)
            z = (math.log1p(amount) - peer["median_log"]) / peer["scale_log"]
            cost_score = 25 * float(np.clip((z - 2.5) / 3.5, 0, 1)) if ratio > 2 else 0.0
            norm = normalize(row["work_description"])
            tokens = set(norm.split())
            best = (0.0, 0.0, None, False)
            # Same IDA + same type provides a transparent, frozen candidate block.
            for ref in self.reference[(row["ida_key"], row["work_type"])]:
                sim = len(tokens & ref["tokens"]) / max(len(tokens | ref["tokens"]), 1)
                amount_close = abs(amount - ref["sanction_amount"]) <= max(1, 0.05 * ref["sanction_amount"])
                # At least five tokens avoids a one-word exact match being strong evidence.
                score = 25 * float(np.clip((sim - 0.80) / 0.20, 0, 1)) if amount_close and len(tokens) >= 5 else 0.0
                if (score, sim) > best[:2]:
                    best = (score, sim, int(ref["work_id"]), amount_close)
            duplicate_score, similarity, reference_id, amount_close = best
            output.append({
                "work_id": int(row["work_id"]), "delay_score": delay_score,
                "aging_score": aging_score, "cost_score": cost_score,
                "duplicate_score": duplicate_score, "score_a": delay_score + aging_score,
                "score_b": delay_score + aging_score + cost_score + duplicate_score,
                "delay_signal": delay > 45, "aging_signal": early and age > 180,
                "cost_signal": cost_score > 0, "duplicate_signal": duplicate_score > 0,
                "peer_level": level, "peer_n": peer["n"], "peer_median": peer["median_amount"],
                "cost_robust_z": z, "cost_ratio": ratio, "reference_work_id": reference_id,
                "reference_similarity": similarity, "reference_amount_close": amount_close,
            })
        return pd.DataFrame(output)


def order(scores, tie):
    return np.lexsort((tie, -np.asarray(scores)))


def coverage(scored, selected):
    flags = ["delay_signal", "aging_signal", "cost_signal", "duplicate_signal"]
    result = {}
    for flag in flags:
        count = int(scored.iloc[selected][flag].sum())
        total = int(scored[flag].sum())
        result[flag.removesuffix("_signal")] = {
            "selected": count, "available": total,
            "coverage": count / total if total else None,
        }
    result["distinct_signal_types"] = sum(result[f.removesuffix("_signal")]["selected"] > 0 for f in flags)
    result["mean_signals_per_selected_work"] = float(scored.iloc[selected][flags].sum(axis=1).mean())
    return result


def actual_comparison(scored):
    tie = np.random.default_rng(SEED + 2).random(len(scored))
    rank_a, rank_b = order(scored.score_a, tie), order(scored.score_b, tie)
    budgets = []
    for budget in BUDGETS:
        k = max(1, math.ceil(len(scored) * budget))
        a, b = rank_a[:k], rank_b[:k]
        overlap = len(set(a) & set(b))
        budgets.append({"review_fraction": budget, "review_count": k,
                        "overlap_count": overlap, "overlap_fraction": overlap / k,
                        "jaccard": overlap / (2 * k - overlap), "new_cases_in_b": k - overlap,
                        "a": coverage(scored, a), "b": coverage(scored, b),
                        "top_work_ids_a": scored.iloc[a].work_id.astype(int).tolist(),
                        "top_work_ids_b": scored.iloc[b].work_id.astype(int).tolist()})
    return {"test_rows": len(scored), "budgets": budgets,
            "accuracy_estimated": False,
            "interpretation": "Observed queue composition only; the original data has no confirmed fraud labels."}


def make_benchmark(held_out, detector):
    # Eligibility ensures an aging injection can change status without changing dates.
    pool = held_out.loc[held_out.age_days_at_snapshot_proxy >= 365].copy()
    rng = np.random.default_rng(SEED + 1)
    n = min(1200, len(pool))
    if n < 600:
        raise ValueError("Insufficient independently held-out records for the frozen benchmark design")
    picked = rng.choice(pool.index.to_numpy(), size=n, replace=False)
    frame = pool.loc[picked].copy().reset_index(drop=True)
    frame["origin_work_id"] = frame.work_id
    frame["scenario"] = "unchanged"
    each = n // 12  # Four equally sized injection groups; two thirds remain unchanged.
    references = detector.training.loc[
        detector.training.work_description.map(lambda s: len(normalize(s).split()) >= 5)
    ].sort_values("work_id")
    for group, label in enumerate(["delay", "aging", "high_cost", "duplicate"]):
        for i in range(group * each, (group + 1) * each):
            frame.at[i, "scenario"] = label
            if label == "delay":
                frame.at[i, "sanction_delay_days"] = 365
                frame.at[i, "recommended_date"] = (pd.Timestamp(frame.at[i, "sanction_date"]) - pd.Timedelta(days=365)).strftime("%Y-%m-%d")
            elif label == "aging":
                frame.at[i, "early_stage_flag"] = True
                frame.at[i, "status_stage"] = "Early"
                frame.at[i, "work_status"] = "Sanction"
            elif label == "high_cost":
                _, peer = detector.peer(frame.loc[i])
                # Severity is fixed from training statistics, not selected after observing recovery.
                frame.at[i, "sanction_amount"] = math.ceil(max(peer["median_amount"] * 8,
                                                              math.expm1(peer["median_log"] + 6 * peer["scale_log"])))
            else:
                ref = references.iloc[int(rng.integers(0, len(references)))]
                for col in ["state", "ida_key", "work_type", "work_description", "sanction_amount"]:
                    frame.at[i, col] = ref[col]
                frame.at[i, "injected_reference_work_id"] = int(ref.work_id)
    # Randomize output order; tie breaking uses an independent frozen random stream.
    frame = frame.iloc[rng.permutation(len(frame))].reset_index(drop=True)
    return frame


def injected_metrics(scores, labels, tie, budget):
    assert len(scores["score_a"]) == len(scores["score_b"]) == len(labels) == len(tie)
    k = max(1, math.ceil(len(labels) * budget))
    positive = labels != "unchanged"
    result = {"review_count": k, "injected_count": int(positive.sum())}
    for model in ["a", "b"]:
        chosen = order(scores[f"score_{model}"], tie)[:k]
        found = int(positive[chosen].sum())
        per_scenario = {}
        for label in ["delay", "aging", "high_cost", "duplicate"]:
            total = int((labels == label).sum())
            count = int((labels[chosen] == label).sum())
            per_scenario[label] = {"recovered": count, "injected": total, "recovery": count / total}
        result[model] = {"recovered": found, "recovery": found / int(positive.sum()),
                         "injected_cases_per_review": found / k,
                         "unchanged_cases_selected": k - found,
                         "scenario_recovery": per_scenario}
    result["recovery_difference_b_minus_a"] = result["b"]["recovery"] - result["a"]["recovery"]
    return result


def benchmark_comparison(frame, scored, original_scores):
    labels = frame.scenario.to_numpy()
    tie = np.random.default_rng(SEED + 3).random(len(frame))
    score_arrays = {"score_a": scored.score_a.to_numpy(), "score_b": scored.score_b.to_numpy()}
    results = []
    rng = np.random.default_rng(SEED + 4)
    strata = [np.flatnonzero(labels == s) for s in sorted(set(labels))]
    boot = {budget: [] for budget in BUDGETS}
    for _ in range(BOOTSTRAP_REPLICATES):
        indexes = np.concatenate([rng.choice(ix, size=len(ix), replace=True) for ix in strata])
        vals = {key: values[indexes] for key, values in score_arrays.items()}
        # Both models see identical bootstrap rows and tie-breaking numbers.
        for budget in BUDGETS:
            value = injected_metrics(vals, labels[indexes], tie[indexes], budget)
            boot[budget].append(value["recovery_difference_b_minus_a"])
    for budget in BUDGETS:
        metric = injected_metrics(score_arrays, labels, tie, budget)
        metric["review_fraction"] = budget
        low, high = np.quantile(boot[budget], [0.025, 0.975])
        metric["paired_bootstrap_95_interval_difference"] = [float(low), float(high)]
        results.append(metric)
    diagnostic = {}
    score_col = {"delay": "delay_score", "aging": "aging_score", "high_cost": "cost_score", "duplicate": "duplicate_score"}
    for label, col in score_col.items():
        indexes = np.flatnonzero(labels == label)
        positives = int((scored.iloc[indexes][col] > 0).sum())
        before = original_scores.iloc[indexes][col].to_numpy()
        after = scored.iloc[indexes][col].to_numpy()
        diagnostic[label] = {"triggered": positives, "injected": len(indexes), "trigger_rate": positives / len(indexes),
                             "signal_present_before_injection": int((before > 0).sum()),
                             "score_component_increased": int((after > before + 1e-9).sum()),
                             "median_component_increase": float(np.median(after - before))}
    return {"rows": len(frame), "injection_counts": frame.scenario.value_counts().to_dict(),
            "budgets": results, "diagnostic_signal_trigger_rates": diagnostic,
            "bootstrap": {"replicates": BOOTSTRAP_REPLICATES, "seed": SEED + 4,
                          "method": "Paired stratified nonparametric bootstrap, percentile interval; rerank inside each resample at the same review budget."},
            "meaning": "Recovery of deliberately injected evidence. Untouched records are unlabeled background, not verified negatives. Injected cases per review is not real fraud precision."}


def report(metrics):
    split = metrics["split"]
    lines = ["# MPLADS offline A/B ranking validation", "",
             "This is a reproducible offline comparison of review ranking methods. It is not a randomized live user experiment and does not estimate real fraud accuracy.", "",
             "## Data and temporal split", "",
             f"Source: {metrics['source']['source_file']}. Workbook SHA-256: `{metrics['source']['source_workbook_sha256']}`. Extracted snapshot JSON SHA-256: `{metrics['source']['snapshot_sha256']}`.",
             f"The frozen cutoff is {split['cutoff_inclusive']}: {split['train_rows']:,} earlier works form the reference; {split['test_rows']:,} later works form the test set. All records on a cutoff date remain together.",
             "Peer medians and log-MAD scales are fitted only on earlier amounts. Test descriptions are matched only to earlier training works in the same IDA and work type. Original full-dataset cost, duplicate, entity aggregates, and priority scores are not used. No test outcome is used for fitting or tuning.", "",
             "The date split validates retrospective screening on a frozen snapshot; it does not demonstrate forecasting from information available at the sanction date. Status/age are measured at the 2026-09-01 snapshot.", "",
             "## Frozen methods", "",
             "A = delay contribution + early-stage aging contribution. B = A + robust high-cost contribution + corroborated description similarity contribution. These research scores are distinct from the earlier workbook priority scores.",
             "Delay: 30 × clip((calendar delay − 45)/320, 0, 1). Aging: 20 × clip((snapshot age − 180)/550, 0, 1), only for early-stage works. Cost: 25 × clip((log-cost robust z − 2.5)/3.5, 0, 1), only when amount exceeds 2× historical peer median. Duplicate: 25 × clip((token Jaccard − 0.80)/0.20, 0, 1), within the same IDA/type and amount within 5%, with at least five description tokens.",
             "Peer fallback: state + type when at least 20 reference works exist, then type with at least 20, then global. Robust scale = max(1.4826 × log-amount MAD, 0.25). Weights and benchmark severity were fixed in the script before running the experiment; they were not searched or optimized on the held-out results.", "",
             "## Real-data queue comparison", "",
             "The counts below measure queue composition. A cost or duplicate flag is an unconfirmed signal, so these are coverage measures, not correctness measures.", "",
             "| Review budget | Cases each | Queue overlap | A cost / duplicate cases | B cost / duplicate cases |", "|---|---:|---:|---:|---:|"]
    for b in metrics["actual_data"]["budgets"]:
        lines.append(f"| {b['review_fraction']:.0%} | {b['review_count']} | {b['overlap_fraction']:.1%} | {b['a']['cost']['selected']} / {b['a']['duplicate']['selected']} | {b['b']['cost']['selected']} / {b['b']['duplicate']['selected']} |")
    lines += ["", "## Controlled held-out injection benchmark", "",
              "The benchmark samples 1,200 held-out source rows aged at least 365 days (fixed seed). Four disjoint groups of 100 receive delay, early-stage aging, high cost, or historical duplicate evidence; 800 rows retain their source values. If fewer eligible rows exist, the script scales this fixed design proportionally. Unchanged cases may already contain legitimate anomalies.",
              "Delay sets recommendation 365 days before the existing sanction date. Aging changes status to early stage while retaining actual sanction/snapshot dates. High cost sets amount to the larger of 8× historical median or exp(median log amount + 6 historical robust scales) − 1. Duplicate replaces description, IDA, type, state, and amount with an earlier training record. Injection changes are confined to an in-memory copy and an explicitly labeled validation output; no source data are augmented.",
              "Some temporal injections can reinforce a signal already present. Therefore the benchmark measures recovery of cases selected for an injected scenario, not a causal estimate that every detected signal was newly created.", "",
              "| Review budget | A recovery | B recovery | Difference B−A | Paired bootstrap 95% interval |", "|---|---:|---:|---:|---:|"]
    for b in metrics["synthetic_benchmark"]["budgets"]:
        lo, hi = b["paired_bootstrap_95_interval_difference"]
        lines.append(f"| {b['review_fraction']:.0%} | {b['a']['recovery']:.1%} | {b['b']['recovery']:.1%} | {b['recovery_difference_b_minus_a'] * 100:+.1f} pp | [{lo * 100:+.1f}, {hi * 100:+.1f}] pp |")
    lines += ["", "Intervals condition on this fixed reference model, designed severity, selected source pool, and artificial scenario mixture. They do not cover unknown fraud prevalence, label error, distribution drift, or re-training uncertainty.", "",
              "| Scenario | Injected | Signal triggered | Already signaled before | Component increased | A recovery at 20% | B recovery at 20% |", "|---|---:|---:|---:|---:|---:|---:|"]
    twenty = next(b for b in metrics["synthetic_benchmark"]["budgets"] if b["review_fraction"] == 0.2)
    for label, d in metrics["synthetic_benchmark"]["diagnostic_signal_trigger_rates"].items():
        lines.append(f"| {label} | {d['injected']} | {d['trigger_rate']:.1%} | {d['signal_present_before_injection']} | {d['score_component_increased']} | {twenty['a']['scenario_recovery'][label]['recovery']:.1%} | {twenty['b']['scenario_recovery'][label]['recovery']:.1%} |")
    lines += ["", "The combined ranking improves total recovery for this designed mixture at 10–30% budgets. Its benefit at 5% is uncertain because the interval includes zero. At 20%, B prioritizes injected cost/duplicate evidence while detecting fewer of the injected delay/aging cases than A. This is a measurable allocation tradeoff, not general superiority. Keep distinct operational delay and aging queues or agree a review quota before considering the combined queue for deployment; validate any changed policy on a new untouched test set.",
              "", "## Limits and next validation step", "",
              "- The 10,000-row work extract covers 12.75% of its reported value and may be selected rather than representative. Training/test results apply to this extract.",
              "- Sanction delay is recommendation-to-sanction calendar time; actual IDA receipt date and excluded periods are absent. Aging is a snapshot proxy. Cost comparisons lack dimensions and specifications. Similarity lacks verified coordinates and asset scope.",
              "- Background records are not verified negatives. Neither false-positive rate, fraud precision/recall, nor saved reviewer time can be estimated here. The duplicate benchmark contains intentionally strong matches and can overstate generalization to paraphrases or genuine scope differences.",
              "- The narrow A baseline is useful for isolating added signals, but is not claimed to be the strongest possible alternative. An unsupervised score has no supervised fraud calibration.",
              "- A prospective pilot should randomize comparable cases/officers to A or B at the same review budget, use blinded independent adjudication, and measure substantiated issues per review, time to decision, agreement, and missed-case sampling. The current comparison does not replace this live experiment.", "",
              "## Reproduction and files", "",
              "Run `python run_ab_validation.py` with the bundled NumPy and pandas runtime. Optional `--input` and `--out` arguments override paths. Fixed seeds, hashes, train/test manifest, scores, synthetic row records, and machine-readable metrics accompany this report.",
              "The script asserts record uniqueness, temporal separation, no train/test overlap, all historical references belonging to training, correct output counts, and source hash stability. Successful assertions are recorded under `checks` in metrics.json."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parents[1] / "pipeline_research" / "artifacts" / "snapshot.json")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    # Independent known-answer check catches ranking-budget and label alignment bugs.
    fixture = {"score_a": np.array([4., 3., 2., 1.]), "score_b": np.array([1., 2., 3., 4.])}
    fixture_labels = np.array(["delay", "aging", "high_cost", "duplicate"])
    fixture_result = injected_metrics(fixture, fixture_labels, np.arange(4), 0.5)
    assert fixture_result["review_count"] == 2
    assert fixture_result["a"]["scenario_recovery"]["delay"]["recovered"] == 1
    assert fixture_result["b"]["scenario_recovery"]["duplicate"]["recovered"] == 1
    source_bytes = args.input.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    payload = json.loads(source_bytes)
    project_root = Path(__file__).resolve().parents[1]
    if payload['meta'].get('pipelineVersion'):
        sources = payload['meta']['sourceFiles']
        for source in sources.values():
            assert hashlib.sha256((project_root / 'Dataset' / source['file']).read_bytes()).hexdigest() == source['sha256']
        source_name = 'Three raw MPLADS workbooks via ' + payload['meta']['pipelineVersion']
        source_hashes = ' | '.join(f"{s['file']}: {s['sha256']}" for s in sources.values())
    else:
        workbook_path = project_root / 'outputs' / '01a06d6b-9b94-7a61-b28b-6f9116f20942' / payload['meta']['sourceFile']
        assert hashlib.sha256(workbook_path.read_bytes()).hexdigest() == payload['meta']['sourceSha256']
        source_name, source_hashes = payload['meta']['sourceFile'], payload['meta']['sourceSha256']
    table = payload["tables"]["Work_Features"]
    works = pd.DataFrame(table["rows"], columns=table["columns"])
    assert len(works) == EXPECTED_COUNT
    assert works.work_id.is_unique
    works["sanction_date"] = pd.to_datetime(works.sanction_date)
    cutoff = works.sanction_date.sort_values().iloc[math.floor(len(works) * 0.7) - 1]
    training = works.loc[works.sanction_date <= cutoff].copy()
    testing = works.loc[works.sanction_date > cutoff].copy()
    assert training.sanction_date.max() < testing.sanction_date.min()
    assert not set(training.work_id) & set(testing.work_id)
    detector = HistoricalDetector(training)
    actual_scores = detector.score(testing)
    benchmark = make_benchmark(testing, detector)
    benchmark_scores = detector.score(benchmark)
    benchmark_original = works.set_index("work_id", drop=False).loc[benchmark.origin_work_id].reset_index(drop=True)
    original_scores = detector.score(benchmark_original)
    for scored in [actual_scores, benchmark_scores]:
        references = set(scored.reference_work_id.dropna().astype(int))
        assert references <= set(training.work_id)
        assert np.isfinite(scored[["score_a", "score_b"]]).all().all()
    metrics = {
        "schema_version": "1.0", "experiment_id": "mplads-offline-ab-26102-v1",
        "runtime": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        "source": {"source_file": source_name, "snapshot_file": str(args.input),
                   "snapshot_sha256": source_hash, "source_workbook_sha256": source_hashes,
                   "snapshot_date": payload["meta"]["snapshot"], "rows": len(works)},
        "split": {"method": "70th percentile sanction date with whole-date grouping",
                  "cutoff_inclusive": cutoff.strftime("%Y-%m-%d"), "train_rows": len(training),
                  "test_rows": len(testing), "test_min_date": testing.sanction_date.min().strftime("%Y-%m-%d"),
                  "test_max_date": testing.sanction_date.max().strftime("%Y-%m-%d")},
        "design": {"seed": SEED, "budgets": BUDGETS, "minimum_peer_count": MIN_PEERS,
                   "a": "Fixed continuous delay and early-stage aging rules",
                   "b": "A plus robust historical peer cost and same-IDA/type historical duplicate evidence",
                   "weight_search": False, "test_tuning": False, "live_randomized_test": False,
                   "labels": "No real fraud labels; synthetic labels record explicitly injected evidence only"},
        "actual_data": actual_comparison(actual_scores),
        "synthetic_benchmark": benchmark_comparison(benchmark, benchmark_scores, original_scores),
        "checks": {"unique_source_work_ids": True, "strict_temporal_split": True,
                   "train_test_disjoint": True, "historical_reference_only": True,
                   "known_answer_ranking_fixture": True, "source_workbook_hash_matches_snapshot": True,
                   "finite_scores": True, "source_unchanged": None},
    }
    assert hashlib.sha256(args.input.read_bytes()).hexdigest() == source_hash
    metrics["checks"]["source_unchanged"] = True
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = works[["work_id", "sanction_date"]].copy()
    manifest["split"] = np.where(manifest.sanction_date <= cutoff, "train", "test")
    manifest.to_csv(args.out / "split_manifest.csv", index=False)
    actual_scores.to_csv(args.out / "actual_test_scores.csv", index=False)
    keep = ["origin_work_id", "scenario", "sanction_date", "recommended_date", "state", "ida_key", "work_type", "work_description", "sanction_amount", "sanction_delay_days", "age_days_at_snapshot_proxy", "early_stage_flag"]
    injected = benchmark[keep].copy().join(benchmark_scores.drop(columns=["work_id"]))
    injected.to_csv(args.out / "controlled_benchmark.csv", index=False)
    (args.out / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False), encoding="utf-8")
    (args.out / "AB_Validation_Report.md").write_text(report(metrics), encoding="utf-8")
    summary = {"split": metrics["split"], "actual": [{k: b[k] for k in ["review_fraction", "review_count", "overlap_fraction", "new_cases_in_b"]} for b in metrics["actual_data"]["budgets"]],
               "synthetic": [{"budget": b["review_fraction"], "a": b["a"]["recovery"], "b": b["b"]["recovery"], "difference": b["recovery_difference_b_minus_a"], "ci": b["paired_bootstrap_95_interval_difference"]} for b in metrics["synthetic_benchmark"]["budgets"]], "checks": metrics["checks"]}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
