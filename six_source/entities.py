"""Read-only entity profiles and conservative local name resolution.

No fuzzy ranking or external model: return all ambiguous matches for user choice.
Work aggregates use a distinct work grain; vendor payments are never multiplied.
"""
from __future__ import annotations
import re

ENTITIES = {
    "ida": ("IDA_Features", "ida_key", "ida_name"),
    "mp": ("MP_Features", "mp_key", "mp_name"),
    "vendor": ("Vendor_Features", "vendor_id", "vendor_name"),
}


def normalized(value):
    return " ".join(re.sub(r"[\W_]+", " ", value.casefold()).split())


def resolve_names(db, question, aliases=False):
    text = " " + normalized(question) + " "
    exact, short = [], []
    for kind, (table, key, name) in ENTITIES.items():
        for row in db.execute(f'SELECT "{key}", "{name}" FROM "{table}"'):
            label = str(row[1] or "").strip()
            full = normalized(label)
            match = {"kind": kind, "key": str(row[0]), "name": label}
            if len(full) >= 4 and " " + full + " " in text:
                exact.append(match)
            elif aliases and kind == "ida":
                alias = normalized(label.split("(")[0])
                if len(alias) >= 4 and " " + alias + " " in text:
                    short.append(match)
    # A full legal name wins over its district abbreviation, but multiple full
    # matches are still ambiguous. Never silently pick the first matching person.
    return exact or short


def profile(db, kind, key):
    if kind not in ENTITIES or len(key) > 300:
        raise ValueError("Unknown entity kind or invalid key")
    table, column, name = ENTITIES[kind]
    found = db.execute(f'SELECT * FROM "{table}" WHERE "{column}"=?', [key]).fetchone()
    if found is None:
        return None
    where = f'"{column}"=?' if kind != "vendor" else 'work_id IN (SELECT DISTINCT work_id FROM Payment_Features WHERE vendor_id=?)'
    aggregate = "COUNT(*) works, SUM(in_sanctioned) sanctioned, SUM(in_completed) completed, SUM(CASE WHEN priority_band IN ('High','Critical') THEN 1 ELSE 0 END) high, SUM(open_over_one_year_flag) open_over_year, SUM(no_payment_three_months_flag) no_payment_3m, SUM(sanction_amount_paise) sanction_paise, SUM(successful_payment_paise) settled_paise, SUM(pending_payment_paise) pending_paise, AVG(priority_score) mean_priority"
    sql = f"SELECT {aggregate} FROM Work_Features WHERE {where}"
    summary = dict(db.execute(sql, [key]).fetchone())
    years = [dict(r) for r in db.execute(f"SELECT COALESCE(sanction_fy,'Not recorded') year, {aggregate} FROM Work_Features WHERE {where} GROUP BY sanction_fy ORDER BY sanction_fy", [key])]
    reasons = [dict(r) for r in db.execute(f"SELECT rule, COUNT(DISTINCT work_id) works, SUM(points) points FROM Rule_Contributions WHERE work_id IN (SELECT work_id FROM Work_Features WHERE {where}) GROUP BY rule ORDER BY works DESC,rule", [key])]
    return {"kind": kind, "key": key, "name": found[name], "profile": dict(found), "summary": summary, "years": years, "reasons": reasons, "sql": sql, "params": [key],
            "note": "District authority is an administrative label, not necessarily a unique geographic district. Vendor-linked work totals include each connected work once; they are not payments exclusively to that vendor. Scores prioritize human review, not findings of fraud."}
