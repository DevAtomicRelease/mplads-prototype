"""Offline A/B screening comparison over the six_source build (PS 26102).

Two evidence layers, matching the frozen protocol, written to local/:
  1. Real retrospective queue comparison. Score every built work with a
     transparent baseline A (operational/payment screens only) and an
     enhanced B (A plus the cost-outlier and near-duplicate screens); at
     equal review budgets, report the queue overlap. No fraud accuracy,
     precision, or money-saved is claimed -- there are no adjudicated labels.
  2. Controlled mechanism benchmark. Wholly synthetic, seeded cases with
     known which-screen-fires labels test whether B recovers cost/duplicate
     cases that A ranks as zero. Labels mean "constructed review-worthy
     mechanism", not real fraud. A paired bootstrap gives a 95% interval.

Run after build.py:  python validate.py
Outputs: local/ab_metrics.json (served at /api/validation), AB_Report.md,
ab_actual_scores.csv, ab_controlled_benchmark.csv.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sqlite3
from pathlib import Path

import numpy as np

from common import SEED

HERE = Path(__file__).parent
# Baseline A: operational and payment screens present before the enhancement.
SHARED = ["pending_recommendation_45d_flag", "sanction_delay_45d_flag", "open_over_one_year_flag",
          "no_payment_three_months_flag", "paid_over_sanction_flag", "completion_over_sanction_flag",
          "repeat_payment_report_flag"]
# Enhancement in B: cost-outlier and near-duplicate screens.
EXTRA = ["high_cost_peer_flag", "high_similarity_review_flag"]
BUDGETS = [0.05, 0.10, 0.20, 0.30]
# (label, shared screens firing, extra screens firing). The last two are the
# families the enhancement is designed to recover -- A scores them zero.
FAMILIES = [
    ("Late sanction (>45 days)", 1, 0),
    ("Stalled open work (>1 year)", 1, 0),
    ("No payment after three months", 1, 0),
    ("Payment above sanction", 1, 0),
    ("Completion above sanction", 1, 0),
    ("Repeated payment report", 1, 0),
    ("Pending recommendation (>45 days)", 1, 0),
    ("Inflated cost vs peers (B only)", 0, 1),
    ("Near-duplicate description (B only)", 0, 1),
]
CONTEXTS = 300
NEGATIVES = 91  # per context; with 9 positives -> 100 cases per context


def tie_keys(labels):
    return np.array([int(hashlib.sha256(f"{SEED}:{x}".encode()).hexdigest()[:16], 16) for x in labels], dtype=np.uint64)


def topk(scores, tie, k):
    # Highest score first; label-independent deterministic tie-break.
    order = np.lexsort((tie, -np.asarray(scores, dtype=float)))
    return set(order[:k].tolist())


def real_comparison(db):
    cols = ",".join(["work_id", "cohort", "state"] + SHARED + EXTRA)
    rows = list(db.execute(f"SELECT {cols} FROM Work_Features"))
    ids = [r[0] for r in rows]
    a = np.array([sum(r[3 + i] for i in range(len(SHARED))) for r in rows], dtype=float)
    b = a + np.array([sum(r[3 + len(SHARED) + i] for i in range(len(EXTRA))) for r in rows], dtype=float)
    tie = tie_keys(ids)
    n = len(rows)
    overlap = {}
    for frac in BUDGETS:
        k = math.ceil(frac * n)
        sa, sb = topk(a, tie, k), topk(b, tie, k)
        inter, union = len(sa & sb), len(sa | sb)
        overlap[frac] = {"k": k, "jaccard": inter / union if union else 0.0,
                         "only_a": len(sa - sb), "only_b": len(sb - sa)}
    return ids, a, b, overlap, n


def controlled(rng):
    a_base = np.array([s for _, s, _ in FAMILIES], dtype=float)
    b_base = np.array([s + e for _, s, e in FAMILIES], dtype=float)
    p = len(FAMILIES)
    n = p + NEGATIVES
    pos_idx = set(range(p))
    per_budget = {frac: {"a_ctx": [], "b_ctx": [], "a_sel": np.zeros(p, int), "b_sel": np.zeros(p, int)} for frac in BUDGETS}
    for _ in range(CONTEXTS):
        tie = rng.random(n)
        sa = np.concatenate([a_base, np.zeros(NEGATIVES)])
        sb = np.concatenate([b_base, np.zeros(NEGATIVES)])
        for frac in BUDGETS:
            k = max(1, round(frac * n))
            ta, tb = topk(sa, tie, k), topk(sb, tie, k)
            rec = per_budget[frac]
            rec["a_ctx"].append(len(ta & pos_idx) / p)
            rec["b_ctx"].append(len(tb & pos_idx) / p)
            for i in range(p):
                if i in ta:
                    rec["a_sel"][i] += 1
                if i in tb:
                    rec["b_sel"][i] += 1
    return per_budget


def bootstrap_ci(a_ctx, b_ctx, rng, resamples=1000):
    a, b = np.array(a_ctx), np.array(b_ctx)
    diffs = []
    idx = np.arange(len(a))
    for _ in range(resamples):
        s = rng.choice(idx, len(idx), replace=True)
        diffs.append(float(b[s].mean() - a[s].mean()))
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return float(lo), float(hi)


def build(local: Path):
    db = sqlite3.connect((local / "mplads.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)
    ids, a_real, b_real, overlap, n_real = real_comparison(db)
    db.close()
    rng = np.random.default_rng(SEED)
    per_budget = controlled(rng)
    ci_rng = np.random.default_rng(SEED + 1)

    budgets = []
    for frac in BUDGETS:
        rec = per_budget[frac]
        a_rec = float(np.mean(rec["a_ctx"]))
        b_rec = float(np.mean(rec["b_ctx"]))
        lo, hi = bootstrap_ci(rec["a_ctx"], rec["b_ctx"], ci_rng)
        scenarios = [{"scenario": FAMILIES[i][0], "assigned": CONTEXTS,
                      "a_selected": int(rec["a_sel"][i]), "b_selected": int(rec["b_sel"][i])}
                     for i in range(len(FAMILIES))]
        budgets.append({"fraction": frac, "a_recovery": a_rec, "b_recovery": b_rec,
                        "difference": b_rec - a_rec, "ci95": [lo, hi],
                        "scenarios": scenarios, "actual_queue_overlap": overlap[frac]["jaccard"]})

    metrics = {
        "version": "six-source-ab-v1", "seed": SEED, "contexts": CONTEXTS,
        "real_works": n_real,
        "design": ("Baseline A sums seven transparent operational and payment screens. Enhanced B adds the "
                   "cost-outlier and near-duplicate screens. Recovery is measured on wholly synthetic, seeded "
                   "cases whose labels record which screen should fire; the two B-only families (inflated cost, "
                   "near-duplicate) are scored zero by A, so any B advantage at a fixed review budget comes from "
                   "the enhancement. The actual-queue overlap is computed on the real build and describes how "
                   "differently the two arms select cases, not which arm is correct."),
        "budgets": budgets,
        "limitations": [
            "No independently adjudicated fraud labels exist; controlled labels mean constructed review-worthy mechanisms, not real fraud.",
            "Recovery, precision-like terms and the interval apply only to the synthetic families and their 9% positive prevalence per context.",
            "The real-data layer reports only queue overlap at equal budgets; it makes no accuracy, false-positive-rate or money-saved claim.",
            "Screens are unweighted counts here so the enhancement's effect is isolated; the live queue uses the disclosed weighted rule registry.",
            "This is an offline screening-method comparison, not a prospective randomized trial with adjudicated outcomes.",
        ],
    }
    local.mkdir(parents=True, exist_ok=True)
    (local / "ab_metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    with (local / "ab_actual_scores.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["work_id", "baseline_a_score", "enhanced_b_score"])
        for i, wid in enumerate(ids):
            w.writerow([wid, int(a_real[i]), int(b_real[i])])
    with (local / "ab_controlled_benchmark.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["budget_fraction", "scenario", "assigned_contexts", "a_selected", "b_selected"])
        for bd in budgets:
            for s in bd["scenarios"]:
                w.writerow([bd["fraction"], s["scenario"], s["assigned"], s["a_selected"], s["b_selected"]])

    lines = ["# Offline A/B screening comparison — PS 26102 six_source build", "",
             f"Seed {SEED}; {CONTEXTS} synthetic contexts; real works scored: {n_real:,}.", "",
             "Baseline **A** = seven operational/payment screens. Enhanced **B** = A + cost-outlier + near-duplicate.",
             "Labels are constructed review-worthy mechanisms, not fraud. No accuracy claim on real rows.", "",
             "| Budget | A recovery | B recovery | B−A | 95% interval | Real queue overlap (Jaccard) |",
             "|---|---:|---:|---:|---|---:|"]
    for bd in budgets:
        lines.append(f"| {bd['fraction']*100:.0f}% | {bd['a_recovery']*100:.1f}% | {bd['b_recovery']*100:.1f}% | "
                     f"{bd['difference']*100:.1f} pp | {bd['ci95'][0]*100:.1f} to {bd['ci95'][1]*100:.1f} pp | "
                     f"{bd['actual_queue_overlap']*100:.1f}% |")
    lines += ["", "## Per-family recovery at 10% budget", "",
              "| Family | A selected | B selected (of {} contexts) |".format(CONTEXTS), "|---|---:|---:|"]
    b10 = next(bd for bd in budgets if bd["fraction"] == 0.10)
    for s in b10["scenarios"]:
        lines.append(f"| {s['scenario']} | {s['a_selected']} | {s['b_selected']} |")
    lines += ["", "## Limitations", ""] + [f"- {x}" for x in metrics["limitations"]] + [""]
    (local / "AB_Report.md").write_text("\n".join(lines), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", type=Path, default=HERE / "local")
    args = parser.parse_args()
    m = build(args.local)
    print(json.dumps({"budgets": [{"fraction": b["fraction"], "a": round(b["a_recovery"], 3),
                                   "b": round(b["b_recovery"], 3), "diff": round(b["difference"], 3),
                                   "overlap": round(b["actual_queue_overlap"], 3)} for b in m["budgets"]]}, indent=2))
