"""Read-only profiling by default; --output saves a reproducible local profile."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'six_source'))
from common import sha, paise, name_key, json_safe

COHORTS = ['Lok Sabha', 'Rajya_Sabha_retired', 'Rajya_Sabha_sitting']
KINDS = ['allocations', 'consents', 'recommended', 'sanctioned', 'completed', 'payments']
FILES = ['01_allocated_limit.csv', '02_calamity_consent.csv', '03_works_recommended.csv',
         '04_works_sanctioned.csv', '05_works_completed.csv', '06_expenditure.csv']
WORK = 'WORK_RECOMMENDATION_DTL_ID'

def term_key(df):
    return df.HOUSE_OF_PARLIAMENT + '|' + df.MP_NAME.map(name_key) + '|' + df.TENURE_START_DATE + '|' + df.TENURE_END_DATE

def profile(root):
    frames, records = {}, []
    for cohort in COHORTS:
        for kind, filename in zip(KINDS, FILES):
            path = root / cohort / filename
            d = pd.read_csv(path, dtype=str, keep_default_na=False, encoding='utf-8-sig')
            frames[(cohort, kind)] = d
            rec = dict(cohort=cohort, kind=kind, file=str(path.relative_to(root)), sha256=sha(path),
                       bytes=path.stat().st_size, rows=len(d), columns=list(d.columns),
                       missing={c:int(d[c].isin(['','NA']).sum()) for c in d if d[c].isin(['','NA']).any()},
                       duplicate_rows_excluding_serial=int(d.drop(columns=['Sno'], errors='ignore').duplicated().sum()))
            if WORK in d:
                rec.update(work_ids=d[WORK].nunique(), duplicate_work_ids=int(d[WORK].duplicated().sum()))
            if 'HOUSE_OF_PARLIAMENT' in d:
                rec.update(houses=d.HOUSE_OF_PARLIAMENT.value_counts().to_dict(), tenures=d.TENURE.value_counts().to_dict(), terms=term_key(d).nunique())
            rec['dates'] = {}
            rec['money_paise'] = {}
            for c in d:
                if c.endswith('_DATE') or c == 'CRT_DT':
                    fmt = '%b %d, %Y %I:%M:%S %p' if c.startswith('TENURE_') else '%d-%b-%Y'
                    s = pd.to_datetime(d[c].replace({'':None,'NA':None}),format=fmt,errors='coerce')
                    bad = ~d[c].isin(['','NA']) & s.isna()
                    rec['dates'][c] = dict(min=str(s.min()),max=str(s.max()),invalid=int(bad.sum()),bad_examples=d.loc[bad,c].unique().tolist()[:3])
                if c.endswith('_AMOUNT') or c in ['ALLOCATED_AMT','FUND_DISBURSED_AMT']:
                    bad_money=[]
                    def parse(value):
                        try: return paise(value)
                        except ValueError:
                            bad_money.append(value)
                            return None
                    s = pd.Series([parse(v) for v in d[c]],dtype='Int64')
                    rec['money_paise'][c] = dict(sum_valid=int(s.sum()),missing_or_invalid=int(s.isna().sum()),negative=int(s.lt(0).sum()),zero=int(s.eq(0).sum()),invalid=len(bad_money),invalid_examples=sorted(set(bad_money))[:10])
            if 'WORK_STATUS' in d:
                rec['statuses'] = d.WORK_STATUS.value_counts().to_dict()
            records.append(rec)
    joins = []
    for cohort in COHORTS:
        alloc = frames[cohort,'allocations']
        ak = set(term_key(alloc))
        rs = {k:set(frames[cohort,k][WORK]) - {''} for k in KINDS[2:]}
        joins.append(dict(cohort=cohort, allocated_term_duplicates=int(term_key(alloc).duplicated().sum()),
            terms_unmatched={k:len(set(term_key(frames[cohort,k]))-ak) for k in ['consents','recommended','sanctioned','payments']},
            sanctioned_not_recommended=len(rs['sanctioned']-rs['recommended']),
            completed_not_sanctioned=len(rs['completed']-rs['sanctioned']),
            paid_not_sanctioned=len(rs['payments']-rs['sanctioned']),work_union=len(set.union(*rs.values()))))
    overlaps = []
    for i,a in enumerate(COHORTS):
        for b in COHORTS[i+1:]:
            overlaps.append(dict(a=a,b=b,work_overlap={k:len(set(frames[a,k][WORK]) & set(frames[b,k][WORK]) - {''}) for k in KINDS[2:]},
                                 allocated_term_overlap=len(set(term_key(frames[a,'allocations'])) & set(term_key(frames[b,'allocations'])))))
    return dict(sources=records, joins=joins, overlaps=overlaps)

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,default=ROOT/'Dataset');p.add_argument('--output',type=Path)
    a=p.parse_args();result=profile(a.data_dir)
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(json_safe(result),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    compact={**result,'sources':[{k:v for k,v in r.items() if k not in ['columns','bytes','sha256']} for r in result['sources']]}
    print(json.dumps(json_safe(compact),ensure_ascii=False,indent=2))
