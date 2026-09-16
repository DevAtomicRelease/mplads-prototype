"""Independent saved-result audit; never imports the experiment implementation.

Reads CSV with the standard library, computes ranks with Python sorting, and
audits bootstrap selection through multiplicities rather than reranking copies.
Only an explicitly requested, new JSON audit report may be written.
"""
import argparse
import calendar
from collections import Counter, defaultdict
import csv
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import re
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data_preparation/local/release_2026-09-10_v2'
SEED = 26102
SHARED = ['pending_recommendation_45d_flag', 'sanction_delay_45d_flag',
          'open_over_one_year_flag', 'no_success_three_months_flag',
          'open_after_demission_18m_flag', 'paid_over_sanction_flag',
          'completion_over_sanction_flag', 'repeat_payment_report_flag']
CHECKS = []

def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(2**20), b''):
            h.update(chunk)
    return h.hexdigest()

def yes(value):
    if value not in {'True', 'False'}:
        raise ValueError('Noncanonical Boolean: ' + repr(value))
    return value == 'True'

def check(name, condition, detail=None):
    item = dict(check=name, passed=bool(condition))
    if detail is not None:
        item['detail'] = detail
    CHECKS.append(item)
    if not condition:
        raise AssertionError(name)

def close(actual, expected):
    return abs(float(actual) - float(expected)) <= 1e-10

def tie(key, seed=SEED):
    return int(hashlib.sha256((str(seed)+':'+key).encode()).hexdigest()[:16], 16)

def ordering(records, arm, key, seed=SEED):
    return sorted(range(len(records)), key=lambda i: (-int(records[i]['score_'+arm]), tie(records[i][key], seed)))

def components(records, label):
    for row in records:
        shared = sum(yes(row[k]) for k in SHARED)
        assert int(row['score_a']) == shared + yes(row['exact_duplicate'])
        assert int(row['score_b']) == shared + yes(row['near_duplicate']) + yes(row['high_cost_peer_flag'])
        assert yes(row['near_duplicate']) >= yes(row['exact_duplicate'])
    check(label+' all component sums and monotonicity', True, len(records))

def add_months(value, count):
    index=value.year*12+value.month-1+count
    year,month=divmod(index,12);month+=1
    return date(year,month,min(value.day,calendar.monthrange(year,month)[1]))

