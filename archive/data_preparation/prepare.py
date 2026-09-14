"""Reproducible preparation of all 18 MPLADS source files; never modifies inputs."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
import numpy as np
import pandas as pd
from contracts import ROOT, AS_OF, VERSION, COHORTS, COHORT_CODES, KINDS, FILES, CONTRACTS, RECONCILIATION_TOLERANCE_PAISE

sys.path.insert(0, str(ROOT/'six_source'))
from common import norm, name_key, money, dates, fy, ratio, require, sha, write_json, to_records
import build as legacy

DEFS = legacy.DEFS
field = legacy.field
WORK = 'WORK_RECOMMENDATION_DTL_ID'
ADJUSTMENTS = []
CHECKS = []

def check(name, actual, expected):
    pack=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True) if isinstance(x,(list,dict,tuple)) else x
    CHECKS.append(dict(check=name,actual=pack(actual),expected=pack(expected),passed=bool(actual==expected)))
    require(actual==expected, f'{name}: {actual} != {expected}')

def stable_hash(values):
    return hashlib.sha256(json.dumps(values,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()

def term_key(frame):
    # Terms are not interchangeable: "Sitting MP" occurs in the retired export too.
    parts = zip(frame.HOUSE_OF_PARLIAMENT,frame.MP_NAME.map(name_key),frame.TENURE_START_DATE,frame.TENURE_END_DATE)
    return pd.Series(['term:'+stable_hash(list(v))[:24] for v in parts],index=frame.index)

def work_keys(frame, kind):
    result = 'work:' + frame[WORK]
    if kind == 'recommended':
        special = frame.FLAG.eq('2')
        require(frame.loc[special,'ACTIVITY_NAME'].str.startswith('NA-').all(),'Unreviewed FLAG=2 identifier pattern')
        result = result.mask(special, 'rec2:'+frame.cohort.map(COHORT_CODES)+':'+frame[WORK])
        require(set(frame.FLAG) <= {'1','2'},'Unreviewed recommendation flag')
    return result

def clean_allocation(value):
    original = Decimal(value)
    rounded = original.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
    require(original.is_finite() and abs(original-rounded)<=Decimal('0.000001'), 'Material fractional-paise allocation requires source correction')
    return int(rounded*100), str(rounded-original)

def load(data_dir):
    raw, tables, audit, quarantine, columns = {},defaultdict(list),[],[],{}
    expected_paths={(Path(c)/f).as_posix() for c in COHORTS for f in FILES}
    actual_paths={p.relative_to(data_dir).as_posix() for p in data_dir.rglob('*.csv')}
    check('All CSV files in scope accounted for',sorted(actual_paths),sorted(expected_paths))
    for n,(cohort,kind,filename) in enumerate((c,k,f) for c in COHORTS for k,f in zip(KINDS,FILES)):
        path=data_dir/cohort/filename
        d=pd.read_csv(path,dtype=str,keep_default_na=False,encoding='utf-8-sig')
        rows,digest=CONTRACTS[n]
        check(f'{cohort}/{kind}: source hash',sha(path),digest)
        check(f'{cohort}/{kind}: source rows',len(d),rows)
        originals=list(d.columns); columns[kind]=sorted(set(columns.get(kind,[]))|set(originals))
        d['source_file']=(Path(cohort)/filename).as_posix();d['cohort']=cohort
        d['source_record']=np.arange(1,len(d)+1)
        d['source_id']=[f'{COHORT_CODES[cohort]}:{kind}:{i}' for i in d.source_record]
        raw[f'{COHORT_CODES[cohort]}_{kind}']=d.copy()
        invalid=pd.Series(False,index=d.index)
        if kind=='payments':
            required=[WORK,'VENDOR_ID','FUND_DISBURSED_AMT','EXPENDITURE_DATE','WORK_STATUS','MP_NAME','TENURE_START_DATE','TENURE_END_DATE']
            invalid=d[required].isin(['','NA']).any(axis=1)
            q=d.loc[invalid].copy();q['quarantine_reason']='Missing required payment fields; apparent truncated CSV data record. Not imputed.'
            quarantine.append(q)
        if 'TENURE_START_DATE' in d:
            d['mp_key']=term_key(d)
        if WORK in d:
            d['work_id']=work_keys(d,kind)
        if kind=='allocations':
            amounts=[]
            for row in d.itertuples():
                amount,delta=clean_allocation(row.ALLOCATED_AMT);amounts.append(amount)
                if Decimal(delta)!=0:
                    ADJUSTMENTS.append(dict(source_id=row.source_id,field='ALLOCATED_AMT',original_value=row.ALLOCATED_AMT,prepared_paise=amount,adjustment_inr=delta,reason='Sub-micro-rupee export residue rounded to nearest paise (half-up); original retained'))
            d['allocated_paise']=pd.Series(amounts,dtype='Int64')
        for c in originals:
            nonblank=~d[c].isin(['','NA'])
            columns_row=dict(source_file=(Path(cohort)/filename).as_posix(),field=c,source_rows=len(d),missing_rows=int((~nonblank).sum()),distinct_values=int(d.loc[nonblank,c].nunique()))
            tables['_column_profile'].append(columns_row)
        d=d.loc[~invalid].copy()
        if WORK in d and kind!='payments':check(f'{cohort}/{kind}: namespaced key duplicates',int(d.work_id.duplicated().sum()),0)
        audit.append(dict(cohort=cohort,kind=kind,source_file=(Path(cohort)/filename).as_posix(),sha256=digest,source_rows=rows,accepted_rows=len(d),quarantined_rows=int(invalid.sum()),column_count=len(originals)))
        tables[kind].append(d)
    prof=pd.DataFrame(tables.pop('_column_profile'))
    t={k:pd.concat(v,ignore_index=True) for k,v in tables.items()}
    for k in ['allocations','recommended','sanctioned','completed']:
        check(f'{k}: combined key duplicates',int(t[k]['mp_key' if k=='allocations' else 'work_id'].duplicated().sum()),0)
    for k in ['consents','recommended','sanctioned','payments']:
        check(f'{k}: unmatched MP terms',int((~t[k].mp_key.isin(t['allocations'].mp_key)).sum()),0)
    return t,raw,pd.DataFrame(audit),pd.concat(quarantine,ignore_index=True),prof,columns

def connect(t):
    rec=t['recommended'].set_index('work_id');san=t['sanctioned'].set_index('work_id');comp=t['completed'].set_index('work_id')
    source=san.combine_first(rec).sort_index()
    w=pd.DataFrame(index=source.index)
    field(w,'work_id',source.index,'Namespaced stable key: work:<detail ID> for main records; rec2:<cohort>:<detail ID> for FLAG=2 recommendations. Numeric detail ID alone is unsafe.','03/04/05/06','Join key')
    mapping={'source_work_detail_id':WORK,'cohort':'cohort','mp_key':'mp_key','mp_name':'MP_NAME','state':'STATE_NAME','ida_name':'IDA_NAME','house':'HOUSE_OF_PARLIAMENT','tenure':'TENURE','constituency':'CONSTITUENCY','constituency_id':'CONSTITUENCY_ID','description':'WORK_DESCRIPTION','activity_raw':'ACTIVITY_NAME','work_category':'WORK_CATEGORY','letter_no':'LETTER_NO'}
    for c,original in mapping.items():
        field(w,c,source[original],f'{original} from sanctioned source, otherwise recommendation source; original record retained in SQLite.','04 preferred; 03 fallback','Source snapshot')
    field(w,'identity_namespace',np.where(w.work_id.str.startswith('rec2:'),'recommendation_flag2','main_work'),'Separates incompatible observed ID groups. FLAG=2 business meaning has not been verified.','03/04','Join key')
    field(w,'ida_key',w.state.map(norm)+'|'+w.ida_name.map(norm),'Normalized state plus full implementing district authority name. Not an official district code.','03/04','Source snapshot')
    activity=source.ACTIVITY_NAME.str.replace(r'^WS/\s*MP\d+/\d{4}-\d{4}/\d+-','',regex=True).str.replace(r'^NA-','',regex=True).str.strip()
    field(w,'activity_type',activity,'Activity label after removing work prefix WS/... or NA-.','03/04','Source snapshot')
    field(w,'mp_code_observed',source.LETTER_NO.str.extract(r'MP(\d+)/',expand=False),'MP code extracted from letter number; diagnostic only, not the allocation join key.','03/04','Source snapshot')
    for label,data in [('recommended',rec),('sanctioned',san),('completed',comp)]:
        field(w,'in_'+label,w.index.isin(data.index),f'Record is present in {label} export. Absence is not proof an event never happened.',label,'Source coverage')
        field(w,label+'_source_id',data.source_id.reindex(w.index),'Exact source reference <cohort>:<kind>:<one-based CSV data record>. Embedded newlines mean this is not a physical line number.',label,'Provenance')
    for c,s,raw in [('recommended_amount_paise',rec,'RECOMMENDED_AMOUNT'),('sanction_amount_paise',san,'SANCTION_AMOUNT'),('completion_actual_paise',comp,'ACTUAL_AMOUNT')]:
        field(w,c,money(s[raw]).reindex(w.index),f'{raw} in integer paise from its owning export. Missing membership stays null; explicit zero retained.','03' if s is rec else ('04' if s is san else '05'),'Source snapshot')
    for name,s,raw in [('recommendation_date',source,'RECOMMENDATION_DATE'),('sanction_date',san,'SANCTION_DATE'),('completion_date',comp,'ACTUAL_END_DATE')]:
        field(w,name,dates(s[raw]).reindex(w.index),f'Parsed {raw}; event date, not observation or extraction timestamp.','03/04/05','Event date; knowledge time unavailable')
    for c,raw in [('tenure_start_date','TENURE_START_DATE'),('tenure_end_date','TENURE_END_DATE')]:
        value=pd.to_datetime(source[raw],format='%b %d, %Y %I:%M:%S %p',errors='raise').dt.normalize()
        field(w,c,value,f'Reported {raw}. Term end is a proxy for actual demission; do not infer current office from the TENURE label.','01/03/04','Source snapshot')
    for c,s,raw in [('recommendation_stage_raw',rec,'WORK_STAGE'),('sanction_stage_raw',san,'WORK_STAGE'),('recommendation_flag_raw',rec,'FLAG'),('completion_description_raw',comp,'WORK_DESCRIPTION'),('completion_work_id_raw',comp,'WORK_ID'),('completion_attachment_id',comp,'ATTACH_ID'),('completion_rating_raw',comp,'AVERAGE_RATING')]:
        field(w,c,s[raw].reindex(w.index).replace('',None),f'Original {raw} in {"completion" if s is comp else "recommendation" if s is rec else "sanction"} export. No business meaning invented for opaque codes or zero ratings.','03/04/05','Source snapshot')
    field(w,'lifecycle',np.select([w.in_completed,w.in_sanctioned],['Reported complete','Sanctioned / open'],default='Not in sanction export'),'Completion export determines reported completion; raw stages retained.','03/04/05')
    field(w,'recommendation_missing_flag',~w.in_recommended & w.in_sanctioned,'Sanction is present but no matching recommendation record under a safe key.','03/04','Data quality')
    field(w,'source_stage_difference_flag',w.in_recommended&w.in_sanctioned&w.recommendation_stage_raw.ne(w.sanction_stage_raw),'Different raw stage labels; potentially differing vocabularies or snapshots, not automatically inconsistent events.','03/04','Data quality')
    field(w,'description_changed_flag',w.in_completed & w.description.str.strip().ne(w.completion_description_raw.fillna('').str.strip()),'Completion description differs from the selected work description; inspect both.','04/05','Data quality')
    field(w,'missing_description_flag',w.description.str.strip().eq(''),'No text evidence for description matching.','03/04','Data quality')
    check('Completed keys absent from sanctions',int((~comp.index.isin(san.index)).sum()),0)
    # Non-description identity must agree; differing descriptions/stages remain visible.
    conflicts=[]
    for other,label in [(rec,'recommended'),(comp,'completed')]:
        common=san.index.intersection(other.index)
        for c in ['MP_NAME','STATE_NAME','IDA_NAME','CONSTITUENCY_ID','WORK_DESCRIPTION','WORK_STAGE','SANCTION_AMOUNT','RECOMMENDATION_DATE','TENURE_START_DATE','TENURE_END_DATE']:
            if c not in other:continue
            a=san.loc[common,c];b=other.loc[common,c];bad=a.ne(b)
            for key in common[bad]:
                conflicts.append(dict(work_id=key,field=c,preferred_source_id=san.at[key,'source_id'],other_source_id=other.at[key,'source_id'],preferred_value=a[key],other_value=b[key]))
            if c in ['MP_NAME','STATE_NAME','IDA_NAME','CONSTITUENCY_ID','TENURE_START_DATE','TENURE_END_DATE']:
                check(f'{label}/sanction {c} join disagreement',int(bad.sum()),0)
    conflict=pd.DataFrame(conflicts,columns=['work_id','field','preferred_source_id','other_source_id','preferred_value','other_value'])
    w=w.reset_index(drop=True)
    return w,conflict

def payments(t,w,original_columns):
    raw=t['payments']
    p=raw.rename(columns={'WORK_STATUS':'payment_status','VENDOR_ID':'vendor_id','VENDOR_NAME':'vendor_name','IA_NAME':'ia_name','WORK_ID':'payment_work_id_raw'}).copy()
    p['report_fingerprint']=[stable_hash(list(v)) for v in raw[[c for c in original_columns if c!='Sno']].itertuples(index=False,name=None)]
    p['same_fingerprint_count']=p.groupby('report_fingerprint').report_fingerprint.transform('size')
    p['fingerprint_first_row']=~p.report_fingerprint.duplicated()
    p['repeat_excess_row']=~p.fingerprint_first_row
    p['payment_date']=dates(raw.EXPENDITURE_DATE);p['amount_paise']=money(raw.FUND_DISBURSED_AMT)
    check('Payment keys absent from work master',int((~p.work_id.isin(w.work_id)).sum()),0)
    check('Unexpected payment statuses',len(set(p.payment_status)-{'Payment Success','Payment In-Progress'}),0)
    check('Invalid payment amounts',int((p.amount_paise.isna()|p.amount_paise.lt(0)).sum()),0)
    linked=p.merge(w[['work_id','mp_key','cohort','ida_key','state','activity_type','sanction_date','completion_date']],on='work_id',suffixes=('_report',''),validate='many_to_one')
    check('Payment MP term disagreement',int(linked.mp_key_report.ne(linked.mp_key).sum()),0)
    check('Payment cohort disagreement',int(linked.cohort_report.ne(linked.cohort).sum()),0)
    p=linked
    p['is_success']=p.payment_status.eq('Payment Success')
    p['successful_paise']=p.amount_paise.where(p.is_success,0)
    p['pending_paise']=p.amount_paise.where(~p.is_success,0)
    p['fingerprint_sensitivity_paise']=p.successful_paise.where(p.fingerprint_first_row,0)
    p['payment_before_sanction_flag']=p.payment_date.lt(p.sanction_date)
    p['payment_after_completion_flag']=p.payment_date.gt(p.completion_date)
    p['fiscal_year']=fy(p.payment_date);p['payment_month']=p.payment_date.dt.strftime('%Y-%m')
    p['march_payment_flag']=p.payment_date.dt.month.eq(3)
    p['round_10000_inr_flag']=p.amount_paise.mod(1000000).eq(0)
    agg=p.groupby('work_id').agg(payment_row_count=('work_id','size'),successful_payment_count=('is_success','sum'),successful_payment_paise=('successful_paise','sum'),pending_payment_paise=('pending_paise','sum'),unique_fingerprint_sensitivity_paise=('fingerprint_sensitivity_paise','sum'),repeated_report_excess_rows=('repeat_excess_row','sum'),vendor_count=('vendor_id','nunique'),implementing_agency_count=('ia_name','nunique'),first_payment_date=('payment_date','min'),last_payment_date=('payment_date','max'),payment_before_sanction_flag=('payment_before_sanction_flag','max'),payment_after_completion_count=('payment_after_completion_flag','sum'))
    agg=agg.join(p.loc[p.is_success].groupby('work_id').payment_date.agg(first_success_date='min',last_success_date='max'))
    meanings={
        'payment_row_count':'Accepted expenditure rows, including in-progress requests and repeated reports.',
        'successful_payment_count':'Rows explicitly marked Payment Success; not independently bank-verified.',
        'successful_payment_paise':'Sum of observed Payment Success rows only. Zero means no observed successful amount, not verified zero actual expenditure.',
        'pending_payment_paise':'Sum of Payment In-Progress rows. Excluded from successful expenditure.',
        'unique_fingerprint_sensitivity_paise':'Alternative scenario summing first successful row per identical report fingerprint. Not a corrected ledger.',
        'repeated_report_excess_rows':'Report rows beyond first identical content, ignoring Sno and provenance. Transaction IDs are unavailable.',
        'vendor_count':'Distinct VENDOR_ID values in expenditure rows for this work.',
        'implementing_agency_count':'Distinct IA_NAME strings. No legal agency identifier supplied.',
        'first_payment_date':'Earliest observed expenditure date, any status.',
        'last_payment_date':'Latest observed expenditure date, any status.',
        'first_success_date':'Earliest date on an observed Payment Success row.',
        'last_success_date':'Latest date on an observed Payment Success row.',
        'payment_before_sanction_flag':'Any payment report dated before sanction. Data-quality chronology check.',
        'payment_after_completion_count':'Report rows dated after reported completion. Retention/final settlement may be legitimate.'}
    for c in agg:
        v=w.work_id.map(agg[c])
        if c.endswith(('_count','_rows','_paise')):v=v.fillna(0).astype('int64')
        elif c.endswith('_flag'):v=v.fillna(False).astype(bool)
        field(w,c,v,meanings[c],'06; aggregate before joining to works','Snapshot descriptive')
    field(w,'has_payment_evidence',w.payment_row_count.gt(0),'At least one expenditure row observed.','06','Source coverage')
    field(w,'has_successful_payment_evidence',w.successful_payment_count.gt(0),'At least one Payment Success row observed.','06','Source coverage')
    cols=['source_id','source_file','source_record','cohort','work_id','mp_key','ida_key','state','activity_type','vendor_id','vendor_name','ia_name','payment_status','payment_work_id_raw','report_fingerprint','same_fingerprint_count','fingerprint_first_row','repeat_excess_row','payment_date','amount_paise','is_success','successful_paise','pending_paise','fingerprint_sensitivity_paise','payment_before_sanction_flag','payment_after_completion_flag','fiscal_year','payment_month','march_payment_flag','round_10000_inr_flag']
    return w,p[cols]

def extra_features(w,p,as_of):
    w=legacy.lifecycle_features(w,as_of)
    for name,delta in [('paid_over_sanction_flag','payment_sanction_delta_paise'),('completion_over_sanction_flag','completion_sanction_delta_paise')]:
        field(w,name,w[delta].gt(RECONCILIATION_TOLERANCE_PAISE).fillna(False),'Positive difference exceeds INR 1 screening tolerance; not a legal limit. Exact difference is retained. Check revised sanctions and ledger reconciliation.','04/05/06')
    field(w,'payment_sanction_small_difference_flag',(w.payment_sanction_delta_paise.gt(0)&w.payment_sanction_delta_paise.le(RECONCILIATION_TOLERANCE_PAISE)).fillna(False),'Positive observed payment-sanction difference of at most INR 1; retained as a small reconciliation difference, not a material overrun screen.','04/06','Data quality')
    DEFS['first_success_delay_days']=('Sanction-to-first observed successful payment. Export coverage differs across cohorts.','04/06','Snapshot descriptive')
    w=legacy.cost_features(w)
    ref=pd.Timestamp(as_of)
    additions={
        'term_has_ended_flag':(w.tenure_end_date.lt(ref),'Reported term end precedes assessment date; not a verified office-holder status.'),
        'demission_followup_date':(w.tenure_end_date+pd.DateOffset(months=18),'Reported term end plus 18 calendar months. Proxy for missing actual demission date.'),
        'recommendation_outside_term_flag':(w.recommendation_date.lt(w.tenure_start_date)|w.recommendation_date.gt(w.tenure_end_date),'Recommendation date outside reported term. Historical entry or source correction may explain it.'),
        'legacy_recommendation_flag':(w.recommendation_date.lt(pd.Timestamp('2023-04-01')),'Recommendation predates eSAKSHI revised fund flow; observed legacy entry, not proof of full pre-2023 coverage.'),
        'zero_sanction_amount_flag':(w.in_sanctioned&w.sanction_amount_paise.eq(0),'Explicit zero sanctioned amount. Ratios with zero denominator remain unavailable.'),
        'no_success_three_months_flag':(w.in_sanctioned&~w.has_successful_payment_evidence&(w.sanction_date+pd.DateOffset(months=3)).lt(ref),'No observed successful payment after three calendar months. Includes in-progress requests; incomplete ledger coverage possible.'),
    }
    for c,(v,meaning) in additions.items():field(w,c,v,meaning,'01/03/04/06; MONITOR','Snapshot descriptive')
    field(w,'open_after_demission_18m_flag',w.in_sanctioned&~w.in_completed&w.demission_followup_date.lt(ref),'No completion after reported term end plus 18 months. Confirm actual demission and scheme applicability, especially legacy works.','MONITOR','Snapshot descriptive')
    field(w,'completed_after_demission_18m_flag',w.in_completed&w.completion_date.gt(w.demission_followup_date),'Reported completion after term-end plus 18 months; proxy, not adjudicated non-compliance.','MONITOR','Snapshot descriptive')
    field(w,'paid_over_sanction_sensitivity_flag',(w.unique_fingerprint_sensitivity_paise-w.sanction_amount_paise).gt(RECONCILIATION_TOLERANCE_PAISE).fillna(False),'Payment-over-sanction screen (> INR 1 difference) after retaining one row per report fingerprint. Sensitivity scenario only.','04/06')
    amounts=w.sanction_amount_paise.astype(float)/100
    field(w,'log_sanction_inr',np.log1p(amounts),'Natural log(1 + sanctioned INR). Null when no sanction amount exists.','04','Sanction snapshot')
    march=p.loc[p.is_success].assign(march_paise=lambda d:d.successful_paise.where(d.march_payment_flag,0)).groupby('work_id').march_paise.sum()
    field(w,'march_successful_paise',w.work_id.map(march).fillna(0).astype('int64'),'Successful reported amount dated in March across the observed period. Calendar pattern, not misuse finding.','06')
    field(w,'march_payment_share',ratio(w.march_successful_paise,w.successful_payment_paise),'Observed March successful amount / all observed successful amount. Null if denominator zero.','06')
    return w

def duplicates(w):
    # Bounded local token search. No remote model or transfer of descriptions.
    texts=w.description_normalized.tolist();tokens=[set(s.split())-legacy.STOP for s in texts]
    freq=Counter(t for ts in tokens for t in ts);weights={t:math.log1p(len(w)/(1+n)) for t,n in freq.items()}
    postings=defaultdict(list);rows=[];tested=cap=window=0
    nearest=np.zeros(len(w));count=np.zeros(len(w),dtype=int);strong=np.zeros(len(w),dtype=bool)
    ids=w.work_id.tolist();ida=w.ida_key.tolist();act=w.activity_type.tolist();amt=w.sanction_amount_paise.tolist();phase=w.continuation_cue_flag.tolist()
    for i in range(len(w)):
        anchors=sorted(tokens[i],key=lambda t:(freq[t],t))[:3];candidate=set()
        for token in anchors:
            prior=postings[(ida[i],act[i],token)];window+=int(len(prior)>150);candidate.update(prior[-150:])
        cap+=int(len(candidate)>60);matches=[]
        for j in sorted(candidate,reverse=True)[:60]:
            tested+=1;union=tokens[i]|tokens[j]
            sim=sum(weights[t] for t in sorted(tokens[i]&tokens[j]))/sum(weights[t] for t in sorted(union)) if union else 0
            same=bool(texts[i]) and texts[i]==texts[j];sim=1.0 if same else sim
            if sim<.88:continue
            nums_i=set(re.findall(r'\b\d+\b',texts[i]));nums_j=set(re.findall(r'\b\d+\b',texts[j]))
            conflict=bool(nums_i and nums_j and nums_i!=nums_j);generic=min(len(tokens[i]),len(tokens[j]))<4
            equal=bool(pd.notna(amt[i]) and pd.notna(amt[j]) and amt[i]==amt[j]);cue=bool(phase[i] or phase[j])
            high=sim>=.96 and equal and not(conflict or generic or cue)
            matches.append((sim,j,conflict,generic,equal,cue,high))
        for sim,j,conflict,generic,equal,cue,high in sorted(matches,key=lambda a:(-a[0],ids[a[1]]))[:3]:
            rows.append(dict(pair_id='pair:'+stable_hash(sorted([ids[j],ids[i]]))[:24],work_id_a=ids[j],work_id_b=ids[i],similarity=round(sim,6),same_amount=equal,number_conflict=conflict,generic_text=generic,continuation_cue=cue,high_similarity_review=high,ida_key=ida[i],activity_type=act[i]))
            for k in (i,j):nearest[k]=max(nearest[k],sim);count[k]+=1;strong[k]|=high
        for token in anchors:postings[(ida[i],act[i],token)].append(i)
    field(w,'duplicate_similarity',np.round(nearest,6),'Maximum retained weighted-token similarity, within same IDA and activity. Zero means no retained candidate, not proven uniqueness.','03/04','Full snapshot text vocabulary; not prediction-time safe')
    field(w,'duplicate_candidate_count',count,'Number of retained candidate pairs involving the work. Search is bounded and non-exhaustive.','03/04')
    field(w,'high_similarity_review_flag',strong,'Similarity >=0.96, equal known sanction, at least four non-stop tokens, no numeric mismatch or phase cue. Requires location and scope review.','03/04')
    return w,pd.DataFrame(rows),dict(candidate_comparisons=tested,work_cap_hits=cap,posting_window_hits=window,retained_pairs=len(rows),method='Same IDA/activity; 3 rare tokens; last 150 postings; 60 candidates; top 3 similarities >=0.88. Full-snapshot token frequencies, deterministic key order. No measured duplicate recall.')

SIGNALS={
 'pending_recommendation_45d_flag':('Delay','Recommendation without sanction beyond 45 days','Confirm receipt, rejection and FLAG=2 meaning.'),
 'sanction_delay_45d_flag':('Delay','Recommendation-to-sanction exceeds 45 days','IDA receipt date is missing.'),
 'open_over_one_year_flag':('Delay','No completion beyond one calendar year','Check sanction deadline and extensions.'),
 'no_success_three_months_flag':('Payment','No observed success three months after sanction','Obtain full ledger and pending-request status.'),
 'open_after_demission_18m_flag':('Delay','Open beyond reported term end plus 18 months','Verify actual demission and legacy applicability.'),
 'paid_over_sanction_flag':('Financial','Reported successful payments exceed sanction by > INR 1','Reconcile transaction IDs and revised sanctions.'),
 'completion_over_sanction_flag':('Financial','Reported completion amount exceeds sanction by > INR 1','Check revised scope and sanction orders.'),
 'repeat_payment_report_flag':('Payment','Repeated payment report content','No transaction IDs; do not delete as proven duplicates.'),
 'high_cost_peer_flag':('Cost','High amount versus prior-year peers','Category costs are not unit costs; quantities missing.'),
 'high_similarity_review_flag':('Duplicate candidate','Highly similar descriptions and equal amounts','Verify location, distinct scope and phases.'),
}

def signals(w):
    entries=[]
    for flag,(family,label,caution) in SIGNALS.items():
        for key in w.loc[w[flag].fillna(False),'work_id']:
            entries.append(dict(work_id=key,signal=flag,family=family,reason=label,verification_needed=caution))
    field(w,'screening_signal_count',w[list(SIGNALS)].fillna(False).astype(int).sum(axis=1),'Unweighted count of disclosed investigation screens. Correlated flags may co-occur. Not a risk probability or fraud label.','Signal registry')
    codes=[';'.join(c for c,yes in zip(SIGNALS,row) if yes) for row in w[list(SIGNALS)].fillna(False).itertuples(index=False,name=None)]
    field(w,'screening_reasons',codes,'Semicolon-separated active screens. Work_Signals supplies explanation and evidence requirements.','Signal registry')
    dq=['recommendation_missing_flag','missing_description_flag','description_changed_flag','negative_chronology_flag','future_event_flag','recommendation_outside_term_flag','zero_sanction_amount_flag']
    field(w,'data_quality_issue_count',w[dq].fillna(False).astype(int).sum(axis=1),'Separate count of seven coverage, text, chronology, term and zero-sanction checks. Not added to screening count.','Data quality registry')
    return w,pd.DataFrame(entries)

def entity_tables(t,w,p):
    def grouped(keys):
        return w.groupby(keys,dropna=False).agg(work_count=('work_id','size'),recommended_record_count=('in_recommended','sum'),sanctioned_count=('in_sanctioned','sum'),completed_count=('in_completed','sum'),recommended_paise=('recommended_amount_paise',lambda s:s.sum(min_count=1)),sanction_paise=('sanction_amount_paise',lambda s:s.sum(min_count=1)),successful_payment_paise=('successful_payment_paise','sum'),pending_payment_paise=('pending_payment_paise','sum'),screened_work_count=('screening_signal_count',lambda s:s.gt(0).sum()),open_over_one_year_count=('open_over_one_year_flag','sum'),no_success_three_months_count=('no_success_three_months_flag','sum'),open_after_demission_18m_count=('open_after_demission_18m_flag','sum'))
    a=t['allocations']
    mp=a[['mp_key','cohort','source_id','MP_NAME','HOUSE_NAME','TENURE','STATE_NAME','CONSTITUENCY','TENURE_START_DATE','TENURE_END_DATE','ALLOCATED_AMT','allocated_paise']].rename(columns={'MP_NAME':'mp_name','HOUSE_NAME':'house_name','TENURE':'tenure','STATE_NAME':'allocation_state','CONSTITUENCY':'constituency','ALLOCATED_AMT':'allocated_raw'}).copy()
    for c,raw in [('tenure_start_date','TENURE_START_DATE'),('tenure_end_date','TENURE_END_DATE')]:mp[c]=pd.to_datetime(mp.pop(raw),format='%b %d, %Y %I:%M:%S %p').dt.normalize()
    mp=mp.merge(grouped('mp_key'),on='mp_key',how='left',validate='one_to_one')
    for c in mp:
        if c.endswith('_count'):mp[c]=mp[c].fillna(0).astype('int64')
        elif c.endswith('_paise') and c!='allocated_paise':mp[c]=mp[c].fillna(0).astype('Int64')
    consent=t['consents'].rename(columns={'CALAMITY_NAME':'calamity_name','TYPE':'calamity_type'})
    consent['consent_date']=dates(consent.CRT_DT);consent['consent_amount_paise']=money(consent.CONSENTED_AMOUNT);consent['fiscal_year']=fy(consent.consent_date)
    consent['work_link_available']=False
    consent=consent[['source_id','source_file','source_record','cohort','mp_key','calamity_name','calamity_type','consent_date','consent_amount_paise','fiscal_year','work_link_available']]
    mp['consented_paise']=mp.mp_key.map(consent.groupby('mp_key').consent_amount_paise.sum()).fillna(0).astype('Int64')
    mp['recommendation_to_allocation_ratio']=ratio(mp.recommended_paise,mp.allocated_paise)
    mp['sanction_to_allocation_ratio']=ratio(mp.sanction_paise,mp.allocated_paise)
    mp['observed_paid_to_allocation_ratio']=ratio(mp.successful_payment_paise,mp.allocated_paise)
    mp['completion_to_sanction_ratio']=ratio(mp.completed_count,mp.sanctioned_count)
    ida=grouped(['ida_key','state','ida_name']).reset_index()
    ida['completion_to_sanction_ratio']=ratio(ida.completed_count,ida.sanctioned_count)
    cohort=grouped('cohort').reset_index()
    vendor=p.groupby('vendor_id').agg(vendor_name=('vendor_name','first'),name_variant_count=('vendor_name','nunique'),payment_row_count=('source_id','size'),work_count=('work_id','nunique'),mp_count=('mp_key','nunique'),ida_count=('ida_key','nunique'),successful_payment_paise=('successful_paise','sum'),pending_payment_paise=('pending_paise','sum'),repeat_excess_rows=('repeat_excess_row','sum'),first_payment_date=('payment_date','min'),last_payment_date=('payment_date','max')).reset_index()
    vendor['same_name_vendor_id_count']=vendor.groupby('vendor_name').vendor_id.transform('size')
    edges=p.groupby(['vendor_id','mp_key','ida_key','ia_name','fiscal_year']).agg(payment_row_count=('source_id','size'),work_count=('work_id','nunique'),successful_payment_paise=('successful_paise','sum'),pending_payment_paise=('pending_paise','sum')).reset_index()
    shares=p.loc[p.is_success].groupby(['ida_key','fiscal_year','vendor_id']).successful_paise.sum().reset_index()
    shares['total']=shares.groupby(['ida_key','fiscal_year']).successful_paise.transform('sum')
    shares['vendor_share']=ratio(shares.successful_paise,shares.total);shares['share_squared']=shares.vendor_share**2
    hhi=shares.groupby(['ida_key','fiscal_year']).agg(vendor_hhi=('share_squared','sum'),top_vendor_share=('vendor_share','max'),vendor_count=('vendor_id','nunique'),successful_payment_paise=('successful_paise','sum')).reset_index()
    monthly=p.groupby(['cohort','state','fiscal_year','payment_month']).agg(payment_row_count=('source_id','size'),work_count=('work_id','nunique'),successful_payment_paise=('successful_paise','sum'),pending_payment_paise=('pending_paise','sum')).reset_index()
    return dict(MP_Term_Features=mp,IDA_Features=ida,Cohort_Summary=cohort,Vendor_Features=vendor,Vendor_Connections=edges,IDA_Year_Concentration=hhi,Monthly_Payments=monthly,Calamity_Consents=consent)

def main(data_dir,out,as_of):
    CHECKS.clear();ADJUSTMENTS.clear();DEFS.clear()
    require(out.resolve()!=data_dir.resolve() and not out.resolve().is_relative_to(data_dir.resolve()),'Output must be outside immutable Dataset folder')
    require(not (out/'COMPLETE.json').exists(),'Completed output exists. Use a new output directory; do not overwrite a delivered run.')
    out.mkdir(parents=True,exist_ok=True)
    print('1/7 Validating all 18 source files and preserving raw records',flush=True)
    t,raw,audit,q,prof,columns=load(data_dir)
    print('2/7 Resolving ID namespaces, MP terms and source disagreements',flush=True)
    w,conflicts=connect(t);w,p=payments(t,w,columns['payments'])
    print('3/7 Engineering lifecycle, money, historical peer and term-end features',flush=True)
    w=extra_features(w,p,as_of)
    print('4/7 Generating local, bounded text candidates',flush=True)
    w,pairs,duplicate_meta=duplicates(w);w,screens=signals(w)
    print('5/7 Aggregating MP, IDA, vendor, consent and monthly features',flush=True)
    outputs=entity_tables(t,w,p)
    outputs.update(Work_Features=w,Payment_Features=p,Work_Signals=screens,Duplicate_Candidates=pairs,Source_Audit=audit,Source_Column_Profile=prof,Field_Conflicts=conflicts,Quarantine=q,Normalization_Log=pd.DataFrame(ADJUSTMENTS),Validation_Checks=pd.DataFrame(CHECKS))
    from documentation import dictionary, create_review_data, write_report
    outputs['Feature_Dictionary']=dictionary(outputs,DEFS)
    print('6/7 Independent reconciliations and local artifact export',flush=True)
    check('Work master equals safe recommendation/sanction key union',len(w),len(set(t['recommended'].work_id)|set(t['sanctioned'].work_id)))
    for label,source,col,outcol in [('Recommended',t['recommended'],'RECOMMENDED_AMOUNT','recommended_amount_paise'),('Sanctioned',t['sanctioned'],'SANCTION_AMOUNT','sanction_amount_paise'),('Completion',t['completed'],'ACTUAL_AMOUNT','completion_actual_paise')]:
        check(label+' exact paise reconciliation',int(w[outcol].sum()),int(money(source[col]).sum()))
    for status,col in [('Payment Success','successful_payment_paise'),('Payment In-Progress','pending_payment_paise')]:
        expected=int(money(t['payments'].loc[t['payments'].WORK_STATUS.eq(status),'FUND_DISBURSED_AMT']).sum())
        for table in ['Work_Features','MP_Term_Features','IDA_Features','Vendor_Features','Vendor_Connections','Monthly_Payments','Cohort_Summary']:
            check(f'{table}: {status} paise',int(outputs[table][col].sum()),expected)
    check('Preserved raw records',sum(len(d) for d in raw.values()),int(audit.source_rows.sum()))
    check('Accepted + quarantined records',int(audit.accepted_rows.sum())+len(q),int(audit.source_rows.sum()))
    check('All recommendation rows retained as work entities',int(w.in_recommended.sum()),len(t['recommended']))
    check('All sanction rows retained once',int(w.in_sanctioned.sum()),len(t['sanctioned']))
    check('All completion rows retained once',int(w.in_completed.sum()),len(t['completed']))
    check('All accepted payments retained',len(p),len(t['payments']))
    check('All MP allocation rows retained',len(outputs['MP_Term_Features']),len(t['allocations']))
    check('No duplicated output work keys',int(w.work_id.duplicated().sum()),0)
    check('No missing feature definitions',int(outputs['Feature_Dictionary'].definition.eq('').sum()),0)
    # SQLite keeps raw text unchanged as well as prepared typed feature tables.
    db=sqlite3.connect(out/'mplads_prepared.sqlite3')
    hashes={}
    for name,frame in outputs.items():
        export=legacy.export_frame(frame)
        path=out/(name+'.csv');export.to_csv(path,index=False,encoding='utf-8-sig',lineterminator='\n',float_format='%.10g')
        hashes[path.name]=sha(path)
        export.to_sql(name,db,if_exists='replace',index=False,chunksize=2000)
    for name,frame in raw.items():frame.to_sql('Raw_'+name,db,if_exists='replace',index=False,chunksize=2000)
    db.execute('CREATE UNIQUE INDEX work_key_idx ON Work_Features(work_id)')
    db.execute('CREATE INDEX payment_work_idx ON Payment_Features(work_id)')
    db.execute('CREATE UNIQUE INDEX term_key_idx ON MP_Term_Features(mp_key)')
    db.commit();check('SQLite integrity',db.execute('PRAGMA integrity_check').fetchone()[0],'ok');db.close()
    print('7/7 Documenting findings, limitations and unchanged input hashes',flush=True)
    for row in audit.itertuples():check('Raw unchanged '+row.source_file,sha(data_dir/row.source_file),row.sha256)
    outputs['Validation_Checks']=pd.DataFrame(CHECKS)
    outputs['Validation_Checks'].to_csv(out/'Validation_Checks.csv',index=False,encoding='utf-8-sig',lineterminator='\n')
    hashes['Validation_Checks.csv']=sha(out/'Validation_Checks.csv')
    with sqlite3.connect(out/'mplads_prepared.sqlite3') as final_db:
        outputs['Validation_Checks'].to_sql('Validation_Checks',final_db,if_exists='replace',index=False)
    code_paths=sorted((ROOT/'data_preparation').glob('*.py'))+[ROOT/'six_source'/'common.py',ROOT/'six_source'/'build.py',ROOT/'pipeline_research'/'build_features.py']
    manifest=dict(version=VERSION,as_of=as_of,python=sys.version.split()[0],pandas=pd.__version__,numpy=np.__version__,inputs=to_records(audit),outputs={k:dict(rows=len(v),columns=len(v.columns)) for k,v in outputs.items()},csv_sha256=hashes,code_sha256={str(f.relative_to(ROOT)):sha(f) for f in code_paths},duplicate_search=duplicate_meta,checks=CHECKS)
    write_report(out,outputs,manifest)
    write_json(out/'review_data.json',create_review_data(outputs,manifest))
    write_json(out/'manifest.json',manifest)
    write_json(out/'COMPLETE.json',dict(version=VERSION,as_of=as_of,work_rows=len(w),accepted_payment_rows=len(p),raw_unchanged=True,checks_passed=len(CHECKS)))
    print(json.dumps(dict(work_rows=len(w),payment_rows=len(p),MP_terms=len(outputs['MP_Term_Features']),signals={c:int(w[c].sum()) for c in SIGNALS},checks_passed=len(CHECKS)),indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--data-dir',type=Path,default=ROOT/'Dataset');parser.add_argument('--output-dir',type=Path,default=ROOT/'data_preparation'/'local'/'release_2026-09-10_v2');parser.add_argument('--as-of',default=AS_OF)
    args=parser.parse_args();main(args.data_dir,args.output_dir,args.as_of)
