"""Reproduce the frozen paired offline comparison. Raw/prepared inputs are read-only."""
import argparse
import hashlib
import json
import math
import platform
from pathlib import Path
import numpy as np
import pandas as pd
from methods import SEED, SHARED, FrozenPeers, primitive_features, combine, tie_values, rank
from benchmark import generate

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
DEFAULT=ROOT/'data_preparation/local/release_2026-09-10_v2'
BUDGETS=[.05,.10,.20]

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()

def save_json(path,data):
    path.write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')

def write_csv(out,name,frame):
    frame.to_csv(out/(name+'.csv'),index=False,lineterminator='\n',float_format='%.12g')

def select(frame,key,seed=SEED):
    ties=tie_values(frame[key],seed)
    return {arm:rank(frame['score_'+arm],ties) for arm in ['a','b']}

def queue_detail(frame,order,arm,k):
    score=frame['score_'+arm].to_numpy();idx=order[:k];boundary=score[order[k-1]]
    return dict(zero_score_fillers=int((score[idx]==0).sum()),boundary_score=int(boundary),boundary_tie_population=int((score==boundary).sum()),boundary_tie_selected=int((score[idx]==boundary).sum()),positive_score_workload=int((score>0).sum()))

def confusion(positive,selected):
    p=np.asarray(positive,dtype=bool);s=np.asarray(selected,dtype=bool)
    return dict(true_positive=int((p&s).sum()),false_positive=int((~p&s).sum()),false_negative=int((p&~s).sum()),true_negative=int((~p&~s).sum()))

def real_comparison(works,pairs,out):
    flags=SHARED+['high_cost_peer_flag','high_similarity_review_flag']
    f=works[['work_id','cohort']+flags].copy()
    names=works.set_index('work_id').description_normalized.fillna('')
    same=pairs.work_id_a.map(names).eq(pairs.work_id_b.map(names))
    eligible=pairs.high_similarity_review.astype(bool)&same
    exact=set(pairs.loc[eligible,'work_id_a'])|set(pairs.loc[eligible,'work_id_b'])
    f['exact_duplicate']=f.work_id.isin(exact)
    f['near_duplicate']=f.high_similarity_review_flag.astype(bool)
    f=combine(f);orders=select(f,'work_id')
    for arm in ['a','b']:
        ranks=np.empty(len(f),dtype=int);ranks[orders[arm]]=np.arange(1,len(f)+1);f['rank_'+arm]=ranks
    rows=[];mix=[];coverage=[]
    for budget in BUDGETS:
        k=math.ceil(len(f)*budget);a=set(orders['a'][:k]);b=set(orders['b'][:k]);overlap=len(a&b)
        rows.append(dict(budget=budget,population=len(f),reviewed_per_arm=k,overlap=overlap,new_b=len(b-a),displaced_a=len(a-b),jaccard=overlap/len(a|b)))
        for arm in ['a','b']:
            idx=orders[arm][:k];part=f.iloc[idx]
            rows[-1].update({arm+'_'+key:val for key,val in queue_detail(f,orders[arm],arm,k).items()})
            for cohort,n in part.cohort.value_counts().sort_index().items():mix.append(dict(budget=budget,arm=arm.upper(),cohort=cohort,selected=int(n),share=n/k))
            for flag in SHARED+['exact_duplicate','near_duplicate','high_cost_peer_flag']:
                coverage.append(dict(budget=budget,arm=arm.upper(),screen=flag,selected_with_screen=int(part[flag].sum()),population_with_screen=int(f[flag].sum())))
    for name,df in [('Real_Scores',f),('Real_Queue_Comparison',pd.DataFrame(rows)),('Real_Cohort_Mix',pd.DataFrame(mix)),('Real_Screen_Coverage',pd.DataFrame(coverage))]:write_csv(out,name,df)
    return rows

