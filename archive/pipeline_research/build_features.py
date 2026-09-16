"""Reproducible, local MPLADS screening features. No source workbook mutations."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pandas as pd

VERSION = "core-2026-09-06-v1"
NAMESPACE = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
SEED = 26102
SOURCES = {
    "works": "Works Sanctioned.xlsx",
    "allocations": "Allocated Limit for Honble MPs.xlsx",
    "consents": "Amount consented for Calamity.xlsx",
}
GUIDELINES = "https://www.mplads.gov.in/MPLADS/UploadedFiles/MPLADSGuidelinesApril2023.pdf"
PARLIAMENT = "https://www.sansad.in/getFile/loksabhaquestions/annex/183/AS338_TsKdbP.pdf?source=pqals"
EARLY_STATUSES = {"Sanction", "Vendor Identification", "Time Estimation"}
STATUS_STAGE = {
    "Sanction": "Sanctioned", "Vendor Identification": "Procurement",
    "Time Estimation": "Planning", "Work partially Completed": "Execution",
    "Physical Inspection": "Verification", "Work Completed": "Completed",
}
STOPWORDS = set("a an the of for and at in to with from by near construction installation purchase providing proposed work works supply development road street light lights solar led high mast public community village gram panchayat ward no number district block under new existing place".split())
DEFINITIONS: dict[str, tuple[str, str]] = {}


def define(field: str, definition: str, timing: str = "Snapshot descriptive") -> str:
    DEFINITIONS[field] = (definition, timing)
    return field


def norm_text(value) -> str:
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    return " ".join(re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE).replace("_", " ").split())


def norm_key(value) -> str:
    return re.sub(r"\W|_", "", norm_text(value), flags=re.UNICODE)


def mp_key(value) -> str:
    text = norm_text(value)
    # Only prefixes are removed: no fuzzy match or removal inside personal names.
    text = re.sub(r"^(?:(?:shri|sri|shree|smt|shrimati|dr|prof|honble)\s+)+", "", text)
    return norm_key(text)


def source_rows(path: Path) -> tuple[list[dict], dict]:
    """Read first worksheet values without consulting potentially broken styles."""
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root]
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in root.findall(".//m:row", NAMESPACE):
            record = {"_xlsx_row": int(row.get("r"))}
            for cell in row.findall("m:c", NAMESPACE):
                column = re.sub(r"\d", "", cell.get("r"))
                value_element = cell.find("m:v", NAMESPACE)
                value = value_element.text if value_element is not None else None
                if cell.get("t") == "s" and value is not None:
                    value = shared[int(value)]
                elif cell.get("t") == "inlineStr":
                    element = cell.find("m:is", NAMESPACE)
                    value = "".join(element.itertext()) if element is not None else None
                record[column] = None if value is None or value.strip() == "" else value
            rows.append(record)
    data = [r for r in rows if str(r.get("A", "")).isdigit()]
    total = [r for r in rows if "grand total" in str(r.get("A", "")).casefold()]
    if len(total) != 1:
        raise ValueError(f"{path.name}: expected exactly one Grand Total row")
    return data, total[0]


def exact_sum(rows: list[dict], column: str) -> Decimal:
    return sum((Decimal(r[column]) for r in rows if r.get(column) is not None), Decimal(0))


def fiscal_year(value):
    if pd.isna(value):
        return None
    start = value.year if value.month >= 4 else value.year - 1
    return f"{start}-{start + 1}"


def dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%d-%b-%Y", errors="coerce")


def divide(numerator, denominator):
    if pd.isna(numerator) or pd.isna(denominator) or denominator <= 0:
        return None
    return numerator / denominator


def prior_history(frame: pd.DataFrame, key: str, prefix: str) -> pd.DataFrame:
    """Group equal dates before cumulative sums, so same-date rows never leak."""
    daily = frame.dropna(subset=["sanction_date"]).groupby([key, "sanction_date"], dropna=False).agg(
        count=("work_id", "size"), amount=("sanction_amount", lambda x: x.sum(min_count=1)),
        missing_amount_count=("sanction_amount", lambda x: x.isna().sum()))
    daily = daily.reset_index().sort_values([key, "sanction_date"])
    daily[f"{prefix}_prior_work_count"] = daily.groupby(key)["count"].cumsum() - daily["count"]
    known_amount = daily["amount"].fillna(0)
    daily[f"{prefix}_prior_sanction_total"] = known_amount.groupby(daily[key]).cumsum() - known_amount
    prior_missing = daily.groupby(key)["missing_amount_count"].cumsum() - daily["missing_amount_count"]
    daily.loc[prior_missing.gt(0), f"{prefix}_prior_sanction_total"] = np.nan
    daily[f"{prefix}_previous_sanction_date"] = daily.groupby(key)["sanction_date"].shift()
    daily[f"{prefix}_days_since_previous_sanction"] = (
        daily["sanction_date"] - daily[f"{prefix}_previous_sanction_date"]).dt.days
    daily[f"{prefix}_prior90d_work_count"] = 0
    for _, indexes in daily.groupby(key, sort=False).groups.items():
        sub = daily.loc[indexes]
        days = sub["sanction_date"].to_numpy(dtype="datetime64[D]").astype("int64")
        counts = sub["count"].to_numpy()
        sums = np.concatenate([[0], np.cumsum(counts)])
        starts = np.searchsorted(days, days - 90, side="left")
        daily.loc[indexes, f"{prefix}_prior90d_work_count"] = sums[np.arange(len(sub))] - sums[starts]
    columns = [key, "sanction_date"] + [c for c in daily if c.startswith(prefix + "_") and c != key]
    return frame.merge(daily[columns], on=[key, "sanction_date"], how="left", validate="many_to_one")


def peer_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Leave-current-row-out monetary peers; wider groups used for sparse cells."""
    state_type = frame.groupby(["state", "work_type"], dropna=False).groups
    type_only = frame.groupby("work_type", dropna=False).groups
    positive = frame["sanction_amount"].notna() & frame["sanction_amount"].gt(0)
    global_indexes = frame.index[positive].to_numpy()
    amounts = frame["sanction_amount"].to_numpy(float)
    cache = {}
    for index, row in frame.iterrows():
        levels = [("State + work type", state_type[(row.state, row.work_type)]),
                  ("Work type", type_only[row.work_type]), ("Global", global_indexes)]
        for level, indexes in levels:
            indexes = np.asarray(indexes)
            indexes = indexes[positive.iloc[indexes].to_numpy()]
            if len(indexes) - int(index in indexes) >= 10 or level == "Global":
                break
        peers = amounts[indexes[indexes != index]]
        if not len(peers):
            continue
        # Group statistics depend only on peer values, including leave-one-out removal.
        signature = (level, tuple(indexes), amounts[index])
        if signature not in cache:
            median = float(np.median(peers))
            mad = float(np.median(np.abs(peers - median)))
            iqr_scale = float((np.quantile(peers, .75) - np.quantile(peers, .25)) / 1.349)
            if mad > 0:
                scale, method = 1.4826 * mad, "1.4826 x MAD"
            elif iqr_scale > 0:
                scale, method = iqr_scale, "IQR / 1.349"
            else:
                # Degenerate repeated amounts: a disclosed minimum scale, not a zero divisor.
                scale, method = max(.1 * median, 1.0), "10% median floor (degenerate peers)"
            cache[signature] = (median, scale, method)
        median, scale, method = cache[signature]
        amount = row.sanction_amount
        z = (amount - median) / scale if pd.notna(amount) else np.nan
        ratio = amount / median if pd.notna(amount) and median > 0 else np.nan
        frame.loc[index, "peer_group_level"] = level
        frame.loc[index, "peer_count"] = len(peers)
        frame.loc[index, "peer_median_amount"] = median
        frame.loc[index, "peer_scale_method"] = method
        frame.loc[index, "peer_robust_z"] = z
        frame.loc[index, "amount_to_peer_median_ratio"] = ratio
        frame.loc[index, "high_cost_outlier_flag"] = bool(z > 3.5 and ratio >= 2)
    return frame


