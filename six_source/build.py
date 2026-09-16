"""Read six immutable CSVs; build connected, audited, local investigation data."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from common import AS_OF, COHORTS, CONTRACTS, FILES, ROOT, SEED, SOURCES, VERSION, dates, fy, json_safe, money, mp_key, name_key, norm, ratio, require, sha, to_records, write_json

# Vendored NumPy Isolation Forest; no cross-directory runtime dependency.
from isolation import isolation_scores
from sklearn.cluster import DBSCAN

DEFS = {}
STOP = set("a an the of for and at in to with from by near construction installation purchase providing work works supply development village gram panchayat ward no number district block under proposed new existing".split())


def field(frame, name, values, meaning, source="Connected sources", timing="Snapshot descriptive"):
    frame[name] = values
    DEFS[name] = (meaning, source, timing)


def load_sources(input_root, cohorts):
    parts = {key: [] for key in FILES}
    audit, quarantine = [], []
    for code in cohorts:
        require(code in COHORTS, f"Unknown cohort '{code}'")
        cohort_dir = input_root / COHORTS[code]
        for key, filename in FILES.items():
            path = cohort_dir / filename
            frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
            digest = sha(path)
            expected_rows, expected_hash = CONTRACTS[code][key]
            require(len(frame) == expected_rows and digest == expected_hash,
                    f"{code}/{filename}: source differs from the reviewed contract. Profile and approve a new source version first.")
            report = {"cohort": code, "source": key, "file": f"{COHORTS[code]}/{filename}", "rows": len(frame), "bytes": path.stat().st_size, "sha256": digest,
                      "columns": list(frame.columns), "blank_counts": {c: int(frame[c].str.strip().eq("").sum()) for c in frame},
                      "na_token_counts": {c: int(frame[c].eq("NA").sum()) for c in frame if frame[c].eq("NA").any()}}
            frame["COHORT"] = code
            frame["source_record"] = np.arange(1, len(frame) + 1)
            if key == "payments":
                required = ["WORK_RECOMMENDATION_DTL_ID", "VENDOR_ID", "EXPENDITURE_DATE", "FUND_DISBURSED_AMT", "WORK_STATUS", "MP_NAME"]
                invalid = frame[required].eq("").any(axis=1)
                rejected = frame.loc[invalid].copy()
                rejected["quarantine_reason"] = "Incomplete expenditure record: required identifier/date/amount/status missing; apparent truncated final CSV row"
                quarantine.append(rejected)
                frame = frame.loc[~invalid].copy()
            # Namespace the work/payment join key AFTER quarantine as cohort:mpkey:id.
            # The Rajya Sabha portal reuses WORK_RECOMMENDATION_DTL_ID across MPs (same id,
            # different member/tenure/amount), so the id is unique only per MP; the
            # normalized MP name disambiguates and joins consistently across all four work
            # files and payments. Lok Sabha ids are already unique, so its work count is
            # unchanged. Namespacing after quarantine keeps blank required fields detectable.
            if "WORK_RECOMMENDATION_DTL_ID" in frame.columns:
                frame["WORK_RECOMMENDATION_DTL_ID"] = code + ":" + frame["MP_NAME"].map(name_key) + ":" + frame["WORK_RECOMMENDATION_DTL_ID"].astype(str)
            report["accepted_rows"] = len(frame)
            report["quarantined_rows"] = report["rows"] - len(frame)
            audit.append(report)
            parts[key].append(frame)
    tables = {key: pd.concat(frames, ignore_index=True) for key, frames in parts.items()}
    for key in ("recommended", "sanctioned", "completed"):
        require(tables[key].WORK_RECOMMENDATION_DTL_ID.is_unique, f"Duplicate namespaced work key in {key}")
    quarantine_frame = pd.concat(quarantine, ignore_index=True) if quarantine else pd.DataFrame()
    return tables, audit, quarantine_frame


def connect_works(tables):
    rec = tables["recommended"].set_index("WORK_RECOMMENDATION_DTL_ID")
    san = tables["sanctioned"].set_index("WORK_RECOMMENDATION_DTL_ID")
    complete = tables["completed"].set_index("WORK_RECOMMENDATION_DTL_ID")
    # Sanctioned source governs sanctioned fields; recommendation-only rows remain.
    # Work keys are cohort-namespaced strings ('cohort:id'); sort lexicographically.
    source = san.combine_first(rec).sort_index()
    work = pd.DataFrame(index=source.index)
    field(work, "work_id", source.index.astype(str), "Stable namespaced key 'cohort:mpkey:WORK_RECOMMENDATION_DTL_ID' (RS reuses raw ids across MPs); never join the differently formatted WORK_ID columns", "03/04/05/06")
    field(work, "cohort", source.COHORT, "Source cohort: lok_sabha, rs_sitting or rs_retired; part of the namespaced work and MP keys", "01-06")
    mappings = {"mp_name":"MP_NAME", "state":"STATE_NAME", "ida_name":"IDA_NAME", "constituency":"CONSTITUENCY", "constituency_id":"CONSTITUENCY_ID", "house":"HOUSE_OF_PARLIAMENT", "tenure":"TENURE", "work_category":"WORK_CATEGORY", "activity_raw":"ACTIVITY_NAME", "description":"WORK_DESCRIPTION", "letter_no":"LETTER_NO"}
    for name, raw in mappings.items():
        field(work, name, source[raw], f"Original {raw}; sanctioned export preferred, recommendation export fallback", "04/03")
    field(work, "mp_key", mp_key(source), "Checked house|tenure|normalized MP name; no fuzzy entity merge", "01/03/04")
    field(work, "ida_key", source.STATE_NAME.map(norm) + "|" + source.IDA_NAME.map(norm), "State plus normalized complete implementing district authority name", "03/04")
    field(work, "activity_type", source.ACTIVITY_NAME.str.replace(r"^WS/\s*MP\d+/\d{4}-\d{4}/\d+-", "", regex=True).str.strip(), "Activity taxonomy after removing its work-specific WS prefix", "03/04")
    field(work, "mp_code_observed", source.ACTIVITY_NAME.str.extract(r"MP(\d+)/", expand=False), "Observed MP code parsed from activity identifier; cross-check, not a universal allocation key", "03/04")
    for name, data in [("recommended",rec),("sanctioned",san),("completed",complete)]:
        field(work, "in_" + name, work.index.isin(data.index), f"Record exists in the {name} export; absence is not proof no event occurred", FILES[name])
        field(work, name + "_source_record", data.source_record.reindex(work.index).astype("Int64"), "One-based CSV data record number, excluding header; not necessarily physical line number", FILES[name])
    field(work, "recommended_amount_paise", money(rec.RECOMMENDED_AMOUNT).reindex(work.index), "Recommended amount in integer paise; unknown for sanction-only records", "03")
    field(work, "sanction_amount_paise", money(san.SANCTION_AMOUNT).reindex(work.index), "Sanction amount in integer paise; only sanctioned-export membership establishes sanction", "04")
    field(work, "recommendation_report_sanction_amount_paise", money(rec.SANCTION_AMOUNT).reindex(work.index), "Preserved recommendation-report value, including on unsanctioned rows; not added to official sanction total", "03")
    field(work, "completion_actual_paise", money(complete.ACTUAL_AMOUNT).reindex(work.index), "Reported completion ACTUAL_AMOUNT, not assumed equal to settlement ledger", "05")
    for name, values, src in [("recommendation_date",dates(source.RECOMMENDATION_DATE),"03/04"),("sanction_date",dates(san.SANCTION_DATE).reindex(work.index),"04"),("completion_date",dates(complete.ACTUAL_END_DATE).reindex(work.index),"05")]:
        field(work, name, values, "Parsed ISO date; not a source extraction or event-recording timestamp", src, "Event date; knowledge time unavailable")
    for name, data in [("recommendation_stage_raw",rec),("sanction_stage_raw",san)]:
        field(work, name, data.WORK_STAGE.reindex(work.index), "Source-specific stage preserved; stage labels are not comparable event timestamps", "03/04")
    field(work, "recommendation_flag_raw", rec.FLAG.reindex(work.index), "Original FLAG; code 2 is not assumed to mean confirmed rejection", "03")
    field(work, "completion_description_raw", complete.WORK_DESCRIPTION.reindex(work.index), "Original completion description, including changes from sanctioned description", "05")
    field(work, "completion_work_id_raw", complete.WORK_ID.reindex(work.index), "Completion system's secondary work ID; do not join to expenditure WORK_ID", "05")
    field(work, "completion_attachment_id", complete.ATTACH_ID.reindex(work.index).replace("", None), "Document reference only; no image was supplied or verified", "05")
    field(work, "completion_rating_raw", complete.AVERAGE_RATING.reindex(work.index), "Reported rating; zero is not interpreted as low asset quality", "05")
    field(work, "lifecycle", np.select([work.in_completed,work.in_sanctioned],["Reported complete","Sanctioned / open"],default="Not in sanction export"), "Completion-export membership overrides progress-stage wording for reported completion", "03/04/05")
    field(work, "recommendation_missing_flag", ~work.in_recommended & work.in_sanctioned, "Sanction exists without recommendation row; retained as source-coverage issue", "03/04")
    field(work, "source_stage_difference_flag", work.in_recommended & work.in_sanctioned & work.recommendation_stage_raw.ne(work.sanction_stage_raw), "Differences include Pending for Sanction vs Sanction vocabulary; not automatically a lifecycle violation", "03/04")
    field(work, "description_changed_flag", work.in_completed & work.description.str.strip().ne(work.completion_description_raw.str.strip()), "Completion description differs from sanctioned text; preserve both and inspect scope change", "04/05")
    field(work, "missing_description_flag", work.description.str.strip().eq(""), "Missing descriptive evidence limits text matching", "03/04")
    require(complete.index.isin(san.index).all(), "Completion export has unmatched sanctioned work IDs")
    return work.reset_index(drop=True)


def payments_and_links(raw, work):
    p = raw.copy()
    original = [c for c in p if c not in {"Sno","source_record"}]
    # No transaction IDs: retain every row, with a reproducible sensitivity scenario.
    p["report_fingerprint"] = [hashlib.sha256(json.dumps(row,ensure_ascii=False,separators=(",", ":")).encode()).hexdigest() for row in p[original].itertuples(index=False,name=None)]
    p["same_fingerprint_count"] = p.groupby("report_fingerprint").report_fingerprint.transform("size")
    p["fingerprint_first_row"] = ~p.report_fingerprint.duplicated()
    rename = {"WORK_RECOMMENDATION_DTL_ID":"work_id", "VENDOR_ID":"vendor_id", "VENDOR_NAME":"vendor_name", "IA_NAME":"ia_name", "WORK_STATUS":"payment_status", "STATE_NAME":"payment_state", "IDA_NAME":"payment_ida_name", "MP_NAME":"payment_mp_name", "WORK_ID":"payment_work_id_raw", "Sno":"source_sno"}
    p = p.rename(columns=rename)
    p["payment_date"] = dates(p.EXPENDITURE_DATE)
    p["amount_paise"] = money(p.FUND_DISBURSED_AMT)
    require(p.amount_paise.notna().all() and p.amount_paise.ge(0).all(), "Invalid payment amount")
    require(set(p.payment_status) <= {"Payment Success","Payment In-Progress"}, "New payment status needs contract review")
    require(p.work_id.isin(set(work.work_id)).all(), "Unmatched payment work")
    p = p.merge(work[["work_id","mp_key","ida_key","activity_type","sanction_date","completion_date","state"]],on="work_id",how="left",validate="many_to_one")
    p["is_success"] = p.payment_status.eq("Payment Success")
    p["successful_paise"] = p.amount_paise.where(p.is_success,0)
    p["pending_paise"] = p.amount_paise.where(~p.is_success,0)
    p["fingerprint_sensitivity_paise"] = p.successful_paise.where(p.fingerprint_first_row,0)
    p["payment_before_sanction_flag"] = p.payment_date.lt(p.sanction_date)
    p["payment_after_completion_flag"] = p.completion_date.notna() & p.payment_date.gt(p.completion_date)
    p["fiscal_year"] = fy(p.payment_date)
    p["payment_month"] = p.payment_date.dt.strftime("%Y-%m")
    p["march_payment_flag"] = p.payment_date.dt.month.eq(3)
    p["march_successful_paise"] = p.successful_paise.where(p.march_payment_flag, 0)
    p["repeat_excess_row"] = ~p.fingerprint_first_row
    agg = p.groupby("work_id").agg(payment_row_count=("work_id","size"), successful_payment_count=("is_success","sum"), successful_payment_paise=("successful_paise","sum"), pending_payment_paise=("pending_paise","sum"), march_successful_paise=("march_successful_paise","sum"), unique_fingerprint_sensitivity_paise=("fingerprint_sensitivity_paise","sum"), repeated_report_excess_rows=("repeat_excess_row","sum"), vendor_count=("vendor_id","nunique"), implementing_agency_count=("ia_name","nunique"), first_payment_date=("payment_date","min"), last_payment_date=("payment_date","max"), payment_before_sanction_flag=("payment_before_sanction_flag","max"), payment_after_completion_count=("payment_after_completion_flag","sum"))
    settled = p.loc[p.is_success].groupby("work_id").payment_date.agg(first_success_date="min",last_success_date="max")
    agg = agg.join(settled)
    descriptions = {
        "payment_row_count":"Accepted report rows, including in-progress and repeated fingerprints",
        "successful_payment_count":"Observed Payment Success rows; repeated report rows retained",
        "successful_payment_paise":"Sum of Payment Success amounts in integer paise; reported settlement, not independently bank-reconciled",
        "pending_payment_paise":"Payment In-Progress sum, excluded from settled expenditure",
        "march_successful_paise":"Sum of Payment Success amounts dated in March (financial year-end); year-end disbursement is not itself misuse",
        "unique_fingerprint_sensitivity_paise":"Sensitivity only: one successful report row per identical fingerprint; not corrected expenditure or proven duplicate-payment removal",
        "repeated_report_excess_rows":"Identical report rows beyond first after excluding Sno; no transaction/invoice ID to establish duplicate payment",
        "vendor_count":"Distinct stable vendor IDs on observed payment rows",
        "implementing_agency_count":"Distinct reported implementing-agency names; names are not stable legal entity IDs",
        "first_payment_date":"Earliest observed request/report date, any status", "last_payment_date":"Latest observed request/report date, any status",
        "first_success_date":"Earliest observed successful-payment date", "last_success_date":"Latest observed successful-payment date",
        "payment_before_sanction_flag":"Any reported payment before sanction; chronology check, not proof of misuse",
        "payment_after_completion_count":"Payment rows after reported completion; final settlement/retention can be legitimate",
    }
    for name in agg:
        val = work.work_id.map(agg[name])
        if name.endswith(("_count","_rows","_paise")):
            val = val.fillna(0).astype("int64")
        elif name.endswith("_flag"):
            val = val.fillna(False).astype(bool)
        field(work,name,val,descriptions[name],"06 (aggregated before work join)")
    field(work,"has_payment_evidence",work.payment_row_count.gt(0),"No observed row is not proof of zero actual payments; check coverage", "06")
    field(work,"has_successful_payment_evidence",work.successful_payment_count.gt(0),"At least one reported successful-payment row", "06")
    return work, p


def lifecycle_features(work, as_of):
    ref = pd.Timestamp(as_of)
    field(work,"as_of_date",as_of,"Explicit snapshot assessment date; not export timestamp", "Run configuration")
    field(work,"recommendation_fy",fy(work.recommendation_date),"Indian financial year of recommendation (April-March)","03/04")
    field(work,"sanction_fy",fy(work.sanction_date).where(work.in_sanctioned,None),"Indian financial year of sanction; absent for unsanctioned rows", "04")
    for name, value, meaning in [
        ("recommendation_age_days",(ref-work.recommendation_date).dt.days,"Calendar days since recommendation at snapshot"),
        ("sanction_delay_days",(work.sanction_date-work.recommendation_date).dt.days,"Recommendation-to-sanction delay; proxy for missing IDA receipt date, MCC excluded days unavailable"),
        ("sanction_age_days",(ref-work.sanction_date).dt.days,"Age since sanction; not actual work start duration"),
        ("completion_days",(work.completion_date-work.sanction_date).dt.days,"Reported completion date minus sanction date"),
        ("first_success_delay_days",(work.first_success_date-work.sanction_date).dt.days,"Sanction-to-first observed successful payment; ledger starts November 2024"),
        ("days_since_last_success",(ref-work.last_success_date).dt.days,"Time since last observed successful payment; no physical-progress update date"),
    ]:
        field(work,name,value,meaning)
    anniversary = work.sanction_date + pd.DateOffset(years=1)
    payment_due = work.sanction_date + pd.DateOffset(months=3)
    indicators = {
        "pending_recommendation_45d_flag": (~work.in_sanctioned & work.recommendation_age_days.gt(45),"Not found in sanction export >45 days after recommendation; receipt/MCC/rejection evidence needed"),
        "sanction_delay_45d_flag": (work.sanction_delay_days.gt(45),"Recommendation-based 45-day proxy, not a confirmed statutory breach"),
        "open_over_one_year_flag": (work.in_sanctioned & ~work.in_completed & anniversary.lt(ref),"No completion record beyond calendar-year anniversary; specific sanction due date/extensions absent"),
        "completed_over_one_year_flag": (work.in_completed & work.completion_date.gt(anniversary),"Reported completion after one calendar year; permitted extensions unknown"),
        "no_payment_three_months_flag": (work.in_sanctioned & ~work.has_payment_evidence & payment_due.lt(ref),"No payment row observed beyond three calendar months; requests and missing export coverage require checking"),
        "completion_without_payment_flag": (work.in_completed & ~work.has_successful_payment_evidence,"Completion row without observed successful payment; coverage/reconciliation request, not unpaid-asset finding"),
        "completed_missing_attachment_flag": (work.in_completed & work.completion_attachment_id.isna(),"No supplied completion attachment reference; cannot infer ghost asset"),
        "negative_chronology_flag": (work.sanction_delay_days.lt(0)|work.completion_days.lt(0)|work.payment_before_sanction_flag,"Negative event order requiring source verification"),
        "future_event_flag": (work.recommendation_date.gt(ref)|work.sanction_date.gt(ref)|work.completion_date.gt(ref),"Observed event after the configured assessment date"),
    }
    for name,(value,meaning) in indicators.items():
        field(work,name,value.fillna(False),meaning,"MONITOR / source evidence")
    field(work,"sanction_recommendation_delta_paise",work.sanction_amount_paise-work.recommended_amount_paise,"Sanction versus recommended estimate difference, not a revised-cost overrun","03/04")
    field(work,"completion_sanction_delta_paise",work.completion_actual_paise-work.sanction_amount_paise,"Reported completion amount minus sanctioned amount; revised sanctions/taxes/retentions unavailable","04/05")
    field(work,"payment_sanction_delta_paise",(work.successful_payment_paise-work.sanction_amount_paise).where(work.has_successful_payment_evidence),"Observed successful expenditure minus sanction; missing payment evidence remains null","04/06")
    field(work,"paid_to_sanction_ratio",ratio(work.successful_payment_paise,work.sanction_amount_paise).where(work.has_successful_payment_evidence),"Observed settled amount / sanction, null when no settlement evidence","04/06")
    field(work,"completion_payment_gap_paise",(work.completion_actual_paise-work.successful_payment_paise).where(work.in_completed & work.has_successful_payment_evidence),"Completion actual minus observed successful payments; not assumed recoverable/unpaid money","05/06")
    # Financial materiality: ignore trivial or rounding-level excesses. A payment/completion
    # overage flags only when it clears both an absolute floor (INR 10,000) and 2% of sanction.
    material = np.maximum(1_000_000.0, work.sanction_amount_paise.astype("float64") * 0.02)
    field(work,"paid_over_sanction_flag",(work.payment_sanction_delta_paise.astype("float64") > material).fillna(False),"Reported successful payments exceed sanction by a material margin (over the greater of INR 10,000 and 2% of sanction); investigate revised orders","04/06")
    field(work,"completion_over_sanction_flag",(work.completion_sanction_delta_paise.astype("float64") > material).fillna(False),"Reported completion actual exceeds sanction by a material margin (over the greater of INR 10,000 and 2% of sanction); investigate approved scope/revised sanction","04/05")
    field(work,"repeat_payment_report_flag",work.repeated_report_excess_rows.gt(0),"At least one repeated report fingerprint; payment duplication unproven","06")
    field(work,"march_settled_share",ratio(work.march_successful_paise,work.successful_payment_paise).where(work.has_successful_payment_evidence),"Share of settled amount disbursed in March; null without settlement evidence","06")
    field(work,"march_rush_flag",(work.has_successful_payment_evidence & work.march_successful_paise.gt(0) & work.march_settled_share.ge(0.8)).fillna(False),"At least 80% of settled amount disbursed in March (financial year-end); verify progress at time of payment, not itself misuse","06")
    field(work,"completion_evidence_mismatch_flag",work.completion_payment_gap_paise.abs().gt(10000).fillna(False),"More than INR 100 difference between completion actual and observed successful payment sum; informational reconciliation","05/06")
    field(work,"description_normalized",work.description.map(norm),"Unicode-normalized text for local candidate generation; original retained","03/04")
    field(work,"continuation_cue_flag",work.description_normalized.str.contains(r"\b(?:phase|continued|continue|continuation|extension|part|repair|renovation)\b",regex=True),"Text suggests distinct phase/repair/extension; lowers duplicate certainty","03/04")
    # Strictly earlier calendar-day counts, not full-snapshot history disguised as prior.
    for key,label in [("mp_key","mp"),("ida_key","ida")]:
        daily=work.loc[work.in_sanctioned].groupby([key,"sanction_date"]).size().rename("n").reset_index().sort_values("sanction_date")
        daily["prior"] = daily.groupby(key).n.cumsum()-daily.n
        lookup=daily.set_index([key,"sanction_date"]).prior
        values=[lookup.get((entity,date),pd.NA) if pd.notna(date) else pd.NA for entity,date in zip(work[key],work.sanction_date)]
        field(work,label+"_strict_prior_sanction_count",pd.Series(values,dtype="Int64"),"Observed sanctions for same entity on strictly earlier dates; same-day rows excluded", "03/04", "Event-time history within supplied export; reporting lags unknown")
    return work


def cost_features(work):
    # Reference = prior fiscal years; same-year works never define their own benchmark.
    amounts=work.sanction_amount_paise.astype(float)/100
    stats={}
    sanctioned=work.loc[work.in_sanctioned]
    for year in sorted(sanctioned.sanction_fy.unique()):
        reference=sanctioned.loc[sanctioned.sanction_fy.lt(year)]
        for level,keys in [("State + activity",["state","activity_type"]),("Activity",["activity_type"])]:
            for group,rows in reference.groupby(keys,sort=True):
                if len(rows)<20: continue
                logs=np.log1p(rows.sanction_amount_paise.to_numpy(float)/100)
                median=float(np.median(logs)); mad=float(np.median(np.abs(logs-median)))
                scale=max(1.4826*mad,.1)
                key=group if isinstance(group,tuple) else (group,)
                stats[(year,level,*key)]=(len(rows),float(np.expm1(median)),median,scale)
    peers=[]
    for row in work.itertuples():
        entry=stats.get((row.sanction_fy,"State + activity",row.state,row.activity_type));level="State + activity"
        if entry is None:
            entry=stats.get((row.sanction_fy,"Activity",row.activity_type));level="Activity"
        peers.append((level,*entry) if entry else ("Insufficient prior-year peers",0,np.nan,np.nan,np.nan))
    data=pd.DataFrame(peers,columns=["peer_level","peer_count","peer_median_inr","peer_log_median","peer_log_scale"])
    for col in data:
        field(work,col,data[col],"Prior-financial-year benchmark: state/activity first, activity fallback, minimum 20 peers; log-MAD scale floor 0.1", "04", "Uses earlier fiscal years only; exports may be retrospectively updated")
    field(work,"cost_peer_log_z",(np.log1p(amounts)-work.peer_log_median)/work.peer_log_scale,"Log-amount deviation divided by max(1.4826 log-MAD,0.1); null without historical peers", "04", "Prior-financial-year benchmark")
    field(work,"cost_peer_ratio",ratio(amounts,work.peer_median_inr),"Sanction divided by prior-year peer median; not a unit-cost comparison","04","Prior-financial-year benchmark")
    field(work,"high_cost_peer_flag",(work.cost_peer_log_z.gt(3.5)&work.cost_peer_ratio.ge(2)&work.sanction_amount_paise.ge(10000000)).fillna(False),"Large prior-year peer amount deviation on a work of at least INR 1 lakh (materiality floor); quantities/specifications are unavailable","04","Prior-financial-year benchmark")
    return work


def duplicate_candidates(work):
    texts=work.description_normalized.tolist()
    tokens=[set(text.split())-STOP for text in texts]
    frequencies=Counter(token for terms in tokens for token in terms)
    weights={token:math.log1p(len(work)/(1+count)) for token,count in frequencies.items()}
    postings=defaultdict(list); pairs=[]; tested=0; capped=0; skipped=0
    nearest=np.zeros(len(work));counts=np.zeros(len(work),dtype=int);strong=np.zeros(len(work),dtype=bool)
    ids=work.work_id.tolist();ida=work.ida_key.tolist();activity=work.activity_type.tolist();amounts=work.sanction_amount_paise.tolist();phase=work.continuation_cue_flag.tolist()
    for i in range(len(work)):
        anchors=sorted(tokens[i],key=lambda t:(frequencies[t],t))[:3]
        candidates=set()
        for token in anchors:
            found=postings[(ida[i],activity[i],token)]
            if len(found)>150: skipped+=1
            candidates.update(found[-150:])
        if len(candidates)>60: capped+=1
        candidates=sorted(candidates,reverse=True)[:60]
        eligible=[]
        for j in candidates:
            tested+=1
            common=tokens[i]&tokens[j];union=tokens[i]|tokens[j]
            sim=sum(weights[t] for t in sorted(common))/sum(weights[t] for t in sorted(union)) if union else 0
            same=texts[i]==texts[j] and bool(texts[i]);sim=1.0 if same else sim
            if sim<.88:continue
            numeric_i=set(re.findall(r"\b\d+\b",texts[i]));numeric_j=set(re.findall(r"\b\d+\b",texts[j]))
            number_conflict=bool(numeric_i and numeric_j and numeric_i!=numeric_j)
            generic=min(len(tokens[i]),len(tokens[j]))<4
            same_amount=pd.notna(amounts[i]) and pd.notna(amounts[j]) and amounts[i]==amounts[j]
            high=bool(sim>=.96 and same_amount and not(number_conflict or generic or phase[i] or phase[j]))
            eligible.append((sim,j,number_conflict,generic,high,same_amount,same))
        for sim,j,conflict,generic,high,same_amount,same in sorted(eligible,key=lambda x:(-x[0],ids[x[1]]))[:3]:
            pair_id="pair:"+"-".join(sorted([ids[i],ids[j]]))
            pairs.append({"pair_id":pair_id,"work_id_a":ids[j],"work_id_b":ids[i],"similarity":round(sim,6),"same_normalized_text":same,"same_amount":same_amount,"number_conflict":conflict,"generic_text":generic,"continuation_cue":bool(phase[i] or phase[j]),"high_similarity_review":high,"ida_key":ida[i],"activity_type":activity[i]})
            for k in (i,j):nearest[k]=max(nearest[k],sim);counts[k]+=1;strong[k]|=high
        for token in anchors:postings[(ida[i],activity[i],token)].append(i)
    field(work,"duplicate_similarity",np.round(nearest,6),"Maximum retained weighted-token candidate similarity within same IDA/activity; not asset identity","03/04")
    field(work,"duplicate_candidate_count",counts,"Retained pair incidences; up to three earlier matches emitted per work, earlier endpoints may have more","03/04")
    field(work,"high_similarity_review_flag",strong,"Similarity >=0.96, equal known sanction, no number conflict/generic/phase cue; still needs location/scope evidence","03/04")
    pair_columns=["pair_id","work_id_a","work_id_b","similarity","same_normalized_text","same_amount","number_conflict","generic_text","continuation_cue","high_similarity_review","ida_key","activity_type"]
    meta={"pairs":len(pairs),"candidate_comparisons":tested,"work_candidate_cap_hits":capped,"posting_window_hits":skipped,"method":"Three rare-token anchors; same IDA/activity; last 150 posting members; 60 earlier candidates; top three >=0.88; deterministic ID order. Not exhaustive, no measured duplicate recall."}
    return work,pd.DataFrame(pairs,columns=pair_columns),meta


RULES = [
    ("pending_recommendation_45d_flag",12,"Pending recommendation >45 days","Receipt and rejection/MCC records needed"),
    ("sanction_delay_45d_flag",8,"Sanction delay proxy >45 days","Receipt-based official period cannot be proven"),
    ("open_over_one_year_flag",20,"Open beyond one year","Check contractual due date and extensions"),
    ("no_payment_three_months_flag",12,"No observed payment after three months","Payment report may be incomplete"),
    ("paid_over_sanction_flag",30,"Reported payments exceed sanction","Check revised sanction and reconciliation"),
    ("completion_over_sanction_flag",25,"Completion actual exceeds sanction","Check approved scope and revised sanction"),
    ("repeat_payment_report_flag",15,"Repeated payment report rows","Transaction IDs needed to decide duplication"),
    ("march_rush_flag",8,"Year-end (March) disbursement concentration","Year-end disbursement can be legitimate; verify progress at payment"),
    ("high_cost_peer_flag",12,"High prior-year peer amount","Quantities, unit costs and specifications absent"),
    ("high_similarity_review_flag",12,"Similar work descriptions","Distinct locations/phases can be legitimate"),
]


def scores(work):
    contributions=[]
    raw=np.zeros(len(work))
    for flag,weight,label,caution in RULES:
        value=work[flag].fillna(False).astype(int)*weight
        raw+=value.to_numpy()
        for index in np.flatnonzero(value.to_numpy()):
            contributions.append({"work_id":work.iloc[index].work_id,"rule":flag,"points":weight,"reason":label,"caution":caution})
    field(work,"priority_score",np.minimum(raw,100).astype(int),"Sum of disclosed screening weights, capped at 100; not a probability or calibrated fraud model","Rule registry")
    field(work,"priority_band",pd.cut(work.priority_score,bins=[-1,0,19,39,80,100],labels=["Routine","Low","Medium","High","Critical"]).astype(str),"Queue bands: 0 Routine; 1-19 Low; 20-39 Medium; 40-80 High; 81-100 Critical","Rule registry")
    flags=[r[0] for r in RULES]
    field(work,"reason_codes",work[flags].apply(lambda r:";".join(c for c in flags if r[c]),axis=1),"Semicolon-separated active screening rules; exact contributions in Rule_Contributions","Rule registry")
    dq=["recommendation_missing_flag","description_changed_flag","missing_description_flag","negative_chronology_flag","future_event_flag"]
    field(work,"data_quality_issue_count",work[dq].astype(int).sum(axis=1),"Separate count of coverage/text/chronology issues; stage vocabulary differences excluded","Source audit")
    # Retrospective full-snapshot model, deliberately separate from queue rules.
    columns=["sanction_delay_days","completion_days","days_since_last_success","cost_peer_log_z","paid_to_sanction_ratio","vendor_count"]
    x=np.column_stack([np.log1p(work.sanction_amount_paise.astype(float).fillna(0)/100),work[columns].to_numpy(float)])
    missing=np.isnan(x).astype(float)
    medians=np.nanmedian(x,axis=0);medians=np.nan_to_num(medians)
    x=np.column_stack([np.where(np.isnan(x),medians,x),missing])
    values=isolation_scores(x,seed=SEED,tree_count=100,sample_size=256)
    field(work,"isolation_score",values,"Seeded 100-tree NumPy Isolation Forest, sample 256; median imputation and missing indicators; descriptive full-snapshot atypicality","IFOREST","Full-snapshot fit; not held-out forecast or fraud probability")
    field(work,"isolation_percentile",pd.Series(values).rank(pct=True,method="average")*100,"Average-tie percentile of model atypicality within this extract; separate from rule priority","IFOREST","Full-snapshot fit")
    # Density-based clustering over the same standardized features; a second, independent
    # unsupervised view. Noise (label -1) marks works far from any dense group of peers.
    base=np.column_stack([np.log1p(work.sanction_amount_paise.astype(float).fillna(0)/100),work[columns].to_numpy(float)])
    med=np.nan_to_num(np.nanmedian(base,axis=0));base=np.where(np.isnan(base),med,base)
    scale=base.std(axis=0);scale[scale==0]=1;z=(base-base.mean(axis=0))/scale
    # Many works share identical imputed feature rows; cluster the unique rows with a
    # count weight (min_samples is in works), then map labels back. Keeps DBSCAN tractable
    # on 160k rows and stops a dense repeated row from being mislabelled as sparse noise.
    uniq,inverse=np.unique(np.round(z,1),axis=0,return_inverse=True)
    weights=np.bincount(inverse).astype(float)
    labels=DBSCAN(eps=0.9,min_samples=50).fit_predict(uniq,sample_weight=weights)[inverse]
    field(work,"dbscan_cluster",pd.Series(labels,dtype="Int64"),"Density cluster over standardized work features (log sanction, delays, cost z, paid ratio, vendor count); -1 is a low-density pattern outlier","DBSCAN","Full-snapshot fit; separate from rules and Isolation Forest")
    field(work,"dbscan_outlier_flag",labels==-1,"Not placed in any dense cluster of similar works; a pattern outlier to inspect, never a fraud finding","DBSCAN","Full-snapshot fit")
    return work,pd.DataFrame(contributions,columns=["work_id","rule","points","reason","caution"])


def entity_tables(tables,work,payments):
    alloc=tables["allocations"].copy();alloc["mp_key"]=mp_key(alloc)
    require(alloc.mp_key.is_unique,"Normalized allocation keys are not unique")
    require(work.mp_key.isin(alloc.mp_key).all(),"Unmatched MP allocation key")
    consent=tables["consents"].copy();consent["mp_key"]=mp_key(consent)
    require(consent.mp_key.isin(alloc.mp_key).all(),"Unmatched consent MP")
    consent["consent_amount_paise"]=money(consent.CONSENTED_AMOUNT);consent["consent_date"]=dates(consent.CRT_DT);consent["fiscal_year"]=fy(consent.consent_date)
    consent["work_link_available"]=False
    def grouped(key):
        return work.groupby(key).agg(work_count=("work_id","size"),recommended_record_count=("in_recommended","sum"),sanctioned_count=("in_sanctioned","sum"),completed_count=("in_completed","sum"),recommended_paise=("recommended_amount_paise",lambda x:x.sum(min_count=1)),sanction_paise=("sanction_amount_paise",lambda x:x.sum(min_count=1)),successful_payment_paise=("successful_payment_paise","sum"),pending_payment_paise=("pending_payment_paise","sum"),open_over_one_year_count=("open_over_one_year_flag","sum"),no_payment_three_months_count=("no_payment_three_months_flag","sum"),high_priority_count=("priority_band",lambda x:x.isin(["High","Critical"]).sum()),mean_priority=("priority_score","mean"))
    mp=alloc.rename(columns={"MP_NAME":"mp_name","STATE_NAME":"state","CONSTITUENCY":"constituency","source_record":"allocation_source_record"})
    mp["allocated_paise"]=money(mp.ALLOCATED_AMT)
    mp=mp.merge(grouped("mp_key"),on="mp_key",how="left",validate="one_to_one")
    mp["consented_paise"]=mp.mp_key.map(consent.groupby("mp_key").consent_amount_paise.sum()).fillna(0).astype("int64")
    for c in mp:
        if c.endswith("_count"):mp[c]=mp[c].fillna(0).astype(int)
    mp["recommendation_to_allocation_ratio"]=ratio(mp.recommended_paise,mp.allocated_paise)
    mp["sanction_to_allocation_ratio"]=ratio(mp.sanction_paise,mp.allocated_paise)
    mp["observed_paid_to_allocation_ratio"]=ratio(mp.successful_payment_paise,mp.allocated_paise)
    mp["completion_to_sanction_ratio"]=ratio(mp.completed_count,mp.sanctioned_count)
    ida=grouped("ida_key").reset_index().merge(work[["ida_key","ida_name","state"]].drop_duplicates(),on="ida_key",validate="one_to_one")
    ida["completion_to_sanction_ratio"]=ratio(ida.completed_count,ida.sanctioned_count)
    vendor=payments.groupby("vendor_id").agg(vendor_name=("vendor_name","first"),payment_row_count=("work_id","size"),work_count=("work_id","nunique"),mp_count=("mp_key","nunique"),ida_count=("ida_key","nunique"),successful_payment_paise=("successful_paise","sum"),pending_payment_paise=("pending_paise","sum"),repeat_excess_rows=("repeat_excess_row","sum"),first_payment_date=("payment_date","min"),last_payment_date=("payment_date","max")).reset_index()
    names=vendor.groupby("vendor_name").vendor_id.transform("size")
    vendor["same_name_vendor_id_count"]=names
    edges=payments.groupby(["vendor_id","mp_key","ida_key","ia_name","fiscal_year"]).agg(payment_row_count=("work_id","size"),work_count=("work_id","nunique"),successful_payment_paise=("successful_paise","sum"),pending_payment_paise=("pending_paise","sum")).reset_index()
    shares=payments.loc[payments.is_success].groupby(["ida_key","fiscal_year","vendor_id"]).successful_paise.sum().reset_index()
    shares["ida_year_payment_paise"]=shares.groupby(["ida_key","fiscal_year"]).successful_paise.transform("sum")
    shares["vendor_share"]=ratio(shares.successful_paise,shares.ida_year_payment_paise)
    shares["share_squared"]=shares.vendor_share**2
    concentration=shares.groupby(["ida_key","fiscal_year"]).agg(vendor_hhi=("share_squared","sum"),top_vendor_share=("vendor_share","max"),vendor_count=("vendor_id","nunique"),successful_payment_paise=("successful_paise","sum")).reset_index()
    concentration["interpretation"]="Concentration of observed successful payments, not tender win rates or collusion proof"
    months=payments.groupby(["payment_month","fiscal_year","state"]).agg(payment_row_count=("work_id","size"),work_count=("work_id","nunique"),successful_payment_paise=("successful_paise","sum"),pending_payment_paise=("pending_paise","sum")).reset_index()
    # All six sources connect without fan-out: allocation/consent sums appear once per MP.
    return {"MP_Features":mp,"IDA_Features":ida,"Vendor_Features":vendor,"Vendor_Connections":edges,"IDA_Year_Concentration":concentration,"Monthly_Payments":months,"Calamity_Consents":consent}


def export_frame(frame):
    result=frame.copy()
    for c in result:
        if pd.api.types.is_datetime64_any_dtype(result[c]):result[c]=result[c].dt.strftime("%Y-%m-%d").where(result[c].notna(),None)
        elif isinstance(result[c].dtype,pd.CategoricalDtype):result[c]=result[c].astype(str)
    return result


def dictionary(tables):
    rows=[]
    extra={
        "report_fingerprint":"SHA-256 of complete original expenditure record except Sno/source record; no transaction ID supplied",
        "amount_paise":"Original expenditure report amount in exact integer paise; includes any status",
        "fingerprint_first_row":"First source record for identical report fingerprint, for sensitivity only",
        "same_fingerprint_count":"Number of report rows with identical fingerprint; not verified payment multiplicity",
        "vendor_hhi":"Sum of squared vendor shares of observed successful payments within IDA and fiscal year",
        "top_vendor_share":"Largest observed successful-payment vendor share within IDA/fiscal year",
        "same_name_vendor_id_count":"Distinct vendor IDs having exactly the same reported name; do not merge them",
        "allocated_paise":"Allocated limit snapshot from source 01 in exact paise; not annual entitlement or bank balance",
        "consented_paise":"Consented amounts from source 02, aggregated once per MP; not work expenditure",
        "observed_paid_to_allocation_ratio":"Successful reported expenditure / allocation snapshot; not certified utilization or current bank balance",
        "recommendation_to_allocation_ratio":"Observed recommended amount / allocation snapshot; definition distinct from expenditure",
        "sanction_to_allocation_ratio":"Observed sanctions / allocation snapshot; not payments",
        "completion_to_sanction_ratio":"Completed-export records / sanctioned-export records in this selection",
        "mean_priority":"Mean rule screening score in supplied works; not MP/IDA integrity rating",
        "work_link_available":"False: calamity consent has no source work-level funding link",
        "high_similarity_review":"Text/amount evidence only; still needs asset location/scope adjudication",
    }
    for table,frame in tables.items():
        for c in frame:
            if c in DEFS:meaning,source,timing=DEFS[c]
            elif c in extra:meaning,source,timing=extra[c],"Connected sources","Snapshot descriptive"
            elif c.upper()==c:meaning,source,timing=f"Preserved original CSV field {c}; see source contract and raw record","Original CSV","Raw snapshot"
            else:meaning,source,timing=f"{c.replace('_',' ')} at {table} grain; aggregate of observed records only","Connected sources","Snapshot descriptive"
            rows.append({"table":table,"field":c,"type":str(frame[c].dtype),"unit":"paise (100 = INR 1)" if c.endswith("_paise") else ("ratio 0-1 unless exceeding denominator" if c.endswith("_ratio") else "see definition"),"definition":meaning,"source":source,"availability":timing})
    return pd.DataFrame(rows)


def build(input_dir,output_dir,as_of=AS_OF,cohorts=None):
    cohorts=list(cohorts or COHORTS)
    output_dir.mkdir(parents=True,exist_ok=True)
    print("1/8 Source contracts and quarantine",flush=True)
    raw,source_audit,quarantine=load_sources(input_dir,cohorts)
    print("2/8 One-work master and payment aggregation",flush=True)
    work=connect_works(raw);work,payments=payments_and_links(raw["payments"],work)
    print("3/8 Lifecycle and strictly prior-year cost features",flush=True)
    work=lifecycle_features(work,as_of);work=cost_features(work)
    print("4/8 Bounded text-candidate generation",flush=True)
    work,pairs,duplicate_meta=duplicate_candidates(work)
    print("5/8 Explained rules and separate unsupervised model",flush=True)
    work,contributions=scores(work)
    print("6/8 MP, authority, vendor and monthly context",flush=True)
    tables={"Work_Features":work,"Payment_Features":payments,"Duplicate_Candidates":pairs,"Rule_Contributions":contributions,**entity_tables(raw,work,payments),"Quarantine":quarantine}
    tables["Feature_Dictionary"]=dictionary(tables)
    # Expectations recomputed independently from the raw contracted sources (cohort-agnostic),
    # a stronger reconciliation than hardcoded per-cohort literals.
    rows_of=lambda src:sum(CONTRACTS[c][src][0] for c in cohorts)
    rec_raw,san_raw,comp_raw,pay_raw=raw["recommended"],raw["sanctioned"],raw["completed"],raw["payments"]
    alloc_raw,consent_raw=raw["allocations"],raw["consents"]
    exp_works=len(set(rec_raw.WORK_RECOMMENDATION_DTL_ID)|set(san_raw.WORK_RECOMMENDATION_DTL_ID))
    exp_success=int(money(pay_raw.FUND_DISBURSED_AMT).where(pay_raw.WORK_STATUS.eq("Payment Success"),0).sum())
    exp_pending=int(money(pay_raw.FUND_DISBURSED_AMT).where(pay_raw.WORK_STATUS.eq("Payment In-Progress"),0).sum())
    checks={
        "source_hashes_match_contract":all(s["sha256"]==CONTRACTS[s["cohort"]][s["source"]][1] for s in source_audit),
        "one_row_per_work":bool(work.work_id.is_unique) and len(work)==exp_works,
        "recommended_membership_preserved":int(work.in_recommended.sum())==rows_of("recommended"),
        "sanctioned_membership_preserved":int(work.in_sanctioned.sum())==rows_of("sanctioned"),
        "completed_membership_preserved":int(work.in_completed.sum())==rows_of("completed"),
        "accepted_plus_quarantine_equals_source":len(payments)+len(quarantine)==rows_of("payments"),
        "successful_payment_sum_reconciles":int(work.successful_payment_paise.sum())==exp_success,
        "pending_payment_sum_reconciles":int(work.pending_payment_paise.sum())==exp_pending,
        "sanction_sum_reconciles":int(work.sanction_amount_paise.sum())==int(money(san_raw.SANCTION_AMOUNT).sum()),
        "recommendation_sum_reconciles":int(work.recommended_amount_paise.sum())==int(money(rec_raw.RECOMMENDED_AMOUNT).sum()),
        "completion_sum_reconciles":int(work.completion_actual_paise.sum())==int(money(comp_raw.ACTUAL_AMOUNT).sum()),
        "allocation_sum_reconciles":int(tables["MP_Features"].allocated_paise.sum())==int(money(alloc_raw.ALLOCATED_AMT).sum()),
        "consent_sum_reconciles":int(tables["Calamity_Consents"].consent_amount_paise.sum())==int(money(consent_raw.CONSENTED_AMOUNT).sum()),
        "payment_source_rows_preserved":(not payments.duplicated(["COHORT","source_record"]).any()) and len(payments)==rows_of("payments")-len(quarantine),
        "all_payments_match_work":bool(payments.work_id.isin(work.work_id).all()),
        "all_completed_match_sanction":not bool((work.in_completed & ~work.in_sanctioned).any()),
        "no_future_events_at_snapshot":not bool(work.future_event_flag.any()) and not bool(payments.payment_date.gt(pd.Timestamp(as_of)).any()),
        "rule_score_explanations_reconcile":np.array_equal(work.priority_score.to_numpy(),work.work_id.map(contributions.groupby("work_id").points.sum()).fillna(0).clip(upper=100).to_numpy()),
        "pair_keys_unique":bool(pairs.pair_id.is_unique),
        "model_scores_finite":bool(np.isfinite(work.isolation_score).all()),
        "source_bytes_unchanged":all(sha(input_dir/s["file"])==s["sha256"] for s in source_audit),
    }
    require(all(checks.values()),"A core reconciliation check failed: "+str([k for k,v in checks.items() if not v]))
    print("7/8 CSV and indexed SQLite outputs",flush=True)
    database=output_dir/"mplads.sqlite3"
    with sqlite3.connect(database) as db:
        for name,frame in tables.items():
            exported=export_frame(frame)
            exported.to_csv(output_dir/(name+".csv"),index=False,encoding="utf-8-sig",lineterminator="\n")
            exported.to_sql(name,db,if_exists="replace",index=False,chunksize=1000)
        for sql in ["CREATE UNIQUE INDEX IF NOT EXISTS idx_work_id ON Work_Features(work_id)","CREATE INDEX IF NOT EXISTS idx_work_filter ON Work_Features(state,sanction_fy,priority_score)","CREATE INDEX IF NOT EXISTS idx_work_mp ON Work_Features(mp_key)","CREATE INDEX IF NOT EXISTS idx_work_ida ON Work_Features(ida_key)","CREATE INDEX IF NOT EXISTS idx_payment_work ON Payment_Features(work_id)","CREATE INDEX IF NOT EXISTS idx_payment_vendor ON Payment_Features(vendor_id)","CREATE INDEX IF NOT EXISTS idx_pair_a ON Duplicate_Candidates(work_id_a)","CREATE INDEX IF NOT EXISTS idx_pair_b ON Duplicate_Candidates(work_id_b)","CREATE INDEX IF NOT EXISTS idx_reason_work ON Rule_Contributions(work_id)"]:
            db.execute(sql)
        db.execute("PRAGMA optimize")
    fingerprint=hashlib.sha256("|".join(s["sha256"] for s in source_audit).encode()).hexdigest()
    meta={"version":VERSION,"as_of":as_of,"source_fingerprint":fingerprint,"work_features_sha256":sha(output_dir/"Work_Features.csv"),"pipeline_sha256":sha(Path(__file__)),"common_sha256":sha(Path(__file__).parent/"common.py"),"sources":source_audit,"checks":checks,"all_checks_passed":all(checks.values()),"table_shapes":{name:{"rows":len(f),"columns":len(f.columns)} for name,f in tables.items()},"cohorts":cohorts,"scope":"Supplied exports for cohorts "+", ".join(cohorts)+"; cohort-namespaced work and MP keys; not all chambers or verified national completeness", "duplicate_method":duplicate_meta,
          "totals":{"works":len(work),"recommendations":int(work.in_recommended.sum()),"sanctions":int(work.in_sanctioned.sum()),"completions":int(work.in_completed.sum()),"payment_rows":len(payments),"successful_payment_paise":int(work.successful_payment_paise.sum()),"pending_payment_paise":int(work.pending_payment_paise.sum()),"sanction_paise":int(work.sanction_amount_paise.sum()),"recommended_paise":int(work.recommended_amount_paise.sum()),"completion_actual_paise":int(work.completion_actual_paise.sum()),"allocated_paise":int(tables["MP_Features"].allocated_paise.sum()),"quarantine_rows":len(quarantine),"repeat_excess_rows":int(payments.repeat_excess_row.sum()),"repeat_works":int(work.repeat_payment_report_flag.sum()),"repeat_sensitivity_success_paise":int(work.unique_fingerprint_sensitivity_paise.sum())},
          "rule_counts":{flag:int(work[flag].sum()) for flag,_,_,_ in RULES},"priority_counts":work.priority_band.value_counts().to_dict(),"rules":[{"field":f,"weight":v,"reason":l,"caution":c} for f,v,l,c in RULES],"research":SOURCES,
          "limits":["No independently adjudicated fraud labels, transaction IDs, invoices, revised-sanction ledger, unit quantities, approved due dates or complete progress event history.","Payment Success is used as reported settlement; Payment In-Progress is separate. Report duplicates are retained; sensitivity is not corrected expenditure.","No SC/ST beneficiary-area tags, trust master, geographic coordinates or asset images. These checks are unavailable, not passed.","Completion actual and vendor payments can differ because coverage, taxes/retention, timing and meanings are unresolved. No automatic fraud inference.","All new records, generated outputs and review notes remain local. Publication is not authorized by the previous three-source release.","Isolation Forest is descriptive full-snapshot atypicality and is separate from rule priority. No forecast accuracy is claimed."]}
    write_json(output_dir/"audit.json",meta)
    write_json(output_dir/"review_workbook.json",{"meta":meta,"sheets":{"Source_Coverage":source_audit,"MP_Summary":to_records(tables["MP_Features"]),"Priority_Cases":to_records(work.sort_values(["priority_score","work_id"],ascending=[False,True]).head(1000)),"Monthly_Payments":to_records(tables["Monthly_Payments"]),"Vendor_Summary":to_records(tables["Vendor_Features"].sort_values("successful_payment_paise",ascending=False).head(500)),"Feature_Dictionary":to_records(tables["Feature_Dictionary"])}})
    write_json(output_dir/"artifact_hashes.json",{p.name:sha(p) for p in sorted(output_dir.glob("*.csv"))})
    print("8/8 Completed: "+json.dumps(json_safe({"tables":meta["table_shapes"],"checks":len(checks),"totals":meta["totals"],"rule_counts":meta["rule_counts"]})),flush=True)
    return meta


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir",type=Path,default=ROOT/"Dataset",help="Dataset root holding the per-cohort subfolders")
    parser.add_argument("--output-dir",type=Path,default=Path(__file__).parent/"local")
    parser.add_argument("--cohorts",nargs="+",choices=list(COHORTS),default=list(COHORTS),help="Cohorts to build (default: all three)")
    parser.add_argument("--as-of",default=AS_OF,help="Snapshot assessment date YYYY-MM-DD")
    args=parser.parse_args()
    build(args.input_dir,args.output_dir,as_of=args.as_of,cohorts=args.cohorts)