def controlled_metrics(frame,out):
    test=frame.loc[frame.split.eq('test')].reset_index(drop=True)
    orders=select(test,'case_id');positive=test.synthetic_positive.to_numpy(int);n=len(test);p=int(positive.sum());neg=n-p
    metrics=[];families=[]
    for budget in BUDGETS:
        k=math.ceil(n*budget)
        for arm in ['a','b']:
            selected=np.zeros(n,dtype=bool);selected[orders[arm][:k]]=True
            test[f'selected_{arm}_{int(budget*100)}']=selected
            counts=confusion(positive,selected);tp=counts['true_positive'];fp=counts['false_positive']
            assert sum(counts.values())==n and tp+fp==k
            metrics.append(dict(budget=budget,arm=arm.upper(),population=n,positives=p,negatives=neg,reviewed=k,**counts,recovery=tp/p,controlled_yield=tp/k,normal_selection_rate=fp/neg,**queue_detail(test,orders[arm],arm,k)))
            for (family,label,visibility),g in test.groupby(['family','synthetic_positive','observability'],sort=True):
                found=int(selected[g.index].sum());families.append(dict(budget=budget,arm=arm.upper(),family=family,synthetic_positive=int(label),observability=visibility,population=len(g),selected=found,selection_rate=found/len(g)))
    # Every bootstrap draw keeps all 18 siblings in a context; arms share each draw.
    groups=[np.array(v,dtype=int) for _,v in test.groupby('context_id',sort=True).groups.items()]
    assert all(len(g)==18 for g in groups) and len(groups)==400
    contexts=np.stack(groups);rng=np.random.default_rng(SEED+303);ties=tie_values(test.case_id)
    sa=test.score_a.to_numpy();sb=test.score_b.to_numpy();k=math.ceil(n*.10);boot=[]
    for iteration in range(1000):
        idx=contexts[rng.integers(0,len(contexts),size=len(contexts))].ravel();denom=int(positive[idx].sum())
        ra=positive[idx[rank(sa[idx],ties[idx])[:k]]].sum()/denom
        rb=positive[idx[rank(sb[idx],ties[idx])[:k]]].sum()/denom
        boot.append(dict(resample=iteration,recovery_a=float(ra),recovery_b=float(rb),recovery_difference=float(rb-ra)))
    interval=np.quantile([r['recovery_difference'] for r in boot],[.025,.975]).tolist()
    sensitivity=[]
    for seed in [SEED+500+i for i in range(20)]:
        alt=select(test,'case_id',seed)
        ra=float(positive[alt['a'][:k]].sum()/p);rb=float(positive[alt['b'][:k]].sum()/p)
        sensitivity.append(dict(tie_seed=seed,recovery_a=ra,recovery_b=rb,recovery_difference=rb-ra))
    thresholds=[]
    for arm in ['a','b']:
        chosen=test['score_'+arm].to_numpy()>0;tp=int(positive[chosen].sum());fp=int(chosen.sum())-tp
        thresholds.append(dict(arm=arm.upper(),alert_workload=int(chosen.sum()),true_positive=tp,false_positive=fp,recovery=tp/p,normal_selection_rate=fp/neg))
    for name,df in [('Test_Scores',test),('Controlled_Metrics',pd.DataFrame(metrics)),('Controlled_Families',pd.DataFrame(families)),('Paired_Bootstrap',pd.DataFrame(boot)),('Tie_Sensitivity',pd.DataFrame(sensitivity)),('Threshold_Workload',pd.DataFrame(thresholds))]:write_csv(out,name,df)
    return dict(metrics=metrics,recovery_difference_95_interval=interval,bootstrap_contexts=400,bootstrap_resamples=1000,tie_sensitivity=sensitivity,thresholds=thresholds)

