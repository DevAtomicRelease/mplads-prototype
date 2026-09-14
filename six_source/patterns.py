"""Read-only relations & pattern report over the built six_source dataset.

Run AFTER build.py. Reads local/mplads.sqlite3 and writes local/DATA_PATTERNS.md.
Descriptive only: nothing here asserts fraud; every signal requests human review.

    python patterns.py                    # default local/ build
    python patterns.py --local other_dir  # a different build directory
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent


def report(local: Path) -> str:
    db = sqlite3.connect((local / "mplads.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)
    q = lambda sql: pd.read_sql_query(sql, db)
    inr = lambda p: f"Rs {p / 1e9:,.2f} cr" if p is not None else "NA"
    out: list[str] = []
    P = out.append

    work = q("SELECT * FROM Work_Features")
    P("# MPLADS -- Data Relations & Patterns (descriptive; not fraud findings)\n")
    P(f"Works: {len(work):,} | feature columns: {work.shape[1]}\n")

    P("## 1. Lifecycle funnel")
    rec, san, comp = int(work.in_recommended.sum()), int(work.in_sanctioned.sum()), int(work.in_completed.sum())
    P(f"- Recommended rows: {rec:,}")
    P(f"- Sanctioned: {san:,} ({san / rec * 100:.1f}% of recommended)")
    P(f"- Completed: {comp:,} ({comp / san * 100:.1f}% of sanctioned)")
    P(f"- Sanctioned without a recommendation row: {int(work.recommendation_missing_flag.sum()):,}")
    P(f"- Open (sanctioned, not completed): {san - comp:,}\n")

    P("## 2. Financial cascade")
    for c in ["recommended_amount_paise", "sanction_amount_paise", "successful_payment_paise", "pending_payment_paise", "completion_actual_paise"]:
        P(f"- {c}: {inr(int(work[c].sum()))}")
    alloc = q("SELECT SUM(allocated_paise) a, SUM(consented_paise) c FROM MP_Features")
    san_p, pay_p = int(work.sanction_amount_paise.sum()), int(work.successful_payment_paise.sum())
    P(f"- allocated (MP limit snapshot): {inr(int(alloc.a[0]))}")
    P(f"- observed settled / sanction = {pay_p / san_p * 100:.1f}%")
    P(f"- sanction / allocation = {san_p / int(alloc.a[0]) * 100:.1f}%\n")

    P("## 3. Risk queue (rule engine)")
    P("```")
    P(work.priority_band.value_counts().to_string())
    P("```")
    rules = ["pending_recommendation_45d_flag", "sanction_delay_45d_flag", "open_over_one_year_flag", "no_payment_three_months_flag", "paid_over_sanction_flag", "completion_over_sanction_flag", "repeat_payment_report_flag", "high_cost_peer_flag", "high_similarity_review_flag"]
    for r in rules:
        P(f"- {r}: {int(work[r].sum()):,} ({work[r].mean() * 100:.1f}%)")
    P(f"- works with >=1 flag: {int((work.priority_score > 0).sum()):,} ({(work.priority_score > 0).mean() * 100:.1f}%)\n")

    P("## 4. Data-quality / chronology")
    for c in ["recommendation_missing_flag", "description_changed_flag", "missing_description_flag", "negative_chronology_flag", "future_event_flag", "source_stage_difference_flag"]:
        P(f"- {c}: {int(work[c].sum()):,}")
    P("")

    P("## 5. Top 12 states by High-band works")
    st = work.groupby("state").agg(works=("work_id", "size"), high=("priority_band", lambda x: (x == "High").sum()), open_yr=("open_over_one_year_flag", "sum"), mean_pri=("priority_score", "mean")).sort_values("high", ascending=False).head(12)
    st["high_pct"] = (st.high / st.works * 100).round(1)
    st["mean_pri"] = st.mean_pri.round(1)
    P("```")
    P(st.to_string())
    P("```\n")

    P("## 6. Cost outliers (prior-financial-year peer benchmark)")
    cf = work[work.cost_peer_log_z.notna()]
    P(f"- works with a peer benchmark: {len(cf):,} of {san:,} sanctioned")
    P(f"- high_cost_peer_flag: {int(work.high_cost_peer_flag.sum()):,}")
    P(f"- max cost_peer_ratio: {work.cost_peer_ratio.max():.1f}x ; 99.9th pct: {work.cost_peer_ratio.quantile(0.999):.1f}x\n")

    P("## 7. Duplicate / near-duplicate candidates")
    dup = q("SELECT * FROM Duplicate_Candidates")
    P(f"- candidate pairs: {len(dup):,}")
    P(f"- high_similarity_review pairs: {int(dup.high_similarity_review.sum()):,}")
    P(f"- exact same normalized text: {int(dup.same_normalized_text.sum()):,}")
    P(f"- works touched by a pair: {int((work.duplicate_candidate_count > 0).sum()):,}\n")

    P("## 8. Vendor concentration (collusion SCREEN, not proof)")
    ven = q("SELECT * FROM Vendor_Features")
    con = q("SELECT * FROM IDA_Year_Concentration")
    P(f"- distinct vendor ids: {len(ven):,}")
    P(f"- same-name different-id collisions (>1): {int((ven.same_name_vendor_id_count > 1).sum()):,}")
    P(f"- vendors paid across >5 IDAs: {int((ven.ida_count > 5).sum()):,}")
    P(f"- IDA*FY groups: {len(con):,}; HHI>0.5: {int((con.vendor_hhi > 0.5).sum()):,}; single-vendor (HHI~1): {int((con.vendor_hhi >= 0.999).sum()):,}")
    P("Top concentrated IDA*FY (min 5 vendors):")
    c2 = con[con.vendor_count >= 5].sort_values("vendor_hhi", ascending=False).head(6)[["ida_key", "fiscal_year", "vendor_count", "vendor_hhi", "top_vendor_share"]].round(3)
    P("```")
    P(c2.to_string(index=False))
    P("```\n")

    P("## 9. Payment timing")
    mar = q("SELECT SUM(march_payment_flag) m, COUNT(*) n FROM Payment_Features")
    P(f"- March payment rows: {int(mar.m[0]):,} of {int(mar.n[0]):,} ({mar.m[0] / mar.n[0] * 100:.1f}%)")
    P(f"- works with a payment_before_sanction row: {int(work.payment_before_sanction_flag.sum()):,}\n")

    P("## 10. Feature correlations (Spearman) & model-vs-rule complementarity")
    num = work[["priority_score", "isolation_percentile", "sanction_amount_paise", "successful_payment_paise", "sanction_delay_days", "completion_days", "duplicate_similarity", "cost_peer_log_z", "vendor_count"]].apply(pd.to_numeric, errors="coerce")
    P("```")
    P(num.corr(method="spearman").round(2).to_string())
    P("```")
    hi_iso = work.isolation_percentile >= 99
    hi_pri = work.priority_band == "High"
    both = int((hi_iso & hi_pri).sum())
    P(f"- Isolation Forest top 1%: {int(hi_iso.sum()):,}; also rule High-band: {both:,} (overlap {both / max(int(hi_iso.sum()), 1) * 100:.0f}%).")
    P("  Low overlap is intended: the unsupervised model surfaces atypicality the rules miss, and vice-versa.\n")

    db.close()
    return "\n".join(out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", type=Path, default=HERE / "local")
    args = parser.parse_args()
    text = report(args.local)
    (args.local / "DATA_PATTERNS.md").write_text(text, encoding="utf-8")
    print(text)
    print("\nSaved:", args.local / "DATA_PATTERNS.md")