def duplicate_features(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    records = frame.to_dict("records")
    normalized = frame["description_normalized"].tolist()
    tokens = [set(t.split()) - STOPWORDS for t in normalized]
    grams = [{t[i:i + 3] for i in range(max(0, len(t) - 2))} for t in normalized]
    df = Counter(token for token_set in tokens for token in token_set)
    idf = {token: math.log((1 + len(frame)) / (1 + count)) + 1 for token, count in df.items()}
    postings, exact = defaultdict(list), defaultdict(list)
    for i, row in enumerate(records):
        if normalized[i]:
            exact[(norm_key(row["state"]), normalized[i])].append(i)
        for token in sorted(tokens[i], key=lambda t: (df[t], t))[:3]:
            postings[(norm_key(row["state"]), token)].append(i)
    candidate_indexes = set()
    suppressed_postings = 0
    for indexes in itertools.chain(exact.values(), postings.values()):
        if len(indexes) > 250 and indexes not in exact.values():
            suppressed_postings += 1
            continue
        candidate_indexes.update(itertools.combinations(sorted(indexes), 2))
    nearest = defaultdict(lambda: (0.0, None))
    pairs = []
    for a, b in sorted(candidate_indexes):
        ra, rb = records[a], records[b]
        common = tokens[a] & tokens[b]
        union = tokens[a] | tokens[b]
        weighted = sum(idf[t] for t in common) / sum(idf[t] for t in union) if union else 0
        char = 2 * len(grams[a] & grams[b]) / (len(grams[a]) + len(grams[b])) if grams[a] or grams[b] else 0
        same_text = normalized[a] == normalized[b] and bool(normalized[a])
        similarity = 1.0 if same_text else .65 * weighted + .35 * char
        for left, right in [(a, b), (b, a)]:
            if similarity > nearest[left][0]:
                nearest[left] = (similarity, records[right]["work_id"])
        if similarity < .84:
            continue
        same_ida = ra["ida_key"] == rb["ida_key"]
        same_mp = ra["mp_name_key"] == rb["mp_name_key"]
        same_amount = pd.notna(ra["sanction_amount"]) and ra["sanction_amount"] == rb["sanction_amount"]
        same_date = pd.notna(ra["sanction_date"]) and ra["sanction_date"] == rb["sanction_date"]
        number_tokens_a = set(re.findall(r"\b\d+\b", normalized[a]))
        number_tokens_b = set(re.findall(r"\b\d+\b", normalized[b]))
        number_conflict = bool(number_tokens_a and number_tokens_b and number_tokens_a != number_tokens_b)
        generic = len(tokens[a]) < 4 or len(tokens[b]) < 4
        continuation = bool(ra["description_continuation_flag"] or rb["description_continuation_flag"])
        strong = similarity >= .96 and same_ida and same_amount and same_date and not (number_conflict or generic or continuation)
        strength = "Strong" if strong else ("Moderate" if similarity >= .9 and same_ida and not number_conflict else "Weak")
        pairs.append({
            "work_id_a": ra["work_id"], "work_id_b": rb["work_id"], "similarity": round(similarity, 6),
            "evidence_strength": strength, "exact_description_flag": same_text, "same_ida_flag": same_ida,
            "same_mp_flag": same_mp, "same_amount_flag": same_amount, "same_sanction_date_flag": same_date,
            "number_token_conflict_flag": number_conflict, "generic_description_flag": generic,
            "continuation_or_phase_flag": continuation, "state": ra["state"],
            "description_a": ra["work_description"], "description_b": rb["work_description"],
            "sanction_amount_a": ra["sanction_amount"], "sanction_amount_b": rb["sanction_amount"],
            "sanction_date_a": ra["sanction_date"], "sanction_date_b": rb["sanction_date"],
        })
    counts, strengths = Counter(), defaultdict(lambda: "None")
    strength_order = {"None": 0, "Weak": 1, "Moderate": 2, "Strong": 3}
    for pair in pairs:
        for work_id in (pair["work_id_a"], pair["work_id_b"]):
            counts[work_id] += 1
            if strength_order[pair["evidence_strength"]] > strength_order[strengths[work_id]]:
                strengths[work_id] = pair["evidence_strength"]
    frame["nearest_description_work_id"] = [nearest[i][1] for i in range(len(frame))]
    frame["nearest_description_similarity"] = [round(nearest[i][0], 6) if nearest[i][1] else None for i in range(len(frame))]
    frame["duplicate_candidate_count"] = frame.work_id.map(counts).fillna(0).astype(int)
    frame["near_duplicate_review_flag"] = frame.duplicate_candidate_count.gt(0)
    frame["duplicate_evidence_strength"] = frame.work_id.map(strengths).fillna("None")
    result = pd.DataFrame(pairs)
    if not result.empty:
        result = result.sort_values(["similarity", "work_id_a", "work_id_b"], ascending=[False, True, True])
    return frame, result, {"pairs_examined": len(candidate_indexes), "candidate_pairs": len(pairs),
        "suppressed_common_postings": suppressed_postings, "minimum_similarity": .84,
        "blocking": "Same state plus exact normalized text or one of each record's three rarest informative tokens; token postings over 250 suppressed. Exact blocks retained in full.",
        "similarity": "0.65 IDF-weighted token Jaccard + 0.35 character-trigram Dice. Exact normalized descriptions = 1.",
        "recall_status": "Candidate recall not measured on real audit labels; cross-state and cross-language matches are not searched."}


def isolation_scores(matrix: np.ndarray, seed: int = SEED, tree_count: int = 100, sample_size: int = 256) -> np.ndarray:
    """Isolation Forest following Liu et al. (2008), implemented with NumPy only."""
    rng = np.random.default_rng(seed)
    matrix = np.asarray(matrix, dtype=float)
    medians = np.nanmedian(matrix, axis=0)
    matrix = np.where(np.isnan(matrix), medians, matrix)
    n = min(sample_size, len(matrix))
    if n < 2:
        return np.full(len(matrix), .5)
    max_depth = math.ceil(math.log2(n))

    def c(size):
        if size <= 1:
            return 0.0
        if size == 2:
            return 1.0
        return 2 * (math.log(size - 1) + np.euler_gamma) - 2 * (size - 1) / size

    def tree(train, depth):
        if depth >= max_depth or len(train) <= 1:
            return c(len(train))
        low, high = train.min(axis=0), train.max(axis=0)
        usable = np.flatnonzero(high > low)
        if not len(usable):
            return c(len(train))
        feature = int(rng.choice(usable))
        split = float(rng.uniform(low[feature], high[feature]))
        left = train[:, feature] < split
        return feature, split, tree(train[left], depth + 1), tree(train[~left], depth + 1)

    def walk(node, indexes, depth, total):
        if not isinstance(node, tuple):
            total[indexes] += depth + node
            return
        feature, split, left, right = node
        selected = matrix[indexes, feature] < split
        if selected.any():
            walk(left, indexes[selected], depth + 1, total)
        if (~selected).any():
            walk(right, indexes[~selected], depth + 1, total)

    lengths = np.zeros(len(matrix))
    for _ in range(tree_count):
        root = tree(matrix[rng.choice(len(matrix), n, replace=False)], 0)
        walk(root, np.arange(len(matrix)), 0, lengths)
    return np.power(2, -lengths / tree_count / c(n))


def aggregate_entities(works: pd.DataFrame, key: str, prefix: str) -> pd.DataFrame:
    result = works.groupby(key, dropna=False).agg(**{
        f"{prefix}_visible_work_count": ("work_id", "size"),
        f"{prefix}_visible_sanction_total": ("sanction_amount", lambda x: x.sum(min_count=1)),
        f"{prefix}_median_sanction_amount": ("sanction_amount", "median"),
        f"{prefix}_median_sanction_delay_days": ("sanction_delay_days", "median"),
        f"{prefix}_delay_over45_share": ("potential_sla_over_45_flag", "mean"),
        f"{prefix}_early_stage_over180_share": ("early_stage_age_over_180_flag", "mean"),
        f"{prefix}_completed_share": ("completed_status_flag", "mean"),
        f"{prefix}_high_cost_outlier_share": ("high_cost_outlier_flag", "mean"),
        f"{prefix}_duplicate_review_share": ("near_duplicate_review_flag", "mean"),
        f"{prefix}_average_review_priority_score": ("review_priority_score", "mean"),
        f"{prefix}_max_review_priority_score": ("review_priority_score", "max"),
        f"{prefix}_latest_sanction_date": ("sanction_date", "max"),
        f"{prefix}_distinct_work_type_count": ("work_type", "nunique"),
    }).reset_index()
    hhi = works.groupby(key)["work_type"].apply(lambda x: (x.value_counts(normalize=True) ** 2).sum())
    result[f"{prefix}_work_type_hhi"] = result[key].map(hhi)
    result[f"{prefix}_review_priority_score"] = (
        result[f"{prefix}_average_review_priority_score"] * .7 + result[f"{prefix}_max_review_priority_score"] * .3).round(2)
    result[f"{prefix}_review_priority_band"] = result[f"{prefix}_review_priority_score"].map(priority_band)
    return result


def priority_band(score):
    return "High" if score >= 65 else "Medium" if score >= 40 else "Low" if score >= 20 else "Routine"


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [json_safe(v) for v in value]
    if isinstance(value, (datetime, pd.Timestamp)):
        return None if pd.isna(value) else value.date().isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(value) else None
    return value


def make_dictionary(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    explicit = {
        "sanction_delay_days": ("Sanction date minus supplied recommendation date, in calendar days. Recommendation date is an unverified proxy for IDA receipt date.", "Available at sanction; receipt/MCC caveat"),
        "potential_sla_over_45_flag": ("Calendar-day proxy delay greater than 45. No IDA-receipt timestamp or MCC exclusions supplied; investigate before compliance conclusion.", "Available at sanction; proxy rule"),
        "early_stage_age_over_180_flag": ("Latest observed sanction date minus this sanction date exceeds 180, and current status is Sanction, Vendor Identification or Time Estimation.", "Current status at snapshot only; 180 days is screening threshold"),
        "high_cost_outlier_flag": ("Positive sanctioned amount exceeds leave-current-row-out peer median by at least 2 times and robust z exceeds 3.5. No quantity/unit-cost or revised estimate is supplied.", "Snapshot peers; recompute within training folds"),
        "peer_robust_z": ("(Amount - peer median) / robust scale. Scale is 1.4826 MAD, then IQR/1.349 if MAD zero, then max(10% median, ₹1) for degenerate peers.", "Snapshot peers; current row excluded"),
        "peer_count": ("Number of positive nonmissing amounts in selected state/type, type or global peer group, excluding the current row. Prefer at least 10 peers.", "Snapshot peers; current row excluded"),
        "review_priority_score": ("Capped 0-100 sum of documented rule contributions. Screening priority, never a probability or confirmed fraud outcome.", "Snapshot descriptive; derived target, exclude from predictor inputs"),
        "isolation_forest_score": ("2 to power minus mean isolation path divided by c(sample size), 100 trees, 256-row subsamples, seed 26102; continuous unsupervised atypicality score.", "Fit on full snapshot; not held-out evaluation"),
        "isolation_forest_percentile": ("Average-tie percentile rank of isolation score in this snapshot, multiplied by 100.", "Fit on full snapshot; not held-out evaluation"),
        "observed_sanction_to_allocated_ratio": ("Visible sanctions / recorded allocation limit, whose period is unspecified. Expenditure, release and utilization are not measured.", "Snapshot descriptive; incomplete numerator"),
        "mp_calamity_consent_total": ("Total nonmissing consent amount recorded for joined MP. Zero means no row observed in this consent extract, not proof of no consent.", "Snapshot descriptive; not payment or expenditure"),
        "mp_trust_fy_visible_total": ("Visible Trust and Society sanctions for normalized MP and sanction financial year. Incomplete sanctions are only a proxy for annual recommendations.", "Snapshot descriptive; proxy rule"),
        "potential_trust_annual_limit_flag": ("Visible trust/society sanctions in MP/sanction-FY exceed ₹50 lakh. Sanctions are a proxy for recommendations; legal verification requires complete recommendation history.", "Snapshot descriptive; proxy rule"),
        "potential_limit_breach_flag": ("Consent sum grouped by MP, consent financial year and source calamity type exceeds ₹1 crore national / ₹25 lakh state. Financial year is an explicit annual-basis assumption.", "Snapshot descriptive; rule proxy"),
        "mp_allocated_limit": ("Recorded allocation amount in source export. One source value is missing and remains null. Period and carry-forward composition are unspecified.", "Source snapshot; not annual entitlement"),
        "number_token_conflict_flag": ("Both descriptions contain number tokens and the number-token sets differ. Possible location/quantity difference requiring review.", "Snapshot duplicate context"),
        "source_text_replacement_character_flag": ("Raw work reference/description contains U+FFFD replacement character, indicating source text may be damaged.", "Source quality"),
        "source_worksheet_row": ("Original physical worksheet row, with title/header rows counted. Used to trace evidence directly to the supplied source.", "Provenance; identifier, exclude from model"),
        "work_id": ("Work identifier parsed from WS/MP.../financial-year/work-id-type reference. Stored as an identifier and never treated as a numeric predictive signal.", "Identifier; exclude from model"),
        "mp_code": ("MP code parsed from work reference. Identifier, not a continuous numeric predictor.", "Identifier; exclude from model"),
    }
    source_definitions = {
        "source_row_number": "Sequential row number supplied by the source export, excluding headers and Grand Total.",
        "mp_source_row_number": "Sequential MP allocation row number supplied by the source export.",
        "work_category": "Source category: Normal/Others or Trust and Society. This is not an asset sector.",
        "work_reference": "Unmodified reference from Works Sanctioned column C, containing MP code, reference financial year, work ID and type.",
        "state": "Work's state label from Works Sanctioned column D.",
        "ida_source": "Full implementing district authority label from Works Sanctioned column E.",
        "mp_name": "MP name as written in the relevant source worksheet. It is retained alongside the normalized join key.",
        "constituency": "Constituency label from Works Sanctioned column G.",
        "work_description": "Unmodified source work description from Works Sanctioned column H.",
        "recommended_date": "Parsed dd-Mon-yyyy source date in Works Sanctioned column I. IDA receipt time is not supplied.",
        "sanction_date": "Parsed dd-Mon-yyyy source date in Works Sanctioned column J.",
        "sanction_amount": "Source sanctioned amount in INR from Works Sanctioned column K. It is not recorded expenditure.",
        "work_status": "Current source status from Works Sanctioned column L; no timestamp of last status update is supplied.",
        "mp_state": "MP state from the allocation master, joined by normalized MP name.",
        "mp_constituency": "MP constituency from the allocation master, joined by normalized MP name.",
        "consent_date": "Parsed source consent date from Amount consented for Calamity column E.",
        "consent_amount": "Source consent amount in INR from Amount consented for Calamity column F; not a payment or transfer confirmation.",
        "calamity_type": "Source category National Calamity or State Calamity; official declaration is not supplied.",
        "calamity_name": "Unmodified source event name from Amount consented for Calamity column C.",
    }
    explicit.update({field: (description, "Source snapshot; evidence") for field, description in source_definitions.items()})
    transformed = {
        "work_fiscal_year": "YYYY-YYYY financial-year token parsed from the work reference, retained separately from the date-derived sanction FY.",
        "work_type": "Text following the numeric work ID and hyphen in the source work reference; Unparsed if reference does not match.",
        "ida_district": "Trimmed text before the first opening parenthesis in the full IDA source label. This is a parsed label, not a district-code crosswalk.",
        "ida_authority": "Text inside IDA parentheses, with trailing _IDA removed. It identifies an authority, not an executing vendor.",
        "constituency_reservation": "SC or ST only if present in parentheses in the constituency label; otherwise Unspecified. Does not identify work beneficiary category.",
        "allocation_amount_missing_flag": "True when the source allocation amount is blank or cannot be parsed as numeric. No zero imputation is made.",
        "allocation_join_status": "Matched if the normalized work MP name equals one unique allocation-master key; Unmatched otherwise.",
        "mp_join_status": "Matched if the normalized consent MP name equals one unique allocation-master key; Unmatched otherwise.",
        "state_mp_mismatch_flag": "Normalized work state differs from normalized allocation-master MP state. Context only: permissible out-of-area exceptions may apply.",
        "sanction_fiscal_year": "India financial year (1 April to 31 March) containing the sanction date.",
        "recommended_fiscal_year": "India financial year (1 April to 31 March) containing the recommendation date.",
        "sanction_delay_over_180_flag": "Recommendation-to-sanction calendar-day proxy exceeds 180. This is an analytic screening cutoff.",
        "snapshot_proxy_date": "Maximum nonmissing sanction date in the supplied works extract. It is a reproducible proxy, not certified export time.",
        "age_days_at_snapshot_proxy": "Snapshot proxy date minus sanction date in calendar days; does not measure time since last progress update.",
        "status_stage": "Mapping: Sanction=Sanctioned, Vendor Identification=Procurement, Time Estimation=Planning, Work partially Completed=Execution, Physical Inspection=Verification, Work Completed=Completed; otherwise Unknown.",
        "early_stage_flag": "True for current source status Sanction, Vendor Identification or Time Estimation.",
        "completed_status_flag": "True only when current source status is exactly Work Completed; completion date and certificate are absent.",
        "sanction_month": "Calendar month of sanction, January=1 through December=12.",
        "sanction_fy_quarter": "Financial-year quarter containing sanction: April-June=1, July-September=2, October-December=3, January-March=4.",
        "sanction_in_fy_last_30d_flag": "Sanction date is March 2 through March 31 inclusive, the final 30 calendar days of its FY.",
        "description_normalized": "Unicode NFKC and casefold; punctuation/underscores become spaces; repeated whitespace collapses. Original text remains separate.",
        "description_word_count": "Count of whitespace-delimited tokens in the normalized description.",
        "description_char_count": "Character count of normalized description, including normalized spaces.",
        "description_digit_count": "Number of individual digit characters in normalized description, not number of quantities or locations.",
        "description_continuation_flag": "Normalized description contains a word starting continu, or phase, part, balance or remaining; possible legitimate continuation context.",
        "description_low_information_flag": "Normalized description contains fewer than six words, a screening heuristic.",
        "sanction_amount_lakh": "Sanctioned amount in INR divided by 100,000.",
        "amount_log1p": "Natural logarithm of (1 + sanctioned amount) for nonnegative amounts; otherwise null.",
        "amount_multiple_100k_flag": "Nonmissing sanctioned amount is an exact multiple of ₹100,000. Repeated/rounded grants may be legitimate.",
        "same_amount_mp_frequency": "Count of visible works with exactly the same normalized MP key and numeric sanctioned amount.",
        "sanction_batch_size_mp_date": "Number of visible works with the same normalized MP key and sanction calendar date, including current work.",
        "sanction_batch_total_mp_date": "Sum of known sanctioned amounts for the same normalized MP and sanction date, including current work; null if all amounts missing.",
        "peer_group_level": "First group with at least ten other positive amounts: same state and work type, then same work type, then all works as final fallback.",
        "peer_median_amount": "Median positive nonmissing sanctioned amount in selected peer group after current row is removed.",
        "peer_scale_method": "Indicates whether robust monetary scale uses 1.4826*MAD, IQR/1.349 or max(10% median, ₹1) for degenerate peers.",
        "amount_to_peer_median_ratio": "Current sanctioned amount divided by leave-current-row-out peer median; null when denominator/input unavailable.",
        "nearest_description_work_id": "Highest-similarity other work among examined blocked pairs; null if no pair examined for this work. Not a global nearest neighbor.",
        "nearest_description_similarity": "Similarity to best examined blocked neighbor, which may be below candidate threshold; null if no neighbor examined.",
        "duplicate_candidate_count": "Number of retained examined pairs containing this work with similarity at least 0.84.",
        "near_duplicate_review_flag": "At least one examined pair involving the work meets similarity >=0.84. Does not establish duplicate funding.",
        "duplicate_evidence_strength": "Maximum retained pair evidence: Strong, Moderate, Weak, None. Strong requires >=0.96, same IDA, amount and sanction date, with no number conflict, generic description or continuation cue. Moderate requires >=0.90 and same IDA without number conflict.",
        "mp_latest_calamity_consent_date": "Latest consent date observed for the normalized MP in the consent extract; null if no consent row is observed.",
        "work_amount_share_of_allocation": "Individual visible sanctioned amount divided by positive allocation-master limit; null for missing/nonpositive limit. Denominator period is unknown.",
        "review_priority_band": "High for score >=65; Medium >=40; Low >=20; Routine below20. Fixed investigation workload labels, not measured probabilities.",
        "review_reason_codes": "Semicolon-separated rule codes contributing positive weight to this work's priority.",
        "review_score_contributions_json": "JSON mapping each triggered rule code to its score points. Sum is capped at100 to reproduce review_priority_score.",
        "required_feature_input_missing_count": "Number of nulls among parsed work ID, recommendation date, sanction date, amount, normalized MP key and normalized IDA key.",
        "invalid_date_order_flag": "Sanction date precedes supplied recommendation date.",
        "source_work_id_duplicate_flag": "Parsed work ID occurs in more than one source work row; all such rows are flagged.",
        "works_extract_presence_flag": "Allocation-master MP has at least one joined row in the supplied works extract.",
        "consent_fiscal_year": "India financial year (April-March) containing consent date; explicit annual aggregation basis assumption.",
        "consent_calendar_year": "Calendar year containing consent date, retained separately from consent financial year.",
        "rule_limit": "₹10,000,000 for National Calamity and ₹2,500,000 for State Calamity; null for unknown source type. Eligibility must be verified separately.",
        "mp_fy_type_total": "Sum of known consent amounts for same normalized MP, consent financial year and calamity type; null when all amounts missing.",
        "state_calamity_eligibility_check": "Not assessed because official declaration, affected-area jurisdiction and MP chamber are not available in the three inputs.",
        "work_id_a": "Parsed ID of first work in this unordered candidate pair.",
        "work_id_b": "Parsed ID of second work in this unordered candidate pair; different from work_id_a.",
        "similarity": "0.65 times IDF-weighted informative-token Jaccard plus0.35 times character-trigram Dice; exact nonempty normalized text is1. Stored pairs meet >=0.84.",
        "evidence_strength": "Strong: similarity>=0.96, same IDA/amount/date, no number-token conflict, neither generic nor continuation. Moderate: similarity>=0.90, same IDA, no number conflict. Remaining candidates Weak.",
        "exact_description_flag": "Nonempty normalized descriptions are exactly equal.",
        "same_ida_flag": "Both work rows have the same normalized state-and-IDA key.",
        "same_mp_flag": "Both work rows have the same normalized MP-name key.",
        "same_amount_flag": "Both candidate amounts are nonmissing and numerically equal.",
        "same_sanction_date_flag": "Both candidate sanction dates are nonmissing and equal.",
        "generic_description_flag": "Either description contains fewer than four distinct informative tokens after declared stop-word removal.",
        "continuation_or_phase_flag": "Either description has a continuation/phase cue; potential legitimate staged work.",
        "description_a": "Unmodified description of work_id_a.", "description_b": "Unmodified description of work_id_b.",
        "sanction_amount_a": "Source sanctioned amount in INR for work_id_a.", "sanction_amount_b": "Source sanctioned amount in INR for work_id_b.",
        "sanction_date_a": "Source sanction date for work_id_a.", "sanction_date_b": "Source sanction date for work_id_b.",
    }
    explicit.update({field: (description, "Source-derived snapshot; recompute features in historical folds") for field, description in transformed.items()})
    rows = []
    for table_name, table in tables.items():
        for field in table.columns:
            definition, timing = explicit.get(field, DEFINITIONS.get(field, ("", "")))
            if not definition:
                if "prior" in field or "previous_sanction" in field:
                    definition = {"prior_work_count": "Visible work count with sanction date strictly before the current sanction date.",
                        "prior_sanction_total": "Visible sanctioned amount with date strictly before current date. Zero only when no historical row is observed.",
                        "previous_sanction_date": "Latest visible sanction date strictly earlier than current date.",
                        "days_since_previous_sanction": "Current sanction date minus latest strictly earlier visible sanction date, null if none.",
                        "prior90d_work_count": "Visible sanction count in [current sanction date - 90 days, current sanction date)."}.get(re.sub(r"^(mp|ida)_", "", field), field.replace("_", " "))
                    timing = "Strictly before sanction date, observed extract only"
                elif field.endswith("_share"):
                    definition = "Proportion among this entity's visible work rows meeting " + field.replace("mp_", "").replace("ida_", "").replace("_share", "").replace("_", " ") + ". Entity with no observed works has null share."
                    timing = "Snapshot entity aggregate; recompute inside train folds"
                elif field.endswith("_hhi"):
                    definition, timing = "Sum of squared visible work-count shares across work types, in [0,1]; high concentration alone is not misconduct.", "Snapshot entity aggregate"
                elif field.endswith("_count") or field.endswith("_total") or field.endswith("_score") or field.endswith("_band"):
                    definition, timing = field.replace("_", " ") + "; observed supplied extract only.", "Snapshot descriptive"
                else:
                    definition, timing = field.replace("_", " ") + ". See pipeline implementation for deterministic transformation and source mapping.", "Source or snapshot descriptive"
            if field in ("mp_name_key", "ida_key"):
                definition = "Deterministic normalized join key; names use Unicode NFKC/case folding, honorific-prefix removal and punctuation/space removal. IDA key includes state. Ambiguous MP keys stop the build."
                timing = "Join identifier; exclude as continuous predictor"
            rows.append({"table": table_name, "field": field, "dtype": str(table[field].dtype), "definition": definition, "availability_and_caution": timing})
    return pd.DataFrame(rows)


def build(input_dir: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    hashes_before = {name: hashlib.sha256((input_dir / filename).read_bytes()).hexdigest() for name, filename in SOURCES.items()}
    source = {name: source_rows(input_dir / filename) for name, filename in SOURCES.items()}
    wr, wt = source["works"]
    ar, at = source["allocations"]
    cr, ct = source["consents"]
    mapping = {"A": "source_row_number", "_xlsx_row": "source_worksheet_row", "B": "work_category", "C": "work_reference", "D": "state", "E": "ida_source", "F": "mp_name", "G": "constituency", "H": "work_description", "I": "recommended_date", "J": "sanction_date", "K": "sanction_amount", "L": "work_status"}
    works = pd.DataFrame(wr).rename(columns=mapping)[list(mapping.values())]
    works["source_row_number"] = works.source_row_number.astype(int)
    works["sanction_amount"] = pd.to_numeric(works.sanction_amount, errors="coerce")
    works["recommended_date"] = dates(works.recommended_date)
    works["sanction_date"] = dates(works.sanction_date)
    extracted = works.work_reference.str.extract(r"WS/\s*MP\s*(\d+)/(\d{4}-\d{4})/(\d+)-(.*)", expand=True)
    works["mp_code"] = pd.to_numeric(extracted[0], errors="coerce").astype("Int64")
    works["work_fiscal_year"] = extracted[1]
    works["work_id"] = pd.to_numeric(extracted[2], errors="coerce").astype("Int64")
    works["work_type"] = extracted[3].fillna("Unparsed").str.strip()
    works["mp_name_key"] = works.mp_name.map(mp_key)
    works["ida_key"] = works.state.map(norm_key) + "|" + works.ida_source.map(norm_key)
    works["ida_district"] = works.ida_source.str.split("(", regex=False).str[0].str.strip()
    works["ida_authority"] = works.ida_source.str.extract(r"\((.*)\)", expand=False).str.replace(r"_IDA$", "", regex=True)
    works["constituency_reservation"] = works.constituency.str.extract(r"\((SC|ST)\)", expand=False).fillna("Unspecified")
    allocations = pd.DataFrame(ar).rename(columns={"A": "mp_source_row_number", "_xlsx_row": "source_worksheet_row", "B": "mp_state", "C": "mp_name", "D": "mp_constituency", "E": "mp_allocated_limit"})
    allocations["mp_allocated_limit"] = pd.to_numeric(allocations.mp_allocated_limit, errors="coerce")
    allocations["mp_name_key"] = allocations.mp_name.map(mp_key)
    allocations["allocation_amount_missing_flag"] = allocations.mp_allocated_limit.isna()
    if allocations.mp_name_key.duplicated().any():
        raise ValueError("Normalized MP key collision: manual resolution needed before joins")
    works = works.merge(allocations[["mp_name_key", "mp_state", "mp_constituency", "mp_allocated_limit", "allocation_amount_missing_flag"]], on="mp_name_key", how="left", validate="many_to_one", indicator=True)
    works["allocation_join_status"] = works.pop("_merge").map({"both": "Matched", "left_only": "Unmatched", "right_only": "Unused"}).astype(str)
    works["state_mp_mismatch_flag"] = works.state.map(norm_key).ne(works.mp_state.map(norm_key))
    works["sanction_fiscal_year"] = works.sanction_date.map(fiscal_year)
    works["recommended_fiscal_year"] = works.recommended_date.map(fiscal_year)
    works["sanction_delay_days"] = (works.sanction_date - works.recommended_date).dt.days
    works["potential_sla_over_45_flag"] = works.sanction_delay_days.gt(45).where(works.sanction_delay_days.notna())
    works["sanction_delay_over_180_flag"] = works.sanction_delay_days.gt(180).where(works.sanction_delay_days.notna())
    snapshot = works.sanction_date.max()
    works["snapshot_proxy_date"] = snapshot
    works["age_days_at_snapshot_proxy"] = (snapshot - works.sanction_date).dt.days
    works["status_stage"] = works.work_status.map(STATUS_STAGE).fillna("Unknown")
    works["early_stage_flag"] = works.work_status.isin(EARLY_STATUSES)
    works["early_stage_age_over_180_flag"] = (works.early_stage_flag & works.age_days_at_snapshot_proxy.gt(180)).where(works.age_days_at_snapshot_proxy.notna())
    works["completed_status_flag"] = works.work_status.eq("Work Completed")
    works["sanction_month"] = works.sanction_date.dt.month
    works["sanction_fy_quarter"] = ((works.sanction_date.dt.month - 4) % 12 // 3 + 1).astype("Int64")
    works["sanction_in_fy_last_30d_flag"] = works.sanction_date.dt.month.eq(3) & works.sanction_date.dt.day.ge(2)
    works["description_normalized"] = works.work_description.map(norm_text)
    works["description_word_count"] = works.description_normalized.str.split().str.len()
    works["description_char_count"] = works.description_normalized.str.len()
    works["description_digit_count"] = works.description_normalized.str.count(r"\d")
    works["description_continuation_flag"] = works.description_normalized.str.contains(r"\b(?:continu\w*|phase|part|balance|remaining)\b", regex=True)
    works["description_low_information_flag"] = works.description_word_count.lt(6)
    works["source_text_replacement_character_flag"] = works.work_reference.str.contains("\ufffd", regex=False) | works.work_description.fillna("").str.contains("\ufffd", regex=False)
    works["sanction_amount_lakh"] = works.sanction_amount / 100000
    works["amount_log1p"] = np.log1p(works.sanction_amount.where(works.sanction_amount.ge(0)))
    works["amount_multiple_100k_flag"] = works.sanction_amount.mod(100000).eq(0).where(works.sanction_amount.notna())
    works["same_amount_mp_frequency"] = works.groupby(["mp_name_key", "sanction_amount"], dropna=False).work_id.transform("size")
    batch = works.groupby(["mp_name_key", "sanction_date"], dropna=False)
    works["sanction_batch_size_mp_date"] = batch.work_id.transform("size")
    works["sanction_batch_total_mp_date"] = batch.sanction_amount.transform(lambda x: x.sum(min_count=1))
    print("Raw ingest and deterministic fields complete", flush=True)
    works = prior_history(prior_history(works, "mp_name_key", "mp"), "ida_key", "ida")
    works = peer_features(works)
    print("Prior history and leave-one-out peers complete", flush=True)
    works, pairs, duplicate_audit = duplicate_features(works)
    print(f"Duplicate candidates: {len(pairs)}", flush=True)
    consents = pd.DataFrame(cr).rename(columns={"A": "source_row_number", "_xlsx_row": "source_worksheet_row", "B": "calamity_type", "C": "calamity_name", "D": "mp_name", "E": "consent_date", "F": "consent_amount"})
    consents["mp_name_key"] = consents.mp_name.map(mp_key)
    consents["consent_date"] = dates(consents.consent_date)
    consents["consent_amount"] = pd.to_numeric(consents.consent_amount, errors="coerce")
    consents["consent_fiscal_year"] = consents.consent_date.map(fiscal_year)
    consents["consent_calendar_year"] = consents.consent_date.dt.year
    consents = consents.merge(allocations[["mp_name_key", "mp_state", "mp_constituency", "mp_allocated_limit"]], on="mp_name_key", how="left", validate="many_to_one", indicator=True)
    consents["mp_join_status"] = consents.pop("_merge").map({"both": "Matched", "left_only": "Unmatched", "right_only": "Unused"}).astype(str)
    consents["rule_limit"] = consents.calamity_type.map({"National Calamity": 10000000, "State Calamity": 2500000})
    consents["mp_fy_type_total"] = consents.groupby(["mp_name_key", "consent_fiscal_year", "calamity_type"], dropna=False).consent_amount.transform(lambda x: x.sum(min_count=1))
    consents["potential_limit_breach_flag"] = consents.mp_fy_type_total.gt(consents.rule_limit).where(consents.rule_limit.notna() & consents.mp_fy_type_total.notna())
    consents["state_calamity_eligibility_check"] = "Not assessed: declaration, MP chamber and affected-area jurisdiction unavailable"
    calamity = consents.groupby("mp_name_key").agg(mp_calamity_consent_count=("consent_amount", "size"), mp_calamity_consent_total=("consent_amount", lambda x: x.sum(min_count=1)), mp_latest_calamity_consent_date=("consent_date", "max"))
    works = works.merge(calamity, on="mp_name_key", how="left", validate="many_to_one")
    works["mp_calamity_consent_count"] = works.mp_calamity_consent_count.fillna(0).astype(int)
    works.loc[works.mp_calamity_consent_count.eq(0), "mp_calamity_consent_total"] = 0
    trust = works[works.work_category.eq("Trust and Society")].groupby(["mp_name_key", "sanction_fiscal_year"]).sanction_amount.sum(min_count=1)
    works["mp_trust_fy_visible_total"] = [trust.get((m, fy), 0) for m, fy in zip(works.mp_name_key, works.sanction_fiscal_year)]
    works["potential_trust_annual_limit_flag"] = works.mp_trust_fy_visible_total.gt(5000000)
    works["work_amount_share_of_allocation"] = [divide(a, b) for a, b in zip(works.sanction_amount, works.mp_allocated_limit)]
    matrix = np.column_stack([works.amount_log1p, np.log1p(works.sanction_delay_days.clip(lower=0)), works.age_days_at_snapshot_proxy, works.description_char_count, works.sanction_batch_size_mp_date])
    works["isolation_forest_score"] = isolation_scores(matrix)
    works["isolation_forest_percentile"] = works.isolation_forest_score.rank(pct=True) * 100
    rules = [
        {"code": "SLA_GT_45", "weight": 6, "definition": "Recommendation-to-sanction proxy >45 calendar days", "caution": "IDA receipt/MCC exclusions unavailable"},
        {"code": "DELAY_GT_180", "weight": 10, "definition": "Proxy sanction delay >180 days, in addition to 45-day signal", "caution": "Screening threshold"},
        {"code": "EARLY_STAGE_AGED", "weight": 15, "definition": "Early source status and >180 days since sanction at snapshot proxy", "caution": "No status-update timestamp"},
        {"code": "HIGH_PEER_AMOUNT", "weight": 25, "definition": "Amount >=2x peer median and robust z>3.5", "caution": "No unit quantity or actual cost overrun"},
        {"code": "DUPLICATE_STRONG", "weight": 25, "definition": "Strongest linked duplicate evidence is Strong", "caution": "Distinct locations/legitimate installments require review"},
        {"code": "DUPLICATE_MODERATE", "weight": 12, "definition": "Strongest linked duplicate evidence is Moderate", "caution": "Text similarity only"},
        {"code": "DUPLICATE_WEAK", "weight": 4, "definition": "Strongest linked duplicate evidence is Weak", "caution": "Text similarity only"},
        {"code": "UNSUPERVISED_TOP_1PCT", "weight": 8, "definition": "Isolation-forest percentile >=99", "caution": "Full-snapshot fit; no fraud ground truth"},
        {"code": "TRUST_ANNUAL_PROXY", "weight": 12, "definition": "Visible MP/sanction-FY Trust and Society amount >₹50 lakh", "caution": "Sanctions proxy recommendations"},
    ]
    weights = {r["code"]: r["weight"] for r in rules}
    scores, reasons, contributions = [], [], []
    for r in works.to_dict("records"):
        flags = {"SLA_GT_45": r["potential_sla_over_45_flag"], "DELAY_GT_180": r["sanction_delay_over_180_flag"],
            "EARLY_STAGE_AGED": r["early_stage_age_over_180_flag"], "HIGH_PEER_AMOUNT": r["high_cost_outlier_flag"],
            "DUPLICATE_STRONG": r["duplicate_evidence_strength"] == "Strong", "DUPLICATE_MODERATE": r["duplicate_evidence_strength"] == "Moderate",
            "DUPLICATE_WEAK": r["duplicate_evidence_strength"] == "Weak", "UNSUPERVISED_TOP_1PCT": r["isolation_forest_percentile"] >= 99,
            "TRUST_ANNUAL_PROXY": r["potential_trust_annual_limit_flag"]}
        selected = {code: weights[code] for code, present in flags.items() if pd.notna(present) and bool(present)}
        scores.append(min(100, sum(selected.values())))
        reasons.append(";".join(selected))
        contributions.append(json.dumps(selected, sort_keys=True))
    works["review_priority_score"] = scores
    works["review_priority_band"] = works.review_priority_score.map(priority_band)
    works["review_reason_codes"] = reasons
    works["review_score_contributions_json"] = contributions
    missing_columns = ["work_id", "recommended_date", "sanction_date", "sanction_amount", "mp_name_key", "ida_key"]
    works["required_feature_input_missing_count"] = works[missing_columns].isna().sum(axis=1)
    works["invalid_date_order_flag"] = works.sanction_delay_days.lt(0)
    works["source_work_id_duplicate_flag"] = works.work_id.duplicated(keep=False)
    mp = allocations.merge(aggregate_entities(works, "mp_name_key", "mp"), on="mp_name_key", how="left", validate="one_to_one")
    mp["works_extract_presence_flag"] = mp.mp_visible_work_count.notna()
    # A zero count is observed absence. Rates and amount sums for absent entities remain null.
    mp["mp_visible_work_count"] = mp.mp_visible_work_count.fillna(0).astype(int)
    mp["observed_sanction_to_allocated_ratio"] = [divide(a, b) for a, b in zip(mp.mp_visible_sanction_total, mp.mp_allocated_limit)]
    mp = mp.merge(calamity, on="mp_name_key", how="left", validate="one_to_one")
    mp["mp_calamity_consent_count"] = mp.mp_calamity_consent_count.fillna(0).astype(int)
    mp.loc[mp.mp_calamity_consent_count.eq(0), "mp_calamity_consent_total"] = 0
    ida = aggregate_entities(works, "ida_key", "ida").merge(works[["ida_key", "state", "ida_district", "ida_authority"]].drop_duplicates("ida_key"), on="ida_key", validate="one_to_one")
    ida["ida_visible_mp_count"] = ida.ida_key.map(works.groupby("ida_key").mp_name_key.nunique())
    tables = {"Work_Features": works, "MP_Features": mp, "IDA_Features": ida, "Calamity_Features": consents, "Duplicate_Candidates": pairs}
    dictionary = make_dictionary(tables)
    tables["Feature_Dictionary"] = dictionary
    totals = {
        "works": {"records": len(wr), "visible_sum": str(exact_sum(wr, "K")), "reported_total": wt.get("L"), "grand_total_cell": f"L{wt['_xlsx_row']}"},
        "allocations": {"records": len(ar), "visible_sum": str(exact_sum(ar, "E")), "reported_total": at.get("E"), "grand_total_cell": f"E{at['_xlsx_row']}"},
        "consents": {"records": len(cr), "visible_sum": str(exact_sum(cr, "F")), "reported_total": ct.get("F"), "grand_total_cell": f"F{ct['_xlsx_row']}"},
    }
    for value in totals.values():
        value["difference_reported_minus_visible"] = str(Decimal(value["reported_total"]) - Decimal(value["visible_sum"]))
    hashes_after = {name: hashlib.sha256((input_dir / filename).read_bytes()).hexdigest() for name, filename in SOURCES.items()}
    checks = {
        "raw_sources_sha256_unchanged": hashes_before == hashes_after,
        "works_rows_preserved": len(works) == len(wr),
        "allocation_rows_preserved": len(mp) == len(ar),
        "consent_rows_preserved": len(consents) == len(cr),
        "unique_nonmissing_work_ids": works.work_id.notna().all() and not works.work_id.duplicated().any(),
        "unique_allocation_mp_keys": not allocations.mp_name_key.duplicated().any(),
        "work_mp_join_complete": works.allocation_join_status.eq("Matched").all(),
        "consent_mp_join_complete": consents.mp_join_status.eq("Matched").all(),
        "allocation_exact_total_reconciles": Decimal(totals["allocations"]["difference_reported_minus_visible"]) == 0,
        "consent_exact_total_reconciles": Decimal(totals["consents"]["difference_reported_minus_visible"]) == 0,
        "amount_conserved_after_joins": np.isclose(works.sanction_amount.sum(), float(exact_sum(wr, "K")), atol=.01, rtol=0),
        "mp_aggregate_amount_conserved": np.isclose(mp.mp_visible_sanction_total.sum(), float(exact_sum(wr, "K")), atol=.01, rtol=0),
        "ida_aggregate_amount_conserved": np.isclose(ida.ida_visible_sanction_total.sum(), float(exact_sum(wr, "K")), atol=.01, rtol=0),
        "strict_mp_prior_dates": ((works.mp_previous_sanction_date < works.sanction_date) | works.mp_previous_sanction_date.isna()).all(),
        "strict_ida_prior_dates": ((works.ida_previous_sanction_date < works.sanction_date) | works.ida_previous_sanction_date.isna()).all(),
        "scores_in_0_100": works.review_priority_score.between(0, 100).all(),
        "score_contributions_reconcile": all(min(100, sum(json.loads(c).values())) == s for c, s in zip(works.review_score_contributions_json, works.review_priority_score)),
        "no_self_duplicate_pairs": pairs.empty or not pairs.work_id_a.eq(pairs.work_id_b).any(),
        "no_repeated_duplicate_pairs": pairs.empty or not pairs[["work_id_a", "work_id_b"]].duplicated().any(),
    }
    audit = {
        "pipeline_version": VERSION, "generated_at_utc": datetime.now(timezone.utc).isoformat(), "random_seed": SEED,
        "snapshot_proxy": snapshot.date().isoformat(), "sources": {name: {"file": SOURCES[name], "sha256": digest} for name, digest in hashes_before.items()},
        "source_reconciliation": totals, "checks": checks,
        "work_mp_join_coverage": float(works.allocation_join_status.eq("Matched").mean()),
        "consent_mp_join_coverage": float(consents.mp_join_status.eq("Matched").mean()),
        "visible_works_value_fraction": float(exact_sum(wr, "K") / Decimal(wt["L"])),
        "data_quality": {"allocation_amount_missing": int(allocations.mp_allocated_limit.isna().sum()),
            "work_required_input_missing_rows": int(works.required_feature_input_missing_count.gt(0).sum()),
            "work_source_replacement_character_rows": int(works.source_text_replacement_character_flag.sum()),
            "negative_date_order_rows": int(works.invalid_date_order_flag.sum()),
            "unknown_status_rows": int(works.status_stage.eq("Unknown").sum()),
            "mp_profiles_without_visible_works": int(mp.mp_visible_work_count.eq(0).sum())},
        "screening_counts": {"potential_delay_over45": int(works.potential_sla_over_45_flag.sum()), "early_stage_over180": int(works.early_stage_age_over_180_flag.sum()),
            "high_peer_amount": int(works.high_cost_outlier_flag.sum()), "duplicate_candidate_works": int(works.near_duplicate_review_flag.sum()),
            "priority_bands": works.review_priority_band.value_counts().to_dict()},
        "duplicate_method": duplicate_audit,
        "model": {"name": "Isolation Forest (local NumPy implementation)", "trees": 100, "subsample_size": 256, "seed": SEED,
            "features": ["amount_log1p", "log1p(nonnegative sanction_delay_days)", "age_days_at_snapshot_proxy", "description_char_count", "sanction_batch_size_mp_date"],
            "fit_scope": "Full supplied snapshot; operational descriptive score, not out-of-sample performance", "paper": "https://cs.nju.edu.cn/zhouzh/zhouzh.files/publication/icdm08b.pdf"},
        "limitations": [
            "The works extract has exactly 10,000 records and only 12.75% of its reported sanctioned value. Counts/totals reflect this extract, not complete scheme coverage.",
            "Sanctioned amounts and consent amounts are not expenditure, payments, released funds, or measured utilization.",
            "Cost signals compare whole sanctioned amounts. Work quantities, estimates/revisions, unit rates and specifications are absent; cost overruns cannot be measured.",
            "There are no audit outcomes or fraud labels. Screening priority has no validated fraud probability.",
            "No MP-ID crosswalk exists for the allocation/consent tables. Deterministic normalized names are used and duplicate master keys stop the build.",
            "Missing values remain null. MPs with no visible works have observed work count zero and null amount/rate profiles.",
            "The 45-day proxy lacks IDA receipt dates and Model Code of Conduct exclusions. 180-day aging is an analytic choice, not a statutory completion deadline.",
            "Latest sanction date is a snapshot proxy. Progress-update, actual-start and completion timestamps are absent.",
            "Peer, duplicate, batch, entity and isolation-forest features use the supplied snapshot; rebuild inside temporal training folds for predictive use.",
            "Calamity annual aggregation assumes consent financial year. Legal annual-basis interpretation and declaration/eligibility documents require verification.",
            "Trust annual screening uses sanctions rather than the complete recommendation ledger. Particular-trust term ceilings cannot be assessed without entity IDs and term history.",
            "SC/ST beneficiary targeting, vendor collusion, duplicate invoices, geospatial/ghost assets, and project cost overruns cannot be validated from these inputs.",
            "Constituency reservation labels do not identify the beneficiary community of a work. State mismatches are contextual, not proof of geographic non-compliance.",
        ],
        "rules_sources": [GUIDELINES, PARLIAMENT],
    }
    for name, table in tables.items():
        table.to_csv(output_dir / f"{name}.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    dictionary.to_csv(output_dir / "feature_dictionary.csv", index=False, encoding="utf-8-sig")
    snapshot_payload = {"meta": {"pipelineVersion": VERSION, "snapshot": audit["snapshot_proxy"], "sourceFiles": audit["sources"],
        "reportedWorksTotal": float(wt["L"]), "visibleWorksTotal": float(exact_sum(wr, "K")), "allocationTotal": float(exact_sum(ar, "E")),
        "calamityTotal": float(exact_sum(cr, "F")), "counts": {name: len(table) for name, table in tables.items()},
        "bands": audit["screening_counts"]["priority_bands"], "guidelines": GUIDELINES},
        "tables": {name: {"columns": list(table.columns), "rows": table.values.tolist()} for name, table in tables.items()}, "rules": rules, "audit": audit}
    (output_dir / "snapshot.json").write_text(json.dumps(json_safe(snapshot_payload), ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    (output_dir / "audit.json").write_text(json.dumps(json_safe(audit), indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    report = ["# MPLADS raw-to-features quality report", "", f"Pipeline: {VERSION}", f"Snapshot proxy: {audit['snapshot_proxy']}", "",
        "## Source reconciliation", "", "| Source | Records | Visible amount (INR) | Reported total (INR) | Difference |", "|---|---:|---:|---:|---:|"]
    for name, value in totals.items():
        report.append(f"| {name} | {value['records']:,} | {value['visible_sum']} | {value['reported_total']} | {value['difference_reported_minus_visible']} |")
    report += ["", "## Validation", ""] + [f"- {name}: {bool(value)}" for name, value in checks.items()]
    report += ["", "## Source quality and signals", "", "```json", json.dumps(json_safe({"data_quality": audit["data_quality"], "screening_counts": audit["screening_counts"], "duplicate_method": duplicate_audit}), indent=2), "```", "", "## Limitations", ""]
    report += [f"- {text}" for text in audit["limitations"]]
    report += ["", "## Sources", "", f"- [MPLADS Guidelines 2023]({GUIDELINES})", f"- [Parliamentary reply on salient features]({PARLIAMENT})", "- [Isolation Forest, Liu et al. 2008](https://cs.nju.edu.cn/zhouzh/zhouzh.files/publication/icdm08b.pdf)", "", "Source SHA256 values are recorded in audit.json. All source checksums are compared before and after processing."]
    (output_dir / "QA_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(json_safe({"checks": checks, "data_quality": audit["data_quality"], "screening": audit["screening_counts"], "tables": {name: [len(table), len(table.columns)] for name, table in tables.items()}}), indent=2), flush=True)
    if not all(checks.values()):
        raise AssertionError("One or more output validation checks failed; see audit.json")
    return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path(__file__).resolve().parent.parent / "Dataset")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "artifacts")
    arguments = parser.parse_args()
    build(arguments.input_dir, arguments.output_dir)
