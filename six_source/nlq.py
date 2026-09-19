"""Local, deterministic natural-language query over the built MPLADS dataset.

No external language model and no network: a plain-English question is parsed
into a structured intent (metric + dimension + filters + ranking) and turned into
a safe, parameterised, read-only aggregate query against Work_Features (plus
Vendor_Features / Monthly_Payments). SQL fragments come only from allow-listed
internal maps; user text reaches the database only as bound parameters or values
validated against the known vocabulary. Every returned number is an aggregate of
local rows, shown with the exact SQL. Nothing here asserts fraud.
"""
from __future__ import annotations

import re

# metric -> (order-by SQL alias, human label, kind, higher_is_better)
METRICS = {
    "works": ("works", "works", "count", None),
    "high": ("high", "high-priority works", "count", False),
    "open_over_year": ("open_over_year", "works open beyond one year", "count", False),
    "no_payment_3m": ("no_payment_3m", "works with no payment after three months", "count", False),
    "completed": ("completed", "reported-complete works (export membership)", "count", True),
    "sanctioned": ("sanctioned", "sanctioned works", "count", None),
    "cost_outliers": ("cost_outliers", "high-cost-peer works", "count", False),
    "duplicates": ("duplicates", "similar-work flags", "count", False),
    "sanction_paise": ("sanction_paise", "sanctioned amount", "money", None),
    "settled_paise": ("settled_paise", "settled (reported) payments", "money", None),
    "pending_paise": ("pending_paise", "in-progress payments", "money", None),
    "settled_pct": ("settled_pct", "settled-to-sanction ratio", "pct", True),
    "completion_rate": ("completion_rate", "reported completion rate (export membership)", "pct", True),
    "mean_priority": ("mean_priority", "mean review priority", "num", False),
}
METRIC_WORDS = [
    ("high", ["high priority", "high-priority", "high risk", "high-risk", "risky", "flagged", "high band", "priority cases", "most at risk"]),
    ("open_over_year", ["open beyond", "beyond one year", "over one year", "over a year", "delayed", "delays", "delay", "stalled", "overdue", "long open", "not completed in time"]),
    ("no_payment_3m", ["no payment", "unpaid", "without payment", "no observed payment"]),
    ("completion_rate", ["completion rate", "completed ratio", "percent completed", "completion percentage"]),
    ("completed", ["completed works", "works completed", "completed", "completions", "finished works"]),
    ("settled_pct", ["utilisation", "utilization", "settled ratio", "spend ratio", "paid ratio", "settled to sanction", "settled vs sanction", "settlement ratio"]),
    ("settled_paise", ["settled", "paid", "spent", "expenditure", "disbursed", "payment", "payments", "spending"]),
    ("pending_paise", ["pending payment", "pending", "in progress", "in-progress", "not settled", "unsettled"]),
    ("sanction_paise", ["sanction amount", "sanctioned amount", "sanctioned value", "funds sanctioned", "sanctioned funds", "sanction value"]),
    ("cost_outliers", ["cost outlier", "cost outliers", "overpriced", "high cost", "high-cost", "expensive", "costliest", "high cost peer"]),
    ("duplicates", ["duplicate", "duplicates", "similar work", "similar works", "repeated work"]),
    ("mean_priority", ["average priority", "mean priority", "average risk", "risk score"]),
    ("sanctioned", ["sanctioned works", "number sanctioned"]),
    ("works", ["works", "projects", "how many works", "number of works", "count of works"]),
]
# dimension -> (group key column, display column, label singular, label plural, source)
DIMENSIONS = {
    "state": ("state", "state", "state", "states", "work"),
    "cohort": ("cohort", "cohort", "cohort", "cohorts", "work"),
    "ida": ("ida_key", "ida_name", "district authority", "district authorities", "work"),
    "mp": ("mp_key", "mp_name", "MP", "MPs", "work"),
    "activity": ("activity_type", "activity_type", "activity", "activities", "work"),
    "fy": ("sanction_fy", "sanction_fy", "sanction year", "sanction years", "work"),
    "band": ("priority_band", "priority_band", "priority band", "priority bands", "work"),
    "vendor": ("vendor_id", "vendor_name", "vendor", "vendors", "vendor"),
    "month": ("payment_month", "payment_month", "month", "months", "month"),
}
DIM_WORDS = [
    ("ida", ["district authorit", "district authorit", "districts", "district", "authorities", "authority", "collector", "ida"]),
    ("mp", ["mp", "mps", "member of parliament", "members of parliament", "members", "parliamentarian"]),
    ("vendor", ["vendor", "vendors", "contractor", "contractors", "supplier"]),
    ("activity", ["activity", "activities", "category", "categories", "work type", "type of work", "kind of work"]),
    ("cohort", ["cohort", "house", "chamber"]),
    ("month", ["month", "months", "monthly", "over time", "by month"]),
    ("fy", ["financial year", "sanction year", "by year", "per year", "each year"]),
    ("band", ["priority band", "band", "bands"]),
    ("state", ["state", "states", "region", "regions", "state wise", "statewise"]),
]
SIGNALS = {
    "open_over_one_year_flag": ["open beyond one year", "open over a year", "delayed", "stalled"],
    "no_payment_three_months_flag": ["no payment after three months", "no payment", "unpaid"],
    "high_cost_peer_flag": ["high cost", "cost outlier", "overpriced"],
    "high_similarity_review_flag": ["duplicate", "similar work"],
    "paid_over_sanction_flag": ["paid over sanction", "payment above sanction", "overpaid"],
    "repeat_payment_report_flag": ["repeated payment", "repeat payment"],
}
COHORT_WORDS = [("rs_sitting", ["sitting"]), ("rs_retired", ["retired"]), ("__rs__", ["rajya sabha", "rajya"]), ("lok_sabha", ["lok sabha", "lok"])]
DESC_WORDS = ["top", "most", "highest", "largest", "biggest", "maximum", "greatest", "leading", "worst", "poorest"]
ASC_WORDS = ["bottom", "least", "lowest", "fewest", "smallest", "minimum", "best"]
NUM_WORDS = {"three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "fifteen": 15, "twenty": 20, "twenty five": 25, "thirty": 30}

EXAMPLES = [
    "Which states have the most high-priority works?",
    "Top 10 district authorities by works open beyond one year",
    "Which districts in Bihar have the most delays?",
    "States with the lowest settled-to-sanction ratio",
    "How many works are open beyond one year in Uttar Pradesh?",
    "Top MPs by sanctioned amount in Gujarat",
    "Which activities have the most cost outliers?",
    "Compare settled ratio by cohort",
]

WF_SELECT = (
    "COUNT(*) works, "
    "SUM(CASE WHEN priority_band IN ('High','Critical') THEN 1 ELSE 0 END) high, "
    "SUM(open_over_one_year_flag) open_over_year, "
    "SUM(no_payment_three_months_flag) no_payment_3m, "
    "SUM(in_completed) completed, "
    "SUM(in_sanctioned) sanctioned, "
    "SUM(high_cost_peer_flag) cost_outliers, "
    "SUM(high_similarity_review_flag) duplicates, "
    "SUM(sanction_amount_paise) sanction_paise, "
    "SUM(successful_payment_paise) settled_paise, "
    "SUM(pending_payment_paise) pending_paise, "
    "AVG(priority_score) mean_priority, "
    "CAST(SUM(successful_payment_paise) AS REAL)/NULLIF(SUM(sanction_amount_paise),0) settled_pct, "
    "CAST(SUM(in_completed) AS REAL)/NULLIF(SUM(in_sanctioned),0) completion_rate"
)


def _find(text, pairs):
    # Whole-word (phrase) match so short tokens like "mp" or "ut" do not match
    # inside "compare" or "uttar".
    for canonical, words in pairs:
        for w in words:
            if re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", text):
                return canonical
    return None


def _limit(text):
    m = re.search(r"\b(\d{1,3})\b", text)
    if m:
        return max(1, min(50, int(m.group(1))))
    for word, value in NUM_WORDS.items():
        if word in text:
            return value
    return 10


def parse(question, states):
    # Lowercase and reduce punctuation (hyphens, ?, etc.) to spaces so multi-word
    # phrases like "settled-to-sanction ratio" match the vocabulary.
    text = " " + re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", question.lower())).strip() + " "
    loaded = any(w in text for w in (" corrupt", " corruption", " fraud", " fraudulent", " guilty", " culprit", " criminal", " scam", " embezzl", " bribe", " cheat"))
    metric_hit = _find(text, METRIC_WORDS)
    metric = metric_hit or "works"
    dim = _find(text, DIM_WORDS)
    # Filters
    filters, clauses, params, described = {}, [], [], []
    matched_state = next((s for s in sorted(states, key=len, reverse=True) if s.lower() in text), None)
    if matched_state:
        clauses.append("state = ?"); params.append(matched_state); described.append(f"in {matched_state}")
        filters["state"] = matched_state
    cohort = _find(text, COHORT_WORDS)
    if cohort == "__rs__":
        clauses.append("cohort IN (?,?)"); params.extend(["rs_sitting", "rs_retired"]); described.append("Rajya Sabha")
    elif cohort:
        clauses.append("cohort = ?"); params.append(cohort); described.append({"lok_sabha": "Lok Sabha", "rs_sitting": "Rajya Sabha (sitting)", "rs_retired": "Rajya Sabha (retired)"}[cohort])
    fym = re.search(r"(20\d{2})[ -](20\d{2})", question.lower())
    if fym:
        fyval = f"{fym.group(1)}-{fym.group(2)}"
        clauses.append("sanction_fy = ?"); params.append(fyval); described.append(f"FY {fyval}")
    # Direction
    direction = "DESC"
    if any(w in text for w in ASC_WORDS) and not any(w in text for w in ["top", "most", "highest"]):
        direction = "ASC"
    higher_better = METRICS[metric][3]
    if "worst" in text or "poorest" in text:
        direction = "ASC" if higher_better else "DESC"
    if "best" in text:
        direction = "DESC" if higher_better else "ASC"
    ranking = any(w in text for w in DESC_WORDS + ASC_WORDS) or bool(dim) or text.strip().startswith(("which", "what", "list", "rank", "show", "compare"))
    # If a state filter is present and the dimension is state, drill to authorities instead.
    if dim == "state" and matched_state:
        dim = "ida"
    # Aggregate question ("how many ... in X") with a filter and no grouping dimension.
    aggregate = (not dim) and (bool(clauses)) and (("how many" in text) or ("total" in text) or ("what is" in text) or not ranking)
    if not dim and not aggregate:
        dim = "state"
    return {"metric": metric, "metric_found": metric_hit is not None, "loaded": loaded, "dimension": dim, "aggregate": aggregate, "clauses": clauses, "params": params,
            "described": described, "direction": direction, "limit": _limit(text), "filters": filters}


def _columns(dim):
    label = DIMENSIONS[dim][2].title() if dim else None
    cols = []
    if dim:
        cols.append({"key": "_dim", "label": label, "kind": "text"})
    cols += [
        {"key": "works", "label": "Works", "kind": "count"},
        {"key": "high", "label": "High", "kind": "count"},
        {"key": "open_over_year", "label": "Open >1yr", "kind": "count"},
        {"key": "sanction_paise", "label": "Sanctioned", "kind": "money"},
        {"key": "settled_paise", "label": "Settled", "kind": "money"},
        {"key": "settled_pct", "label": "Settled/sanction", "kind": "pct"},
        {"key": "mean_priority", "label": "Mean priority", "kind": "num"},
    ]
    return cols


def _fmt(kind, value):
    if value is None:
        return "—"
    if kind == "money":
        return f"₹{float(value) / 1e9:,.2f} cr"
    if kind == "pct":
        return f"{float(value) * 100:.1f}%"
    if kind == "num":
        return f"{float(value):.1f}"
    return f"{int(value):,}"


def _clarify(question, message):
    return {"question": question, "interpretation": "Not interpreted", "summary": message, "note": message,
            "columns": [], "rows": [], "sql": "", "params": [], "row_count": 0,
            "caveat": "Ask for a review signal — high-priority works, delays, cost overruns, duplicates, settled-to-sanction ratio — by state, district authority, MP, activity or cohort."}


def answer(db, question):
    states = [r[0] for r in db.execute("SELECT DISTINCT state FROM Work_Features")]
    intent = parse(question, states)
    # Design law: never rank people or works by fraud/corruption; no score is a finding of fraud.
    if intent["loaded"]:
        return _clarify(question, "This tool does not rank people or works by fraud or corruption — no score here is a finding of fraud. It surfaces review signals for human verification. Try a signal such as high-priority works, cost overruns, delays, duplicates, or settled-to-sanction ratio.")
    metric, dim = intent["metric"], intent["dimension"]
    where = (" WHERE " + " AND ".join(intent["clauses"])) if intent["clauses"] else ""
    order_alias = METRICS[metric][0]

    if dim == "vendor":
        # Vendor_Features is a whole-extract profile with no state/cohort/FY columns, so
        # entity filters cannot be honoured here — say so rather than dropping them silently.
        vm = metric if metric in ("settled_paise", "pending_paise", "works") else "settled_paise"
        vcol = {"settled_paise": "successful_payment_paise", "pending_paise": "pending_payment_paise", "works": "work_count"}[vm]
        sql = f"SELECT vendor_name _dim, work_count works, successful_payment_paise settled_paise, pending_payment_paise pending_paise, mp_count, ida_count FROM Vendor_Features ORDER BY {vcol} DESC LIMIT ?"
        rows = [dict(r) for r in db.execute(sql, [intent["limit"]])]
        cols = [{"key": "_dim", "label": "Vendor", "kind": "text"}, {"key": "works", "label": "Works", "kind": "count"}, {"key": "settled_paise", "label": "Settled", "kind": "money"}, {"key": "pending_paise", "label": "In-progress", "kind": "money"}, {"key": "mp_count", "label": "MPs", "kind": "count"}, {"key": "ida_count", "label": "Authorities", "kind": "count"}]
        note = " — note: state/cohort/year filters do not apply to the vendor extract" if intent["described"] else ""
        interp = f"Top {intent['limit']} vendors by {METRICS[vm][1]}{note}."
        return _package(question, interp, cols, rows, sql, [intent["limit"]], vm, METRICS[vm][2], DIMENSIONS["vendor"])

    if dim == "month":
        # Monthly_Payments carries state, so a state filter is honoured; cohort/FY are not.
        st = intent["filters"].get("state")
        where_m = " WHERE state = ?" if st else ""
        params_m = [st] if st else []
        sql = f"SELECT payment_month _dim, SUM(successful_payment_paise) settled_paise, SUM(pending_payment_paise) pending_paise FROM Monthly_Payments{where_m} GROUP BY payment_month ORDER BY payment_month"
        rows = [dict(r) for r in db.execute(sql, params_m)]
        cols = [{"key": "_dim", "label": "Month", "kind": "text"}, {"key": "settled_paise", "label": "Settled", "kind": "money"}, {"key": "pending_paise", "label": "In progress", "kind": "money"}]
        unhonoured = [x for x in intent["described"] if not x.startswith("in ")]
        note = (" — note: " + ", ".join(unhonoured) + " not applied") if unhonoured else ""
        return _package(question, f"Monthly settled and in-progress payments{(' in ' + st) if st else ''}{note}.", cols, rows, sql, params_m, "settled_paise", "money", DIMENSIONS["month"])

    if intent["aggregate"]:
        sql = f"SELECT {WF_SELECT} FROM Work_Features{where}"
        row = dict(db.execute(sql, intent["params"]).fetchone())
        cols = _columns(None)
        aprefix = "" if intent["metric_found"] else "No specific metric recognised — showing works and totals. "
        return _package(question, aprefix + "National total" + ((" " + ", ".join(intent["described"])) if intent["described"] else ""), cols, [row], sql, intent["params"], order_alias, METRICS[metric][2], None, described=intent["described"], metric=metric)

    gkey, disp = DIMENSIONS[dim][0], DIMENSIONS[dim][1]
    having = " HAVING COUNT(*) >= 20" if metric in ("settled_pct", "completion_rate", "mean_priority") else ""
    sql = f"SELECT {disp} _dim, {WF_SELECT} FROM Work_Features{where} GROUP BY {gkey}{having} ORDER BY {order_alias} {intent['direction']}, works DESC LIMIT ?"
    rows = [dict(r) for r in db.execute(sql, [*intent["params"], intent["limit"]])]
    if dim == "cohort":
        labels = {"lok_sabha": "Lok Sabha", "rs_sitting": "Rajya Sabha (sitting)", "rs_retired": "Rajya Sabha (retired)"}
        for r in rows:
            r["_dim"] = labels.get(r["_dim"], r["_dim"])
    cols = _columns(dim)
    dirword = "highest" if intent["direction"] == "DESC" else "lowest"
    prefix = "" if intent["metric_found"] else "No specific metric recognised — ranking by number of works (name a metric such as high-priority, delays, cost outliers, settled or pending amount, settled-to-sanction ratio). "
    interp = prefix + f"{DIMENSIONS[dim][3].title()} by {METRICS[metric][1]} ({dirword} first)" + ((", " + ", ".join(intent["described"])) if intent["described"] else "") + f", top {intent['limit']}."
    return _package(question, interp, cols, rows, sql, [*intent["params"], intent["limit"]], order_alias, METRICS[metric][2], DIMENSIONS[dim], metric=metric)


def _package(question, interpretation, columns, rows, sql, params, order_alias, kind, dim, described=None, metric=None):
    # Templated, source-tied summary from the returned rows.
    label = METRICS[metric][1] if metric else "settled payments"
    if not rows:
        summary = "No matching records."
    elif dim is None:
        r = rows[0]
        val = _fmt(kind, r.get(order_alias))
        summary = f"{label.capitalize()}: {val} across {int(r['works']):,} works" + ((" " + ", ".join(described)) if described else "") + "."
    else:
        parts = [f"{row['_dim']} ({_fmt(kind, row.get(order_alias))})" for row in rows[:3]]
        summary = f"{dim[3].capitalize()} ranked by {label}: " + ", ".join(parts) + ("." if len(rows) <= 3 else f", and {len(rows) - 3} more.")
    return {
        "question": question,
        "interpretation": interpretation,
        "summary": summary,
        "columns": columns,
        "rows": [{**{c["key"]: r.get(c["key"]) for c in columns}} for r in rows],
        "sql": re.sub(r"\s+", " ", sql).strip(),
        "params": [str(p) for p in params],
        "row_count": len(rows),
        "caveat": "Descriptive aggregate of local Work_Features rows; a review signal, not a finding of fraud. Every value is reproducible from the SQL shown.",
    }
