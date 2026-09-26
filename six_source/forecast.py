"""Experimental one-month aggregate payment forecast, with chronological backtesting.

Only reported settlement totals are forecast, never fraud or physical completion.
The snapshot month is excluded. Missing months are not imputed as zero.
"""
import json
from pathlib import Path
import sqlite3
from datetime import date
from statistics import mean
from contextlib import closing

METHODS = ("last_month", "trailing_three_month_mean")

def prediction(history, method):
    return float(history[-1] if method == "last_month" else mean(history[-3:]))

def next_month(month):
    year, m = map(int, month.split("-"))
    return f"{year + (m == 12):04d}-{1 if m == 12 else m + 1:02d}"

def evaluate(rows, as_of):
    cutoff = as_of[:7]
    rows = sorted((r for r in rows if r["month"] < cutoff), key=lambda r: r["month"])
    result = {"available": False, "as_of": as_of, "excluded_from_training": cutoff,
              "methodology": "Train on earlier months only. Select between last-month and trailing-three-month mean using validation MAE; reserve the last three complete observed months for a rolling one-step test. No random time split.",
              "reference": "https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split",
              "limitations": ["Single retrospective export: historical coverage and later reporting revisions are unknown.",
                 "Experimental forecast of reported aggregate settlement, not a budget, remaining liability, fraud score or work-completion prediction.",
                 "The current snapshot month is excluded as potentially incomplete. A low reported month can reflect missing coverage.",
                 "Only three chronological test months; errors may be unstable. No calibrated prediction interval is claimed."]}
    if len(rows) < 15:
        return {**result, "reason": "At least 15 consecutive pre-snapshot months are required"}
    # Use the most recent consecutive window; refuse to invent missing observations.
    rows = rows[-36:]
    if any(next_month(a["month"]) != b["month"] for a, b in zip(rows, rows[1:])):
        return {**result, "reason": "Missing months in the observation window; no zero-filled forecast"}
    if next_month(rows[-1]["month"]) != cutoff:
        return {**result, "reason": "The last complete month is not observed; forecast withheld"}
    amounts = [r["paise"] for r in rows]
    folds = []
    for i in range(6, len(rows)):
        pred = {m: prediction(amounts[:i], m) for m in METHODS}
        folds.append({"month": rows[i]["month"], "train_through": rows[i-1]["month"],
                      "actual_paise": amounts[i], **pred, "split": "test" if i >= len(rows)-3 else "validation"})
    def mae(method, split):
        return mean(abs(r[method] - r["actual_paise"]) for r in folds if r["split"] == split)
    selected = min(METHODS, key=lambda m: (mae(m, "validation"), METHODS.index(m)))
    return {**result, "available": True, "selected_method": selected, "forecast_month": cutoff,
            "forecast_paise": prediction(amounts, selected), "history": rows, "folds": folds,
            "validation_months": len(folds)-3, "test_months": 3,
            "metrics": [{"method": m, "validation_mae_paise": mae(m, "validation"), "test_mae_paise": mae(m, "test")} for m in METHODS],
            "test_improved_over_last_month": mae(selected, "test") < mae("last_month", "test")}

def build(local):
    local = Path(local)
    meta = json.loads((local / "audit.json").read_text(encoding="utf-8"))
    with closing(sqlite3.connect((local / "mplads.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)) as db:
        rows = [{"month": r[0], "paise": r[1]} for r in db.execute("SELECT payment_month, SUM(successful_payment_paise) FROM Monthly_Payments WHERE payment_month IS NOT NULL GROUP BY payment_month ORDER BY payment_month")]
    report = evaluate(rows, meta["as_of"])
    (local / "forecast.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report
