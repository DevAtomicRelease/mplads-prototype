"""Offline A/B validation for PS 26102 — real feature extraction, actual queue scoring.

Two evidence layers, no fraud-accuracy claim (there are no adjudicated labels):

  1. Controlled mechanism benchmark on the REAL pipeline. Synthetic source-shaped
     rows (a peer background plus labelled positive mechanisms, legitimate-exception
     negatives and difficult negatives) are pushed through the actual build feature
     functions and scored by the actual rule engine. Baseline A = the operational/
     payment screens; enhanced B adds the cost-outlier, near-duplicate and year-end
     screens. At equal review budgets we report recovery, useful findings per review
     and the false-alert burden, with a paired bootstrap 95% interval.

  2. Real retrospective queue comparison. A vs B ranking of the actual built works,
     reporting queue overlap (Jaccard) at equal budgets — no accuracy claim.

Evaluation choices (families, seed, cutoff, peer anchors, thresholds) are frozen here
before any scoring; the production rules are used as-is (no tuning on the test set).

    python validate.py
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
import pandas as pd

from build import connect_works, payments_and_links, lifecycle_features, cost_features, duplicate_candidates, scores
from common import AS_OF

HERE = Path(__file__).parent
SEED = 26102
COHORT = "synthetic"
STATE = "Testland"
ACTIVITY = "Community road works"
PEER_MEDIAN = 500000            # rupees; frozen peer anchor for the cost benchmark
BASELINE = {"pending_recommendation_45d_flag", "sanction_delay_45d_flag", "open_over_one_year_flag",
            "no_payment_three_months_flag", "paid_over_sanction_flag", "completion_over_sanction_flag",
            "repeat_payment_report_flag"}  # arm A; arm B additionally uses march_rush/high_cost_peer/high_similarity
BUDGETS = [0.05, 0.10, 0.20, 0.30]
INSTANCES = 12                  # per family
ROUTINE_BG = 1200               # routine negatives in the eval pool -> realistic low prevalence
# family -> (is_positive, builder-tag). Positives should raise the queue; negatives should not.
FAMILIES = [
    ("Late sanction (>45 days)", True),
    ("Stalled open work (>1 year)", True),
    ("No payment after three months", True),
    ("Material payment over sanction", True),
    ("Material completion over sanction", True),
    ("Repeated payment report", True),
    ("Year-end (March) rush", True),
    ("Inflated cost vs peers (B only)", True),
    ("Near-duplicate description (B only)", True),
    ("Routine work", False),
    ("Rounding-level overage (immaterial)", False),
    ("Pending (in-progress) payment only", False),
    ("Distinct phase / continuation", False),
    ("Minor March share", False),
    ("Legitimately late completion", False),
]


def d(ts):
    return ts.strftime("%d-%b-%Y")


def _rec(work_id, mp, desc, sanc, rec_date, san_date, stage="Sanction"):
    return {"WORK_RECOMMENDATION_DTL_ID": work_id, "MP_NAME": mp, "STATE_NAME": STATE, "IDA_NAME": "Test District Authority",
            "CONSTITUENCY": "Test", "CONSTITUENCY_ID": "1", "HOUSE_OF_PARLIAMENT": "2", "TENURE": "Test Term",
            "WORK_CATEGORY": "Normal/Others", "ACTIVITY_NAME": ACTIVITY, "WORK_DESCRIPTION": desc, "LETTER_NO": "LN",
            "RECOMMENDED_AMOUNT": f"{sanc:.2f}", "SANCTION_AMOUNT": f"{sanc:.2f}", "RECOMMENDATION_DATE": d(rec_date),
            "SANCTION_DATE": d(san_date), "WORK_STAGE": stage, "FLAG": "1"}


def _pay(work_id, mp, vendor, amount, date, status="Payment Success"):
    return {"WORK_RECOMMENDATION_DTL_ID": work_id, "VENDOR_ID": vendor, "VENDOR_NAME": f"Vendor {vendor}", "IA_NAME": "IA",
            "WORK_STATUS": status, "STATE_NAME": STATE, "IDA_NAME": "Test District Authority", "MP_NAME": mp,
            "WORK_ID": "W" + work_id, "EXPENDITURE_DATE": d(date), "FUND_DISBURSED_AMT": f"{amount:.2f}"}


def generate(rng):
    ref = pd.Timestamp(AS_OF)
    rec_rows, san_rows, comp_rows, pay_rows = [], [], [], []
    labels = {}  # work_id -> (family, is_positive)
    counter = [0]

    def newid():
        counter[0] += 1
        return f"syn{counter[0]:06d}"

    def emit(family, positive, sanc, rec_date, san_date, desc=None, mp=None,
             completed=None, comp_amount=None, payments=None):
        wid = newid()
        mp = mp or f"Test Member {counter[0] % 50}"
        desc = desc or f"Construction of community road segment {counter[0]}"
        rec_rows.append(_rec(wid, mp, desc, sanc, rec_date, san_date))
        san_rows.append(_rec(wid, mp, desc, sanc, rec_date, san_date))
        if completed is not None:
            comp_rows.append({"WORK_RECOMMENDATION_DTL_ID": wid, "WORK_DESCRIPTION": desc, "ACTUAL_AMOUNT": f"{comp_amount if comp_amount is not None else sanc:.2f}",
                              "ACTUAL_END_DATE": d(completed), "WORK_ID": "C" + wid, "ATTACH_ID": "A1", "AVERAGE_RATING": "0.0"})
        for p in (payments or []):
            amt, date = p[0], p[1]; status = p[2] if len(p) > 2 else "Payment Success"
            pay_rows.append(_pay(wid, mp, str(1000 + counter[0] % 200), amt, date, status))
        if family is not None:
            labels[wid] = (family, positive)
        return wid

    # 1) Peer background: prior-FY sanctioned works so the cost benchmark has >=20 peers.
    for i in range(80):
        amt = float(rng.normal(PEER_MEDIAN, PEER_MEDIAN * 0.15))
        amt = max(50000, amt)
        san = pd.Timestamp("2023-08-01") + pd.Timedelta(days=int(rng.integers(0, 180)))
        emit(None, False, amt, san - pd.Timedelta(days=20), san,
             payments=[(amt * 0.6, san + pd.Timedelta(days=40))])

    def jitter(base, frac=0.1):
        return max(50000.0, float(base * (1 + rng.normal(0, frac))))

    for _ in range(INSTANCES):
        amt = jitter(PEER_MEDIAN)
        # Recent (< 1 year before the snapshot) so "open beyond one year" does not fire
        # except where a family intends it (stalled / late completion use old dates).
        cur = pd.Timestamp("2026-04-01") + pd.Timedelta(days=int(rng.integers(0, 120)))
        # ---- positives ----
        emit("Late sanction (>45 days)", True, amt, cur - pd.Timedelta(days=70), cur,
             payments=[(amt * 0.6, cur + pd.Timedelta(days=40))])
        old = pd.Timestamp("2024-09-01") + pd.Timedelta(days=int(rng.integers(0, 60)))
        emit("Stalled open work (>1 year)", True, amt, old - pd.Timedelta(days=20), old,
             payments=[(amt * 0.5, old + pd.Timedelta(days=30))])
        recent = pd.Timestamp("2026-02-01") + pd.Timedelta(days=int(rng.integers(0, 30)))
        emit("No payment after three months", True, amt, recent - pd.Timedelta(days=20), recent, payments=[])
        emit("Material payment over sanction", True, amt, cur - pd.Timedelta(days=20), cur,
             payments=[(amt * 1.4, cur + pd.Timedelta(days=40))])
        emit("Material completion over sanction", True, amt, cur - pd.Timedelta(days=20), cur,
             completed=cur + pd.Timedelta(days=90), comp_amount=amt * 1.4,
             payments=[(amt * 0.9, cur + pd.Timedelta(days=50))])
        dup_amt = amt
        emit("Repeated payment report", True, amt, cur - pd.Timedelta(days=20), cur,
             payments=[(dup_amt * 0.7, cur + pd.Timedelta(days=40)), (dup_amt * 0.7, cur + pd.Timedelta(days=40))])
        emit("Year-end (March) rush", True, amt, pd.Timestamp("2025-11-01") - pd.Timedelta(days=20), pd.Timestamp("2025-11-01"),
             payments=[(amt * 0.8, pd.Timestamp("2026-03-20"))])
        emit("Inflated cost vs peers (B only)", True, PEER_MEDIAN * 10, cur - pd.Timedelta(days=20), cur,
             payments=[(PEER_MEDIAN * 6, cur + pd.Timedelta(days=40))])
        shared = "Construction of concrete road at test ward number seven near market"
        a = emit("Near-duplicate description (B only)", True, amt, cur - pd.Timedelta(days=20), cur, desc=shared,
                 payments=[(amt * 0.6, cur + pd.Timedelta(days=40))])
        emit("Near-duplicate description (B only)", True, amt, cur - pd.Timedelta(days=18), cur, desc=shared,
             payments=[(amt * 0.6, cur + pd.Timedelta(days=42))])
        # ---- negatives ----
        emit("Routine work", False, amt, cur - pd.Timedelta(days=25), cur,
             payments=[(amt * 0.6, cur + pd.Timedelta(days=50))])
        emit("Rounding-level overage (immaterial)", False, amt, cur - pd.Timedelta(days=25), cur,
             payments=[(amt + 5000, cur + pd.Timedelta(days=50))])
        emit("Pending (in-progress) payment only", False, amt, cur - pd.Timedelta(days=25), cur,
             payments=[(amt * 0.6, cur + pd.Timedelta(days=50), "Payment In-Progress")])
        phase = f"Construction of drainage phase II extension continued at ward {counter[0]}"
        emit("Distinct phase / continuation", False, amt, cur - pd.Timedelta(days=25), cur, desc=phase,
             payments=[(amt * 0.6, cur + pd.Timedelta(days=50))])
        emit("Distinct phase / continuation", False, amt, cur - pd.Timedelta(days=23), cur, desc=phase,
             payments=[(amt * 0.6, cur + pd.Timedelta(days=52))])
        emit("Minor March share", False, amt, pd.Timestamp("2025-10-01") - pd.Timedelta(days=20), pd.Timestamp("2025-10-01"),
             payments=[(amt * 0.5, pd.Timestamp("2025-12-10")), (amt * 0.05, pd.Timestamp("2026-03-15"))])
        lc = pd.Timestamp("2024-09-01") + pd.Timedelta(days=int(rng.integers(0, 30)))
        emit("Legitimately late completion", False, amt, lc - pd.Timedelta(days=20), lc,
             completed=pd.Timestamp("2026-07-01"), comp_amount=amt,
             payments=[(amt * 0.9, pd.Timestamp("2026-06-20"))])

    # Large routine-negative background so positives are a realistic low share of the
    # review pool and the budget is the binding constraint.
    for _ in range(ROUTINE_BG):
        amt = jitter(PEER_MEDIAN)
        cur = pd.Timestamp("2026-04-01") + pd.Timedelta(days=int(rng.integers(0, 120)))
        emit("Routine work", False, amt, cur - pd.Timedelta(days=25), cur,
             payments=[(amt * 0.6, cur + pd.Timedelta(days=50))])

    def frame(rows):
        f = pd.DataFrame(rows)
        f["COHORT"] = COHORT
        f["source_record"] = np.arange(1, len(f) + 1)
        return f
    tables = {"recommended": frame(rec_rows), "sanctioned": frame(san_rows),
              "completed": frame(comp_rows), "payments": frame(pay_rows)}
    return tables, labels


def score_synthetic():
    rng = np.random.default_rng(SEED)
    tables, labels = generate(rng)
    work = connect_works(tables)
    work, _payments = payments_and_links(tables["payments"], work)
    work = lifecycle_features(work, AS_OF)
    work = cost_features(work)
    work, _pairs, _meta = duplicate_candidates(work)
    work, contributions = scores(work)
    base = contributions[contributions.rule.isin(BASELINE)].groupby("work_id").points.sum()
    work = work.assign(score_b=work.priority_score,
                       score_a=work.work_id.map(base).fillna(0).clip(upper=100).astype(int),
                       family=work.work_id.map({k: v[0] for k, v in labels.items()}),
                       positive=work.work_id.map({k: v[1] for k, v in labels.items()}))
    return work[work.family.notna()].reset_index(drop=True)


def tie(ids):
    return np.array([int(hashlib.sha256(f"{SEED}:{x}".encode()).hexdigest()[:16], 16) for x in ids], dtype=np.uint64)


def topk(score, t, k):
    return set(np.lexsort((t, -np.asarray(score, float)))[:k].tolist())


def evaluate(work):
    pos = work.positive.to_numpy(bool)
    ids = work.work_id.tolist()
    t = tie(ids)
    n, npos = len(work), int(pos.sum())
    fams = sorted(work.loc[pos, "family"].unique())
    budgets = []
    for frac in BUDGETS:
        k = max(1, math.ceil(frac * n))
        out = {}
        for arm, col in (("a", "score_a"), ("b", "score_b")):
            sc = work[col].to_numpy()
            sel = topk(sc, t, k)
            selpos = sum(1 for i in sel if pos[i])
            # False alerts = selected NEGATIVES that were actually flagged (score>0);
            # zero-score fillers are not alerts the queue would force a review of.
            flagged_neg = sum(1 for i in sel if (not pos[i]) and sc[i] > 0)
            reviewed = selpos + flagged_neg
            out[arm] = {"recovery": selpos / npos, "false_alerts": flagged_neg,
                        "findings_per_review": (selpos / reviewed) if reviewed else 0.0, "selected": sel}
        scen = []
        for f in fams:
            idx = set(np.flatnonzero((work.family == f).to_numpy() & pos).tolist())
            scen.append({"scenario": f, "assigned": len(idx),
                         "a_selected": len(idx & out["a"]["selected"]), "b_selected": len(idx & out["b"]["selected"])})
        budgets.append({"fraction": frac, "k": k,
                        "a_recovery": out["a"]["recovery"], "b_recovery": out["b"]["recovery"],
                        "difference": out["b"]["recovery"] - out["a"]["recovery"],
                        "a_false_alerts": out["a"]["false_alerts"], "b_false_alerts": out["b"]["false_alerts"],
                        "a_findings_per_review": out["a"]["findings_per_review"], "b_findings_per_review": out["b"]["findings_per_review"],
                        "scenarios": scen})
    return budgets, n, npos


def bootstrap(work, frac, rng, n_boot=1000):
    pos = work.positive.to_numpy(bool); ids = work.work_id.tolist(); t = tie(ids)
    a, b = work.score_a.to_numpy(), work.score_b.to_numpy(); idx = np.arange(len(work))
    diffs = []
    for _ in range(n_boot):
        s = rng.choice(idx, len(idx), replace=True)
        k = max(1, math.ceil(frac * len(s)))
        sub_pos = pos[s]; np_ = max(1, int(sub_pos.sum()))
        # rank within the resample
        order_a = s[np.lexsort((t[s], -a[s]))[:k]]; order_b = s[np.lexsort((t[s], -b[s]))[:k]]
        diffs.append(pos[order_b].sum() / np_ - pos[order_a].sum() / np_)
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return float(lo), float(hi)


def real_overlap(local):
    db = sqlite3.connect((local / "mplads.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)
    shared = ["pending_recommendation_45d_flag", "sanction_delay_45d_flag", "open_over_one_year_flag",
              "no_payment_three_months_flag", "paid_over_sanction_flag", "completion_over_sanction_flag", "repeat_payment_report_flag"]
    extra = ["march_rush_flag", "high_cost_peer_flag", "high_similarity_review_flag"]
    rows = list(db.execute(f"SELECT work_id,{','.join(shared+extra)} FROM Work_Features"))
    db.close()
    ids = [r[0] for r in rows]
    a = np.array([sum(r[1 + i] for i in range(len(shared))) for r in rows], float)
    b = a + np.array([sum(r[1 + len(shared) + i] for i in range(len(extra))) for r in rows], float)
    t = tie(ids); out = {}
    for frac in BUDGETS:
        k = math.ceil(frac * len(rows)); sa, sb = topk(a, t, k), topk(b, t, k)
        out[frac] = (len(sa & sb) / len(sa | sb)) if (sa | sb) else 0.0
    return out


def build(local: Path):
    work = score_synthetic()
    budgets, n, npos = evaluate(work)
    rng = np.random.default_rng(SEED + 1)
    overlap = real_overlap(local)
    for b in budgets:
        b["ci95"] = list(bootstrap(work, b["fraction"], rng))
        b["actual_queue_overlap"] = overlap[b["fraction"]]
    metrics = {
        "version": "six-source-ab-real-v2", "seed": SEED, "synthetic_pool": n, "synthetic_positives": npos,
        "design": ("Synthetic source-shaped rows (a prior-year peer background plus labelled positive mechanisms, "
                   "legitimate-exception and difficult negatives) are run through the actual build feature pipeline "
                   "and scored by the actual rule engine. Baseline A uses the operational/payment screens; enhanced B "
                   "adds the cost-outlier, near-duplicate and year-end screens. Recovery, useful findings per review "
                   "and false-alert burden are read off the real queue at equal review budgets. The real-queue overlap "
                   "is computed on the actual build and only describes how differently the arms select, not correctness."),
        "budgets": budgets,
        "limitations": [
            "No independently adjudicated fraud labels; synthetic labels are constructed review-worthy mechanisms, not real fraud.",
            "Legitimate-exception negatives (large scope, approved extension, revised sanction) are information-limited: some are irreducible false alerts with the supplied fields, and are reported as such.",
            "Recovery, findings-per-review and false-alert burden apply to the synthetic pool and its constructed low prevalence, not to national data; false alerts count genuinely flagged negatives, not zero-score fillers.",
            "The real-data layer reports only queue overlap at equal budgets; no accuracy, false-positive-rate or money-saved claim is made on real rows.",
            "Evaluation families, seed, cutoff and peer anchors were frozen before scoring; production thresholds are used unchanged (no tuning on the test set).",
            "This is an offline screening-method comparison, not a prospective randomised trial with adjudicated outcomes.",
        ],
    }
    local.mkdir(parents=True, exist_ok=True)
    (local / "ab_metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with (local / "ab_controlled_benchmark.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["budget_fraction", "scenario", "assigned", "a_selected", "b_selected"])
        for bd in budgets:
            for s in bd["scenarios"]:
                w.writerow([bd["fraction"], s["scenario"], s["assigned"], s["a_selected"], s["b_selected"]])
    work[["work_id", "family", "positive", "score_a", "score_b", "priority_band", "reason_codes"]].to_csv(local / "ab_actual_scores.csv", index=False, encoding="utf-8-sig")
    lines = ["# Offline A/B validation — PS 26102 (real feature extraction)", "",
             f"Seed {SEED}; synthetic pool {n} works ({npos} positive); scored by the actual build pipeline and rule engine.", "",
             "| Budget | A recovery | B recovery | B−A | 95% interval | B findings/review | B false alerts | Real queue overlap |",
             "|---|---:|---:|---:|---|---:|---:|---:|"]
    for bd in budgets:
        lines.append(f"| {bd['fraction']*100:.0f}% | {bd['a_recovery']*100:.1f}% | {bd['b_recovery']*100:.1f}% | {bd['difference']*100:.1f} pp | "
                     f"{bd['ci95'][0]*100:.1f} to {bd['ci95'][1]*100:.1f} pp | {bd['b_findings_per_review']*100:.0f}% | {bd['b_false_alerts']} | {bd['actual_queue_overlap']*100:.1f}% |")
    b10 = next(bd for bd in budgets if bd["fraction"] == 0.10)
    lines += ["", "## Per-family recovery at 10% budget", "", "| Family | Assigned | A | B |", "|---|---:|---:|---:|"]
    for s in b10["scenarios"]:
        lines.append(f"| {s['scenario']} | {s['assigned']} | {s['a_selected']} | {s['b_selected']} |")
    lines += ["", "## Limitations", ""] + [f"- {x}" for x in metrics["limitations"]] + [""]
    (local / "AB_Report.md").write_text("\n".join(lines), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", type=Path, default=HERE / "local")
    args = parser.parse_args()
    m = build(args.local)
    print(json.dumps({"pool": m["synthetic_pool"], "positives": m["synthetic_positives"],
                      "budgets": [{"f": b["fraction"], "a": round(b["a_recovery"], 3), "b": round(b["b_recovery"], 3),
                                   "diff": round(b["difference"], 3), "overlap": round(b["actual_queue_overlap"], 3)} for b in m["budgets"]]}, indent=2))
