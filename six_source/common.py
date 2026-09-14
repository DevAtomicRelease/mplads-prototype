"""Shared, versioned contracts for the six-source MPLADS solution."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VERSION = "six-source-2026-09-09-v2"
AS_OF = "2026-09-09"
SEED = 26102
FILES = {
    "allocations": "01_allocated_limit.csv", "consents": "02_calamity_consent.csv",
    "recommended": "03_works_recommended.csv", "sanctioned": "04_works_sanctioned.csv",
    "completed": "05_works_completed.csv", "payments": "06_expenditure.csv",
}
EXPECTED = {
    "allocations": (543, "da79d9fecefcff66670dd4b656f1d624b1feee0f2c5560800fd5b77bb14a696b"),
    "consents": (12, "c653f3d0ebde00baabbd9fa375f830dc9c6755a5462e838ecbf514a2d35da373"),
    "recommended": (107562, "f396f91ad15e0f63aae25e8171481e29007ad0c0632caed2cfd5b03c36e1c4a2"),
    "sanctioned": (79881, "8b31c7f7c335458719d8db447d5b53f407f72f66d56f434aaa7cff3a14c476d5"),
    "completed": (34940, "458edd98ddc5b2c4b9b713aca5f81333661775758073d2827058db2621c96139"),
    "payments": (57349, "bba2f79a9c5390a7e3a3ccada22282d3b223ea8f365991bbdd5a5b7a5637086f"),
}
SOURCES = [
    {"id": "PS", "title": "SIH PS 26102 (supplied problem statement)", "date": "2026", "url": "https://www.sih.gov.in/sih2026PS", "use": "Anomaly investigation, financial and execution monitoring, explainability and accountable review."},
    {"id": "PORTAL", "title": "MoSPI: revamped eSAKSHI public dashboard", "date": "2026-03-06", "url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2235932&lang=1&reg=3", "use": "Recommendations, sanctions, completions and vendor expenditure describe different stages. Live portal updates do not establish synchronized CSV extraction timestamps."},
    {"id": "MONITOR", "title": "MoSPI: eSAKSHI monitoring and pendency", "date": "2025-08-06", "url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2153066&lang=2&reg=48", "use": "Receipt-based 45-day decisions, generally one-year completion and three-month no-payment monitoring; contractual exceptions and missing receipt dates limit compliance claims."},
    {"id": "FUND", "title": "MoSPI: revised fund authorization", "date": "2025-08-11", "url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2155040&lang=2&reg=48", "use": "Annual INR 5 crore entitlement authorized in one instalment since April 2023. Allocation snapshot is not an annual bank balance."},
    {"id": "RULES", "title": "MPLADS Guidelines April 2023", "date": "2023-04-01", "url": "https://mplads.gov.in/MPLADS/UploadedFiles/MPLADSGuidelinesApril2023.pdf", "use": "Official guideline location; repeated fetch timeouts in this run. Do not activate unverified trust/geography thresholds; obtain scheme-owner effective-rule sign-off."},
    {"id": "IFOREST", "title": "Liu, Ting and Zhou: Isolation Forest", "date": "2008", "url": "https://cs.nju.edu.cn/zhouzh/zhouzh.files/publication/icdm08b.pdf", "use": "Random isolation paths measure atypicality, not fraud probability. Local NumPy implementation; seeded and versioned."},
    {"id": "LEAKAGE", "title": "scikit-learn: common pitfalls", "date": "accessed 2026-09-09", "url": "https://scikit-learn.org/stable/common_pitfalls.html", "use": "Separate fitting and evaluation data; do not tune detection on held-out cases. Retrospective snapshot scores are not forecasts."},
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def norm(value):
    if value is None or pd.isna(value):
        return ""
    value = unicodedata.normalize("NFKC", str(value)).casefold()
    return " ".join(re.sub(r"[^\w\s]", " ", value.replace("_", " ")).split())


def name_key(value):
    value = re.sub(r"^(?:(?:shri|sri|shree|smt|shrimati|dr|prof|adv|honble)\s+)+", "", norm(value))
    return value.replace(" ", "")


def mp_key(frame):
    return frame.HOUSE_OF_PARLIAMENT + "|" + frame.TENURE + "|" + frame.MP_NAME.map(name_key)


def paise(value):
    if value is None or str(value).strip() in {"", "NA"}:
        return None
    try:
        exact = Decimal(str(value).strip()) * 100
    except InvalidOperation as exc:
        raise ValueError("Invalid monetary value") from exc
    require(exact.is_finite() and exact == exact.to_integral_value(), "Money is not finite whole paise")
    return int(exact)


def money(series):
    return series.map(paise).astype("Int64")


def dates(series):
    cleaned = series.replace({"": None, "NA": None})
    parsed = pd.to_datetime(cleaned, format="%d-%b-%Y", errors="coerce")
    require(not (cleaned.notna() & parsed.isna()).any(), "Unrecognized nonmissing event date")
    return parsed


def fy(series):
    year = series.dt.year - series.dt.month.lt(4).astype(int)
    return year.astype("Int64").astype(str) + "-" + (year + 1).astype("Int64").astype(str)


def ratio(a, b):
    return a.astype(float).div(b.astype(float).where(b.astype(float).gt(0))).replace([np.inf, -np.inf], np.nan)


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    if isinstance(value, (float, np.floating)):
        return None if not np.isfinite(value) else float(value)
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(pd.Timestamp(value).date())
    return value


def write_json(path, payload):
    Path(path).write_text(json.dumps(json_safe(payload), ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def to_records(frame):
    return json_safe(frame.astype(object).where(frame.notna(), None).to_dict("records"))