def shared_from_primitives(row):
    dt=lambda key: date.fromisoformat(row[key]) if row[key] else None
    rec,san,comp,term=[dt(key) for key in ['recommended_date','sanction_date','completion_date','term_end_date']]
    amount=int(row['sanction_paise']) if row['sanction_paise'] else None
    final=int(row['completion_paise']) if row['completion_paise'] else None
    payments=json.loads(row['payments'])
    success=[p for p in payments if p['status']=='Payment Success']
    paid=sum(p['amount_paise'] for p in success)
    asof=date(2026,9,10)
    fingerprints=[(p['vendor_id'],p['date'],p['amount_paise'],p['status']) for p in payments]
    return [san is None and rec is not None and (asof-rec).days>45,
            san is not None and rec is not None and (san-rec).days>45,
            san is not None and comp is None and add_months(san,12)<asof,
            san is not None and not success and add_months(san,3)<asof,
            san is not None and comp is None and term is not None and add_months(term,18)<asof,
            amount is not None and bool(success) and paid>amount+100,
            amount is not None and final is not None and final>amount+100,
            len(fingerprints)!=len(set(fingerprints))],paid

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('run',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();run=args.run.resolve()
    if args.report:
        destination=args.report.resolve()
        safe=(ROOT/'evaluation_18/local').resolve()
        if safe not in destination.parents or destination.exists() or run in destination.parents:
            raise ValueError('Audit report must be a new file under evaluation_18/local, outside a run')
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    for filename,digest in manifest['output_sha256'].items():
        check('Saved artifact hash '+filename,sha(run/filename)==digest)
    for filename,digest in manifest['verified_input_sha256'].items():
        check('Preserved input hash '+filename,sha(ROOT/filename)==digest)
    for filename,digest in manifest['code_sha256'].items():
        check('Frozen code hash '+filename,sha(ROOT/'evaluation_18'/filename)==digest)
    real=rows(run/'Real_Scores.csv')
    cols=['work_id','description_normalized','in_sanctioned','sanction_date','sanction_amount_paise','state','activity_type']+SHARED+['high_cost_peer_flag','high_similarity_review_flag']
    with (SOURCE/'Work_Features.csv').open(encoding='utf-8-sig',newline='') as stream:
        prepared={r['work_id']:{k:r[k] for k in cols} for r in csv.DictReader(stream)}
    check('Real key population conserved',len(real)==len(prepared)==160701 and {r['work_id'] for r in real}==set(prepared))
    for row in real:
        original=prepared[row['work_id']]
        for flag in SHARED+['high_cost_peer_flag']:
            assert yes(row[flag])==yes(original[flag])
    check('Real shared and cost flags match locked release',True)
    exact=set();near=set()
    for pair in rows(SOURCE/'Duplicate_Candidates.csv'):
        if yes(pair['high_similarity_review']):
            a,b=pair['work_id_a'],pair['work_id_b'];near.update([a,b])
            assert yes(pair['same_amount']) and not any(yes(pair[k]) for k in ['number_conflict','generic_text','continuation_cue'])
            if prepared[a]['description_normalized']==prepared[b]['description_normalized']:
                assert prepared[a]['description_normalized']
                exact.update([a,b])
    check('Real exact/near components reconstructed from all stored pairs',all(yes(r['exact_duplicate'])==(r['work_id'] in exact) and yes(r['near_duplicate'])==(r['work_id'] in near) for r in real))
    check('Real near component equals locked feature',all(yes(r['near_duplicate'])==yes(prepared[r['work_id']]['high_similarity_review_flag']) for r in real))
    components(real,'Real')
    orders={arm:ordering(real,arm,'work_id') for arm in ['a','b']}
    for arm,order in orders.items():
        check('Real saved rank '+arm,all(int(real[i]['rank_'+arm])==j+1 for j,i in enumerate(order)))
    queue=rows(run/'Real_Queue_Comparison.csv')
    for q in queue:
        k=math.ceil(float(q['budget'])*len(real));a=set(orders['a'][:k]);b=set(orders['b'][:k])
        check('Real overlap/counts budget '+q['budget'],int(q['reviewed_per_arm'])==k and int(q['overlap'])==len(a&b) and int(q['new_b'])==len(b-a) and int(q['displaced_a'])==len(a-b) and close(q['jaccard'],len(a&b)/len(a|b)))
        for arm in ['a','b']:
            selected=orders[arm][:k];boundary=int(real[selected[-1]]['score_'+arm]);scores=[int(r['score_'+arm]) for r in real]
            check('Real ties/workload '+arm+' '+q['budget'],int(q[arm+'_zero_score_fillers'])==sum(scores[i]==0 for i in selected) and int(q[arm+'_positive_score_workload'])==sum(s>0 for s in scores) and int(q[arm+'_boundary_score'])==boundary and int(q[arm+'_boundary_tie_population'])==scores.count(boundary) and int(q[arm+'_boundary_tie_selected'])==sum(scores[i]==boundary for i in selected))
    for entry in rows(run/'Real_Cohort_Mix.csv'):
        k=math.ceil(float(entry['budget'])*len(real));selected=orders[entry['arm'].lower()][:k]
        actual=sum(real[i]['cohort']==entry['cohort'] for i in selected)
        assert int(entry['selected'])==actual and close(entry['share'],actual/k)
    check('Real cohort mix independently reconciled',True)
    for entry in rows(run/'Real_Screen_Coverage.csv'):
        k=math.ceil(float(entry['budget'])*len(real));flag=entry['screen'];selected=orders[entry['arm'].lower()][:k]
        assert int(entry['selected_with_screen'])==sum(yes(real[i][flag]) for i in selected)
        assert int(entry['population_with_screen'])==sum(yes(r[flag]) for r in real)
    check('Real screen coverage independently reconciled',True)
    membership=rows(run/'Reference_Membership.csv')
    eligible={key for key,row in prepared.items() if yes(row['in_sanctioned']) and row['sanction_date'] and row['sanction_date']<='2025-03-31' and row['sanction_amount_paise']}
    check('Historical reference membership and cutoff',len(membership)==len(eligible) and {r['work_id'] for r in membership}==eligible)
    primitive=rows(run/'Synthetic_Primitives.csv');oracle=rows(run/'Synthetic_Oracle.csv');test=rows(run/'Test_Scores.csv');development=rows(run/'Development_Scores.csv')
    primitive_by={r['case_id']:r for r in primitive};oracle_by={r['case_id']:r for r in oracle}
    check('Synthetic populations',len(primitive)==len(oracle)==9000 and len(test)==7200 and len(development)==1800 and len(primitive_by)==9000)
    check('Oracle columns excluded from primitive input',not(set(primitive[0])&{'family','synthetic_positive','observability','oracle_explanation'}))
    check('Development scores excluded from oracle labels',not(set(development[0])&{'family','synthetic_positive','observability','oracle_explanation'}))
    check('Development/test context disjointness',not({r['context_id'] for r in development}&{r['context_id'] for r in test}))
    for row in test+development:
        flags,paid=shared_from_primitives(primitive_by[row['case_id']])
        assert flags==[yes(row[k]) for k in SHARED] and paid==int(row['successful_paise'])
    check('All 9000 primitive operational/financial flags independently recalculated',True)
    components(test,'Synthetic test');components(development,'Synthetic development')
    for row in test:
        assert all(row[k]==oracle_by[row['case_id']][k] for k in ['context_id','split','family','synthetic_positive','observability','oracle_explanation'])
    check('Test labels correctly joined only after scoring',True)
    test_orders={arm:ordering(test,arm,'case_id') for arm in ['a','b']}
    labels=np.array([int(r['synthetic_positive']) for r in test]);positives=int(labels.sum())
    metric_rows=rows(run/'Controlled_Metrics.csv')
    for metric in metric_rows:
        arm=metric['arm'].lower();budget=float(metric['budget']);k=math.ceil(budget*len(test));selected=set(test_orders[arm][:k]);tp=sum(labels[i] for i in selected);fp=k-tp;fn=positives-tp;tn=len(test)-positives-fp
        check('Controlled confusion matrix '+arm+' '+str(budget),all(int(metric[key])==value for key,value in [('population',len(test)),('positives',positives),('negatives',len(test)-positives),('reviewed',k),('true_positive',tp),('false_positive',fp),('false_negative',fn),('true_negative',tn)]) and close(metric['recovery'],tp/positives) and close(metric['controlled_yield'],tp/k) and close(metric['normal_selection_rate'],fp/(len(test)-positives)))
        flag='selected_'+arm+'_'+str(int(budget*100))
        check('Saved controlled selection '+flag,all(yes(r[flag])==(i in selected) for i,r in enumerate(test)))
    for entry in rows(run/'Controlled_Families.csv'):
        matches=[r for r in test if r['family']==entry['family'] and r['synthetic_positive']==entry['synthetic_positive'] and r['observability']==entry['observability']]
        key='selected_'+entry['arm'].lower()+'_'+str(int(float(entry['budget'])*100));found=sum(yes(r[key]) for r in matches)
        assert len(matches)==int(entry['population']) and found==int(entry['selected']) and close(found/len(matches),entry['selection_rate'])
    check('Every controlled family count/rate independently reconciled',True)
    for entry in rows(run/'Threshold_Workload.csv'):
        arm=entry['arm'].lower();selected=[i for i,r in enumerate(test) if int(r['score_'+arm])>0];tp=int(labels[selected].sum());fp=len(selected)-tp
        assert int(entry['alert_workload'])==len(selected) and int(entry['true_positive'])==tp and int(entry['false_positive'])==fp and close(entry['recovery'],tp/positives) and close(entry['normal_selection_rate'],fp/(len(test)-positives))
    check('Score-positive threshold workload and outcome totals',True)
    ties=rows(run/'Tie_Sensitivity.csv');deltas=[];k=math.ceil(.10*len(test))
    for entry in ties:
        seed=int(entry['tie_seed']);rates={arm:sum(labels[i] for i in ordering(test,arm,'case_id',seed)[:k])/positives for arm in ['a','b']}
        assert close(entry['recovery_a'],rates['a']) and close(entry['recovery_b'],rates['b']) and close(entry['recovery_difference'],rates['b']-rates['a'])
        deltas.append(rates['b']-rates['a'])
    check('All 20 alternate tie seeds independently recomputed',len(ties)==20)
    groups=defaultdict(list)
    for i,r in enumerate(test):groups[r['context_id']].append(i)
    ordered_contexts=sorted(groups);context_number={key:i for i,key in enumerate(ordered_contexts)}
    check('Exactly 400 test contexts with 18 siblings and 9 positives',len(groups)==400 and all(len(v)==18 and labels[v].sum()==9 for v in groups.values()))
    per_row_context=np.array([context_number[r['context_id']] for r in test]);rng=np.random.default_rng(SEED+303);boot=rows(run/'Paired_Bootstrap.csv');differences=[]
    check('1000 recorded bootstrap draws',len(boot)==1000)
    for iteration,entry in enumerate(boot):
        counts=np.bincount(rng.integers(0,400,400),minlength=400);multiplicity=counts[per_row_context]
        assert multiplicity.sum()==len(test) and (multiplicity*labels).sum()==positives
        rates={}
        for arm in ['a','b']:
            order=np.asarray(test_orders[arm]);copies=multiplicity[order];before=np.cumsum(copies)-copies;take=np.minimum(copies,np.maximum(0,k-before))
            assert take.sum()==k
            rates[arm]=float((take*labels[order]).sum()/positives)
        assert int(entry['resample'])==iteration and close(entry['recovery_a'],rates['a']) and close(entry['recovery_b'],rates['b']) and close(entry['recovery_difference'],rates['b']-rates['a'])
        differences.append(rates['b']-rates['a'])
    check('All 1000 paired-context draws independently reconciled by multiplicity allocation',True)
    interval=np.quantile(differences,[.025,.975]).tolist();metrics=json.loads((run/'metrics.json').read_text())
    check('Reported bootstrap percentile interval',all(close(x,y) for x,y in zip(interval,metrics['controlled']['recovery_difference_95_interval'])))
    for item in metrics['controlled']['metrics']:
        match=next(r for r in metric_rows if float(r['budget'])==item['budget'] and r['arm']==item['arm'])
        assert all(close(match[key],value) for key,value in item.items() if key!='arm')
    check('Machine-readable metric JSON matches audited metric CSV',True)
    for filename,digest in manifest['output_sha256'].items():
        assert sha(run/filename)==digest
    check('All frozen result artifacts unchanged by independent audit',True)
    primary={r['arm']:int(r['true_positive']) for r in metric_rows if float(r['budget'])==.10}
    report=dict(passed=all(c['passed'] for c in CHECKS),check_count=len(CHECKS),checks=CHECKS,audit_script_sha256=sha(Path(__file__)),run_manifest_sha256=sha(run/'manifest.json'),primary_positives_recovered=primary,primary_budget_per_arm=k,primary_total_constructed_positives=positives,bootstrap_95_interval_difference=interval,tie_seed_results=dict(b_positive=int(sum(x>0 for x in deltas)),equal=int(sum(x==0 for x in deltas)),b_negative=int(sum(x<0 for x in deltas)),minimum_difference=float(min(deltas)),maximum_difference=float(max(deltas))),limits=['Independent accounting audit, not validation of real fraud truth.','Uncertainty is conditional on synthetic contexts and frozen tie ordering.','Synthetic cost/pair mechanism formulas were reviewed separately, not re-executed by this audit.'])
    report_text=json.dumps(report,indent=2,allow_nan=False)
    if args.report:
        with args.report.open('x',encoding='utf-8') as stream:stream.write(report_text)
    print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))

if __name__=='__main__':main()
