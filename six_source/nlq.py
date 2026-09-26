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
from entities import resolve_names, profile

# metric -> (order-by SQL alias, human label, kind, higher_is_better)
METRICS = {
    "works": ("works", "works", "count", None),
    "high": ("high", "high-priority works", "count", False),
    "open_over_year": ("open_over_year", "works open beyond one year", "count", False),
    "no_payment_3m": ("no_payment_3m", "works with no payment after three months", "count", False),
    "completed": ("completed", "works reported complete", "count", True),
    "sanctioned": ("sanctioned", "sanctioned works", "count", None),
    "cost_outliers": ("cost_outliers", "works costing much more than similar earlier works", "count", False),
    "duplicates": ("duplicates", "works with a near-identical description to another", "count", False),
    "paid_over": ("paid_over", "works with payments over sanction", "count", False),
    "completion_over": ("completion_over", "works with completion amount over sanction", "count", False),
    "march_rush": ("march_rush", "works with year-end (March) payment concentration", "count", False),
    "repeat_payments": ("repeat_payments", "works with repeated payment report rows", "count", False),
    "completed_no_payment": ("completed_no_payment", "works reported complete with no payment seen", "count", False),
    "avg_sanction": ("avg_sanction", "average sanctioned amount per work", "money", None),
    "pending_rec": ("pending_rec", "recommendations pending over 45 days", "count", False),
    "sanction_delay": ("sanction_delay", "works sanctioned over 45 days after recommendation", "count", False),
    "sanction_paise": ("sanction_paise", "sanctioned amount", "money", None),
    "settled_paise": ("settled_paise", "amount paid (reported)", "money", None),
    "pending_paise": ("pending_paise", "payments still in progress", "money", None),
    "settled_pct": ("settled_pct", "share of sanctioned money paid", "pct", True),
    "completion_rate": ("completion_rate", "share of sanctioned works reported complete", "pct", True),
    "mean_priority": ("mean_priority", "average flag score", "num", False),
}
METRIC_WORDS = [
    # Specific multi-word signals first so generic words ("payment", "completed") cannot capture them.
    ("march_rush", ["march rush", "year end rush", "year end", "yearend", "march concentration", "march payments", "march spending", "fiscal year end"]),
    ("repeat_payments", ["repeated payment", "repeat payment", "repeated payments", "repeat payments", "duplicate payment", "duplicate payments", "payment reported twice", "repeated payment report", "repeated payment reports"]),
    ("completed_no_payment", ["completed without payment", "complete without payment", "completed but unpaid", "completed with no payment", "completion without payment", "completed but not paid"]),
    ("avg_sanction", ["average sanction", "average sanctioned", "mean sanction", "mean sanctioned", "average cost", "average work cost", "average amount", "average value", "sanction per work", "average project cost"]),
    ("pending_rec", ["pending recommendation", "pending recommendations", "recommendation pending", "recommendations pending", "awaiting sanction", "not yet sanctioned", "unsanctioned recommendation", "unsanctioned recommendations"]),
    ("sanction_delay", ["sanction delay", "sanction delays", "delayed sanction", "delayed sanctions", "late sanction", "late sanctions", "slow sanction", "sanctioning delay", "delay in sanction"]),
    ("high", ["high priority", "high-priority", "high risk", "high-risk", "risky", "flagged", "high band", "priority cases", "most at risk"]),
    ("open_over_year", ["open beyond", "beyond one year", "over one year", "over a year", "delayed", "delays", "delay", "stalled", "overdue", "long open", "not completed in time"]),
    ("no_payment_3m", ["no payment", "unpaid", "without payment", "no observed payment"]),
    ("completion_rate", ["completion rate", "completed ratio", "percent completed", "completion percentage"]),
    ("completed", ["completed works", "works completed", "completed", "completions", "finished works"]),
    ("paid_over", ["overpaid", "paid over sanction", "payment over sanction", "payment above sanction", "payments above sanction", "paid above sanction", "over-sanction payment"]),
    ("completion_over", ["completion above sanction", "completion over sanction", "completed above sanction", "completion overrun"]),
    ("settled_pct", ["utilisation", "utilization", "settled ratio", "spend ratio", "paid ratio", "settled to sanction", "settled vs sanction", "settlement ratio"]),
    ("pending_paise", ["pending payment", "pending payments", "pending", "in progress", "in-progress", "not settled", "unsettled"]),
    ("settled_paise", ["settled", "paid", "spent", "expenditure", "disbursed", "payment", "payments", "spending"]),
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
COHORT_WORDS = [("rs_sitting", ["sitting"]), ("rs_retired", ["retired"]), ("__rs__", ["rajya sabha", "rajya"]), ("lok_sabha", ["lok sabha", "lok"])]
DESC_WORDS = ["top", "most", "highest", "largest", "biggest", "maximum", "greatest", "leading", "worst", "poorest"]
ASC_WORDS = ["bottom", "least", "lowest", "fewest", "smallest", "minimum", "best"]
NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fifteen": 15, "twenty": 20, "twenty five": 25, "thirty": 30, "fifty": 50}
# Words that ask for one number rather than a ranking ("how many ...", "total ...").
COUNT_WORDS = ["how many", "how much", "total", "overall", "national", "nationally", "in total", "sum of", "what is the", "whats the", "number of"]
# Nouns a top-N count may qualify ("5 districts"). Months/years are excluded so
# "no payment after three months" or "open over one year" never set a row limit.
LIMIT_NOUNS = r"(?:states?|uts?|regions?|districts?|authorit\w*|collectors?|idas?|mps?|members?|parliamentarians?|vendors?|contractors?|suppliers?|activit\w*|categor\w*|cohorts?|bands?)"

EXAMPLES = [
    "Jaunpur, give me details on this authority",
    "Which states have the most high-priority works?",
    "Top 10 district authorities by works open beyond one year",
    "Which districts in Bihar have the most delays?",
    "States with the lowest settled-to-sanction ratio",
    "How many works are open beyond one year in Uttar Pradesh?",
    "Top MPs by sanctioned amount in Gujarat",
    "Which activities have the most cost outliers?",
    "Compare settled ratio by cohort",
    "Which states have the most pending recommendations?",
    "Top 5 states by March rush",
    "How many works were completed in 2024-25?",
    "Total sanctioned amount",
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
    "SUM(paid_over_sanction_flag) paid_over, "
    "SUM(completion_over_sanction_flag) completion_over, "
    "SUM(march_rush_flag) march_rush, "
    "SUM(pending_recommendation_45d_flag) pending_rec, "
    "SUM(sanction_delay_45d_flag) sanction_delay, "
    "SUM(repeat_payment_report_flag) repeat_payments, "
    "SUM(completion_without_payment_flag) completed_no_payment, "
    "AVG(sanction_amount_paise) avg_sanction, "
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


def _has(text, word):
    # Whole-word/phrase membership on the space-padded normalised text.
    return f" {word} " in text


def _limit(text):
    # A number is a row limit only when it qualifies a ranking ("top 5", "bottom ten")
    # or a rankable noun ("10 districts"). Durations ("three months", "45 days") and
    # financial years ("2024 25") never set the limit.
    t = re.sub(r"\b20\d{2}\s+(?:20)?\d{2}\b", " ", text)
    num = r"(\d{1,3}|" + "|".join(re.escape(w) for w in sorted(NUM_WORDS, key=len, reverse=True)) + r")"
    m = re.search(r"\b(?:top|bottom|first|last|best|worst|highest|lowest)\s+" + num + r"\b", t) \
        or re.search(r"\b" + num + r"\s+(?:[a-z]+\s+)?" + LIMIT_NOUNS + r"\b", t)
    if m:
        v = m.group(1)
        return max(1, min(50, int(v) if v.isdigit() else NUM_WORDS[v]))
    return 10


def _fiscal_year(question):
    # Accept "2024-25", "2024-2025", "2024/25", "FY 2024 25"; data stores "2024-2025".
    m = re.search(r"\b(20\d{2})\s*[-/–]\s*((?:20)?\d{2})\b", question.lower()) or re.search(r"\bfy\s*(20\d{2})\s+((?:20)?\d{2})\b", question.lower())
    if not m:
        return None
    start, end = int(m.group(1)), m.group(2)
    end = int(end) if len(end) == 4 else (start // 100) * 100 + int(end)
    return f"{start}-{end}" if end == start + 1 else "invalid"


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
    fyval = _fiscal_year(question)
    if fyval:
        filters["fy"] = fyval
        if fyval != "invalid":
            clauses.append("sanction_fy = ?"); params.append(fyval); described.append(f"sanctioned in FY {fyval}")
    # Direction
    direction = "DESC"
    if any(_has(text, w) for w in ASC_WORDS) and not any(_has(text, w) for w in ["top", "most", "highest"]):
        direction = "ASC"
    higher_better = METRICS[metric][3]
    if _has(text, "worst") or _has(text, "poorest"):
        direction = "ASC" if higher_better else "DESC"
    if _has(text, "best"):
        direction = "DESC" if higher_better else "ASC"
    explicit_rank = any(_has(text, w) for w in DESC_WORDS + ASC_WORDS)
    ranking = explicit_rank or bool(dim) or text.strip().startswith(("which", "what", "list", "rank", "show", "compare"))
    count_question = any(_has(text, w) for w in COUNT_WORDS)
    # If a state filter is present and the dimension is state, drill to authorities instead.
    if dim == "state" and matched_state:
        dim = "ida"
    # One-number questions: "how many ... in X", or a national "total ..." with no
    # grouping dimension and no ranking word, return a single aggregate row.
    aggregate = (not dim) and ((bool(clauses) and (count_question or not ranking)) or (count_question and not explicit_rank))
    if not dim and not aggregate:
        dim = "state"
    averaged = any(_has(text, w) for w in ("average", "mean", "avg", "per work")) and metric not in ("avg_sanction", "mean_priority", "settled_pct", "completion_rate")
    return {"metric": metric, "metric_found": metric_hit is not None, "loaded": loaded, "dimension": dim, "aggregate": aggregate, "clauses": clauses, "params": params,
            "described": described, "direction": direction, "limit": _limit(text), "filters": filters, "averaged": averaged}


def _columns(dim, metric=None):
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
    if metric and metric not in {c["key"] for c in cols}:
        alias, label, kind, _ = METRICS[metric]
        cols.insert(1 if dim else 0, {"key": alias, "label": label.capitalize(), "kind": kind})
    return cols


def _fmt(kind, value):
    if value is None:
        return "—"
    if kind == "money":
        # paise: 1 crore = 1e9 paise, 1 lakh = 1e7 paise
        v = float(value)
        return f"₹{v / 1e7:,.2f} lakh" if 0 < abs(v) < 1e9 else f"₹{v / 1e9:,.2f} cr"
    if kind == "pct":
        return f"{float(value) * 100:.1f}%"
    if kind == "num":
        return f"{float(value):.1f}"
    return f"{int(value):,}"


def _clarify(question, message):
    return {"question": question, "interpretation": "Not interpreted", "summary": message, "note": message,
            "columns": [], "rows": [], "sql": "", "params": [], "row_count": 0,
            "caveat": "Try asking about high-priority works, delays, costs much higher than similar works, similar descriptions or the share of money paid — by state, district authority, MP, activity or house (Lok Sabha / Rajya Sabha)."}


def answer(db, question):
    states = [r[0] for r in db.execute("SELECT DISTINCT state FROM Work_Features")]
    intent = parse(question, states)
    # Design law: never rank people or works by fraud/corruption; no score is a finding of fraud.
    if intent["loaded"]:
        return _clarify(question, "This tool does not rank people or works by fraud or corruption — no score here is a finding of fraud. It only points to works a person should check. Try asking about high-priority works, delays, similar descriptions, or the share of money paid.")
    if re.search(r"\b(predict\w*|forecast\w*|tomorrow|future)\b", question, re.I):
        return _clarify(question, "Ask the data only describes the data as it is now; it does not predict. For a simple estimate of next month's total payments, open Insights & forecast.")
    detail_request = bool(re.search(r"\b(detail\w*|profile|information|overview|summary|about)\b", question, re.I))
    matches = resolve_names(db, question, aliases=detail_request or (intent["metric_found"] and not intent["filters"].get("state")))
    if len(matches) > 1:
        result = _clarify(question, f"Found {len(matches)} matching entities. Choose the exact profile below; no entity was selected automatically.")
        return {**result, "matches": matches, "caveat": "The same name can appear more than once (for example in both houses). Each option is a different record."}
    if len(matches) == 1:
        entity = matches[0]
        if detail_request or not intent["metric_found"]:
            details = profile(db, entity["kind"], entity["key"])
            return {"question": question, "entity": entity, "interpretation": "Profile of the named authority, MP or vendor", "summary": f"Profile: {entity['name']}", "columns": _columns(None), "rows": [{**details["summary"], "settled_pct": (details["summary"]["settled_paise"] or 0) / details["summary"]["sanction_paise"] if details["summary"]["sanction_paise"] else None}], "sql": details["sql"], "params": details["params"], "row_count": 1, "caveat": details["note"]}
        if entity["kind"] == "vendor":
            return {**_clarify(question, "For a named vendor, open its profile to see its payments and works."), "matches": matches}
        intent["clauses"].append({"ida": "ida_key = ?", "mp": "mp_key = ?"}[entity["kind"]])
        intent["params"].append(entity["key"])
        intent["described"].append("for " + entity["name"])
        intent["aggregate"] = True
        intent["dimension"] = None
    if not intent["metric_found"]:
        return _clarify(question, "Sorry, I could not match that to a name or a measure I know. Try a district authority name followed by 'details', or ask about works, delays, high-priority works, costs much higher than similar works, or payments made or still in progress.")
    fy = intent["filters"].get("fy")
    if fy:
        years = [r[0] for r in db.execute("SELECT DISTINCT sanction_fy FROM Work_Features WHERE sanction_fy IS NOT NULL ORDER BY 1")]
        if fy not in years:
            return _clarify(question, f"That financial year is not in the connected data. Years available: {', '.join(years)} (you can type e.g. \"2024-25\"). The year means the year a work was sanctioned.")
    metric, dim = intent["metric"], intent["dimension"]
    if intent.get("averaged"):
        intent["described"].append("showing totals — averages are only available for the sanctioned amount per work")
    where = (" WHERE " + " AND ".join(intent["clauses"])) if intent["clauses"] else ""
    order_alias = METRICS[metric][0]

    if dim == "vendor":
        if metric not in ("settled_paise", "pending_paise", "works"):
            return _clarify(question, "For vendors, only the number of works, payments made and payments in progress are available — not that measure.")
        # Vendor_Features is a whole-extract profile with no state/cohort/FY columns.
        # Rather than silently ignore a filter the user asked for, refuse and explain.
        if intent["described"]:
            return _clarify(question, "Vendors cannot be filtered by state, house or year here — vendor totals cover all the data. Ask e.g. \"top vendors by payments\" without a filter, or use Work investigation filtered by state and open a work to see its vendor.")
        vm = metric if metric in ("settled_paise", "pending_paise", "works") else "settled_paise"
        vcol = {"settled_paise": "successful_payment_paise", "pending_paise": "pending_payment_paise", "works": "work_count"}[vm]
        sql = f"SELECT vendor_name _dim, vendor_id _entity_key, work_count works, successful_payment_paise settled_paise, pending_payment_paise pending_paise, mp_count, ida_count FROM Vendor_Features ORDER BY {vcol} {intent['direction']}, vendor_id LIMIT ?"
        rows = [dict(r) for r in db.execute(sql, [intent["limit"]])]
        cols = [{"key": "_dim", "label": "Vendor", "kind": "text"}, {"key": "works", "label": "Works", "kind": "count"}, {"key": "settled_paise", "label": "Settled", "kind": "money"}, {"key": "pending_paise", "label": "In-progress", "kind": "money"}, {"key": "mp_count", "label": "MPs", "kind": "count"}, {"key": "ida_count", "label": "Authorities", "kind": "count"}]
        dirword = "highest" if intent["direction"] == "DESC" else "lowest"
        interp = f"Vendors by {METRICS[vm][1]} ({dirword} first), top {intent['limit']}."
        return _package(question, interp, cols, rows, sql, [intent["limit"]], vm, METRICS[vm][2], DIMENSIONS["vendor"], metric=vm)

    if dim == "month":
        if metric not in ("settled_paise", "pending_paise") or any(not x.startswith("in ") for x in intent["described"]):
            return _clarify(question, "Month-by-month answers are only available for payments made or in progress, optionally for one state. House, year and flag measures are not available by month.")
        if re.search(r"\b(top|bottom|most|least|highest|lowest|best|worst)\b", question, re.I):
            return _clarify(question, "Monthly payments are shown in date order, not ranked. Ask for monthly payments, optionally in one state.")
        # Monthly_Payments carries state, so a state filter is honoured; cohort/FY are not.
        st = intent["filters"].get("state")
        where_m = " WHERE state = ?" if st else ""
        params_m = [st] if st else []
        sql = f"SELECT payment_month _dim, SUM(successful_payment_paise) settled_paise, SUM(pending_payment_paise) pending_paise FROM Monthly_Payments{where_m} GROUP BY payment_month ORDER BY payment_month"
        rows = [dict(r) for r in db.execute(sql, params_m)]
        cols = [{"key": "_dim", "label": "Month", "kind": "text"}, {"key": "settled_paise", "label": "Settled", "kind": "money"}, {"key": "pending_paise", "label": "In progress", "kind": "money"}]
        unhonoured = [x for x in intent["described"] if not x.startswith("in ")]
        note = (" — note: " + ", ".join(unhonoured) + " not applied") if unhonoured else ""
        return _package(question, f"Monthly settled and in-progress payments{(' in ' + st) if st else ''}{note}.", cols, rows, sql, params_m, metric, "money", DIMENSIONS["month"], metric=metric)

    if intent["aggregate"]:
        sql = f"SELECT {WF_SELECT} FROM Work_Features{where}"
        row = dict(db.execute(sql, intent["params"]).fetchone())
        cols = _columns(None, metric)
        aprefix = "" if intent["metric_found"] else "No specific measure recognised — showing works and totals. "
        return _package(question, aprefix + ("Total" if intent["clauses"] else "Total for India") + ((" — " + ", ".join(intent["described"])) if intent["described"] else ""), cols, [row], sql, intent["params"], order_alias, METRICS[metric][2], None, described=intent["described"], metric=metric)

    gkey, disp = DIMENSIONS[dim][0], DIMENSIONS[dim][1]
    kind = METRICS[metric][2]
    having = " HAVING COUNT(*) >= 20" if metric in ("settled_pct", "completion_rate", "mean_priority", "avg_sanction") else ""
    # A "most X" ranking of a count signal lists only groups that have any X; a ranked
    # list of zeros would imply an order that does not exist.
    if kind == "count" and intent["direction"] == "DESC" and metric not in ("works", "sanctioned"):
        having = (having + " AND " if having else " HAVING ") + f"{order_alias} > 0"
    sql = f"SELECT {disp} _dim, {gkey} _entity_key, {WF_SELECT} FROM Work_Features{where} GROUP BY {gkey}{having} ORDER BY {order_alias} {intent['direction']}, works DESC, {gkey} LIMIT ?"
    rows = [dict(r) for r in db.execute(sql, [*intent["params"], intent["limit"]])]
    if dim == "cohort":
        labels = {"lok_sabha": "Lok Sabha", "rs_sitting": "Rajya Sabha (sitting)", "rs_retired": "Rajya Sabha (retired)"}
        for r in rows:
            r["_dim"] = labels.get(r["_dim"], r["_dim"])
    cols = _columns(dim, metric)
    dirword = "highest" if intent["direction"] == "DESC" else "lowest"
    interp = f"{_cap(DIMENSIONS[dim][3])} by {METRICS[metric][1]} ({dirword} first)" + ((", " + ", ".join(intent["described"])) if intent["described"] else "") + f", top {intent['limit']}" + (" (groups with at least 20 works)" if "COUNT(*) >= 20" in having else "") + "."
    result = _package(question, interp, cols, rows, sql, [*intent["params"], intent["limit"]], order_alias, kind, DIMENSIONS[dim], metric=metric)
    if not rows and "> 0" in having:
        scope = (" " + ", ".join(intent["described"])) if intent["described"] else " in the connected data"
        result["summary"] = f"None found: no works{scope} have {METRICS[metric][1].removeprefix('works with ')}, so there is nothing to rank."
        if metric in ("paid_over", "completion_over"):
            result["summary"] += " In this data, no payment or final cost is above the sanctioned amount. The check stays switched on and was tested in the A/B test."
    return result


def _cap(label):
    # Capitalise the first letter only, so "MPs" is not turned into "Mps".
    return label[:1].upper() + label[1:]


def _package(question, interpretation, columns, rows, sql, params, order_alias, kind, dim, described=None, metric=None):
    # Templated, source-tied summary from the returned rows.
    label = METRICS[metric][1] if metric else "settled payments"
    if not rows:
        summary = "No matching records."
    elif dim is None:
        r = rows[0]
        val = _fmt(kind, r.get(order_alias))
        summary = f"{_cap(label)}: {val} across {int(r['works']):,} works" + ((" " + ", ".join(described)) if described else "") + "."
    else:
        for row in rows:
            if isinstance(row.get("_dim"), str):
                row["_dim"] = re.sub(r"\s+", " ", row["_dim"]).strip()
        parts = [f"{row['_dim']} ({_fmt(kind, row.get(order_alias))})" for row in rows[:3]]
        summary = f"{_cap(dim[3])} ranked by {label}: " + ", ".join(parts) + ("." if len(rows) <= 3 else f", and {len(rows) - 3} more.")
    return {
        "question": question,
        "interpretation": interpretation,
        "summary": summary,
        "columns": columns,
        "rows": [{**{c["key"]: r.get(c["key"]) for c in columns}, **({"_entity_key": str(r["_entity_key"]), "_entity_kind": {"ida_key":"ida", "mp_key":"mp", "vendor_id":"vendor", "state":"state"}[dim[0]]} if dim and dim[0] in ("ida_key","mp_key","vendor_id","state") and r.get("_entity_key") is not None else {})} for r in rows],
        "sql": re.sub(r"\s+", " ", sql).strip(),
        "params": [str(p) for p in params],
        "row_count": len(rows),
        "caveat": "A summary of the loaded data — a pointer for review, not a finding of fraud. Every number can be checked with the database query shown below.",
    }