def report(out,real,controlled,reference_n):
    m={x['arm']:x for x in controlled['metrics'] if x['budget']==.10};a,b=m['A'],m['B'];lo,hi=controlled['recovery_difference_95_interval'];delta=b['recovery']-a['recovery'];r=next(x for x in real if x['budget']==.10)
    direction='higher' if delta>0 else ('lower' if delta<0 else 'equal')
    text=f'''# Offline A/B results - PS 26102

## Decision

At the locked 10% budget, B has **{direction} controlled recovery** than A ({a['recovery']:.2%} vs {b['recovery']:.2%}; B-A {delta*100:+.2f} percentage points; paired-context 95% interval [{lo*100:+.2f}, {hi*100:+.2f}] points). This is a synthetic mechanism test, not fraud accuracy or a live randomized trial. Do not replace the operational queue on this evidence alone. Keep baseline and enhanced screens separately visible, collect supporting documents and use human adjudication.

## Controlled test

7,200 wholly synthetic test cases in 400 contexts; 3,600 constructed positives and 3,600 controls. Each arm reviews 720 cases. A recovers {a['true_positive']} constructed positives and selects {a['false_positive']} controls; B recovers {b['true_positive']} positives and selects {b['false_positive']} controls. Labels refer to constructed events, not real people, agencies or fraud. An additional 1,800 development cases were saved separately without fitting any parameter to them. Historical reference: {reference_n:,} sanctioned works through 31 March 2025. All generated sanctions are after that cutoff.

See Controlled_Families.csv for every family loss/gain, including the controls whose exonerating facts are unobserved. An approved extension, distinct physical assets, greater legitimate scope or an export artifact can look suspicious with the available fields. Sensitivity across 20 tie seeds and 1,000 paired whole-context bootstrap draws is provided; the interval describes synthetic-context variation only. Zero-score fillers and boundary ties are explicit. Artificial 50% positive prevalence means controlled yield does not estimate operational precision.

## Real snapshot queue

All 160,701 works were scored without assigning truth labels. Each arm's 10% list has {r['reviewed_per_arm']:,} works: {r['overlap']:,} overlap, {r['new_b']:,} enter B and {r['displaced_a']:,} A cases are displaced. Queue Jaccard overlap is {r['jaccard']:.2%}. These are changes in review allocation, not verified improvements. Real precision, recall, false-positive rate, fraud prevalence, money saved and predictive accuracy are unknown.

Real_Scores.csv contains both ranks, scores and components keyed by preserved namespaced IDs. Real_Cohort_Mix.csv and Real_Screen_Coverage.csv expose shifts by cohort and screen. The real-data feature release uses a full current snapshot with prior-financial-year peer costs; it is retrospective, not an event-time forecast. Its stored bounded duplicate candidate set is shared by both arms; neither exhaustive retrieval nor recall of all actual duplicates has been validated. The synthetic duplicate benchmark tests one supplied pair, not large-scale retrieval.

## Reproducibility and safeguards

PROTOCOL.md, methods.py, benchmark.py, run_ab.py and tests.py are fingerprinted in manifest.json. Raw and prepared CSV input hashes are verified before processing and again afterward. All output data stay local; no dataset is edited or uploaded. Metrics are computed from primitive dates, amounts, descriptions and payment records before joining the separate synthetic oracle. Thresholds and weights are frozen; results do not trigger retuning.

Run the same command into a different empty directory, then use verify_repro.py to compare every recorded CSV/JSON/Markdown artifact. Reproducibility verification is recorded separately after that second run. Exact rebuild verifies determinism, not real-world validity.

## Known scope limits

This benchmark stresses nine anomaly families and nine control families; it does not estimate their real prevalence or fully cover every production screen (for example, pending recommendations have no dedicated generated family). Boundary unit tests supplement, not replace, external validation. Synthetic payment fingerprints hold omitted report fields constant and cannot validate bank-level transaction identity. Synthetic cohort names are contextual labels, not representative parliamentary demographic samples. No learned supervised fraud classifier, forecasting model, image inspection or live compliance determination is validated here.

Policy cues are investigation proxies: recommendation date is not proven authority receipt date; reported term end is not always verified demission; one-year completion can have approved exceptions. Missing successful payment in an export is not proof of non-payment. INR1 is a declared rounding-screen tolerance, not a statutory entitlement.

Research: [MoSPI monitoring definitions](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2153066&lang=2&reg=48), [leakage safeguards](https://scikit-learn.org/stable/common_pitfalls.html), [paired resampling](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html).
'''
    (out/'RESULTS.md').write_text(text,encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input-dir',type=Path,default=DEFAULT);ap.add_argument('--output-dir',type=Path,required=True);args=ap.parse_args()
    source=args.input_dir.resolve();out=args.output_dir.resolve()
    if out==source or source in out.parents or out==ROOT or out in source.parents:raise ValueError('Output must not replace or nest inside the locked input release')
    if out.exists() and any(out.iterdir()):raise ValueError('Use a new empty output directory')
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'));verified={}
    for row in manifest['inputs']:
        p=ROOT/'Dataset'/row['source_file'];assert sha(p)==row['sha256'],p;verified[p.relative_to(ROOT).as_posix()]=sha(p)
    for name,h in manifest['csv_sha256'].items():
        p=source/name
        if not p.exists():p=source/(name+'.csv')
        assert sha(p)==h,p;verified[p.relative_to(ROOT).as_posix()]=h
    for name,h in manifest['code_sha256'].items():
        p=ROOT/name;assert sha(p)==h,p;verified[p.relative_to(ROOT).as_posix()]=h
    out.mkdir(parents=True,exist_ok=True)
    print('Verified 18 raw inputs and 19 prepared CSVs.',flush=True)
    cols=['work_id','cohort','sanction_date','state','activity_type','sanction_amount_paise','description_normalized','in_sanctioned']+SHARED+['high_cost_peer_flag','high_similarity_review_flag']
    works=pd.read_csv(source/'Work_Features.csv',usecols=cols,dtype={'work_id':'str'})
    for flag in SHARED+['high_cost_peer_flag','high_similarity_review_flag','in_sanctioned']:
        assert works[flag].dtype==bool and works[flag].notna().all(),flag
    assert len(works)==160701 and works.work_id.is_unique and works.work_id.notna().all()
    pairs=pd.read_csv(source/'Duplicate_Candidates.csv');assert pairs.work_id_a.isin(works.work_id).all() and pairs.work_id_b.isin(works.work_id).all()
    assert pairs.high_similarity_review.dtype==bool and pairs.high_similarity_review.notna().all()
    real=real_comparison(works,pairs,out)
    works['sanction_date']=pd.to_datetime(works.sanction_date)
    reference=works.loc[works.in_sanctioned.astype(bool)&works.sanction_date.le('2025-03-31')&works.sanction_amount_paise.notna()].sort_values('work_id').copy()
    write_csv(out,'Reference_Membership',reference[['work_id','sanction_date']]);peers=FrozenPeers(reference)
    cases,labels,contexts=generate(peers)
    assert labels.case_id.is_unique and labels.groupby('context_id').size().eq(18).all()
    assert len(set(labels.loc[labels.split.eq('test'),'context_id'])&set(labels.loc[labels.split.eq('development'),'context_id']))==0
    primitives=pd.DataFrame([{**c,'payments':json.dumps(c['payments'],sort_keys=True)} for c in cases])
    write_csv(out,'Synthetic_Primitives',primitives);write_csv(out,'Synthetic_Oracle',labels);write_csv(out,'Synthetic_Contexts',contexts)
    print(f'Frozen reference {len(reference):,}; generated {len(cases):,} primitive cases. Scoring without labels.',flush=True)
    scores=combine(pd.DataFrame([primitive_features(c,peers) for c in cases]))
    write_csv(out,'Development_Scores',scores.loc[scores.split.eq('development')])
    scored=scores.merge(labels.drop(columns=['context_id','split']),on='case_id',validate='one_to_one')
    controlled=controlled_metrics(scored,out)
    metrics=dict(version='all-cohort-ab-v1',seed=SEED,as_of='2026-09-10',real=real,controlled=controlled,reference_count=len(reference),real_accuracy=None,real_accuracy_reason='No adjudicated labels; retrospective queue comparison only')
    save_json(out/'metrics.json',metrics);report(out,real,controlled,len(reference))
    for p,h in verified.items():assert sha(ROOT/p)==h,p
    code_files=['PROTOCOL.md','methods.py','benchmark.py','run_ab.py','tests.py','verify_repro.py']
    code={f:sha(HERE/f) for f in code_files}
    artifacts={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}
    save_json(out/'manifest.json',dict(version='all-cohort-ab-v1',source_manifest_sha256=sha(source/'manifest.json'),verified_input_sha256=verified,code_sha256=code,output_sha256=artifacts,python=platform.python_version(),pandas=pd.__version__,numpy=np.__version__,source_unchanged=True))
    print(json.dumps({x['arm']:{k:x[k] for k in ['true_positive','false_positive','recovery','controlled_yield']} for x in controlled['metrics'] if x['budget']==.10},indent=2),flush=True)
    print('Paired 95% interval:',controlled['recovery_difference_95_interval'],flush=True)
    print('Completed:',out,flush=True)

if __name__=='__main__':main()
