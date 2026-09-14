"""Frozen methods shared by real snapshots and primitive synthetic fixtures."""
from collections import Counter
import hashlib
import math
import re
import unicodedata
import numpy as np
import pandas as pd

SEED=26102
AS_OF=pd.Timestamp('2026-09-10')
SHARED=['pending_recommendation_45d_flag','sanction_delay_45d_flag','open_over_one_year_flag','no_success_three_months_flag','open_after_demission_18m_flag','paid_over_sanction_flag','completion_over_sanction_flag','repeat_payment_report_flag']
STOP=set('a an the of for and at in to with from by near construction installation purchase providing work works supply development village gram panchayat ward no number district block under proposed new existing'.split())
PHASE=re.compile(r'\b(?:phase|continued|continue|continuation|extension|part|repair|renovation)\b')

def normalize(x):
    text=unicodedata.normalize('NFKC',str(x)).casefold().replace('_',' ')
    return ' '.join(re.sub(r'[^\w\s]',' ',text).split())

def tie_values(keys,seed=SEED):
    return np.array([int(hashlib.sha256(f'{seed}:{x}'.encode()).hexdigest()[:16],16) for x in keys],dtype=np.uint64)

def rank(scores,tie):return np.lexsort((tie,-np.asarray(scores,dtype=float)))

def combine(frame):
    result=frame.copy()
    base=result[SHARED].astype(int).sum(axis=1)
    result['score_a']=base+result.exact_duplicate.astype(int)
    result['score_b']=base+result.near_duplicate.astype(int)+result.high_cost_peer_flag.astype(int)
    assert (result.near_duplicate>=result.exact_duplicate).all()
    assert (result.score_b>=result.score_a).all()
    return result

class FrozenPeers:
    def __init__(self,reference):
        assert reference.sanction_date.max()<=pd.Timestamp('2025-03-31')
        self.stats={};self.n=len(reference)
        for level,cols in [('state_activity',['state','activity_type']),('activity',['activity_type'])]:
            for key,group in reference.groupby(cols,sort=True):
                if len(group)<20:continue
                if not isinstance(key,tuple):key=(key,)
                x=np.log1p(group.sanction_amount_paise.to_numpy(float)/100)
                med=float(np.median(x));scale=max(float(1.4826*np.median(np.abs(x-med))),.1)
                self.stats[(level,*key)]=(len(group),float(np.expm1(med)),med,scale)
        self.frequencies=Counter(t for s in reference.description_normalized.fillna('') for t in set(s.split())-STOP)
    def peer(self,state,activity):
        return self.stats.get(('state_activity',state,activity),self.stats.get(('activity',activity)))
    def cost(self,amount,state,activity):
        stat=self.peer(state,activity)
        if stat is None or amount is None:return False,None,None
        _,median,logmed,scale=stat
        ratio=(amount/100)/median if median>0 else None
        z=(math.log1p(amount/100)-logmed)/scale
        return bool(ratio is not None and ratio>=2 and z>3.5),z,ratio
    def pair(self,left,right,amount,ref_amount):
        a,b=normalize(left),normalize(right);at=set(a.split())-STOP;bt=set(b.split())-STOP
        weight=lambda t:math.log1p(self.n/(1+self.frequencies.get(t,0)))
        union=at|bt
        similarity=sum(weight(t) for t in sorted(at&bt))/sum(weight(t) for t in sorted(union)) if union else 0
        if a and a==b:similarity=1.0
        na=set(re.findall(r'\b\d+\b',a));nb=set(re.findall(r'\b\d+\b',b))
        eligible=(amount is not None and ref_amount is not None and amount==ref_amount and min(len(at),len(bt))>=4 and not(bool(na and nb and na!=nb) or PHASE.search(a) or PHASE.search(b)))
        return bool(eligible and a==b and a),bool(eligible and similarity>=.96),float(similarity)

def primitive_features(case,peers):
    # Explicit allowlist: family/labels/oracle evidence can never enter scoring.
    allowed={'case_id','context_id','split','cohort','state','activity_type','recommended_date','sanction_date','completion_date','term_end_date','sanction_paise','completion_paise','description','reference_description','reference_amount_paise','payments'}
    if set(case)!=allowed:raise ValueError('Unexpected or missing detector input fields')
    date=lambda key:pd.Timestamp(case[key]) if case[key] else None
    rec,san,comp,term=[date(k) for k in ['recommended_date','sanction_date','completion_date','term_end_date']]
    amount=case['sanction_paise'];successful=[p for p in case['payments'] if p['status']=='Payment Success']
    assert all(p['status'] in ['Payment Success','Payment In-Progress'] for p in case['payments'])
    assert all(p['amount_paise']>=0 for p in case['payments'])
    paid=sum(p['amount_paise'] for p in successful)
    fingerprints=[(p['vendor_id'],p['date'],p['amount_paise'],p['status']) for p in case['payments']]
    flags={
      SHARED[0]:san is None and rec is not None and (AS_OF-rec).days>45,
      SHARED[1]:san is not None and rec is not None and (san-rec).days>45,
      SHARED[2]:san is not None and comp is None and san+pd.DateOffset(years=1)<AS_OF,
      SHARED[3]:san is not None and not successful and san+pd.DateOffset(months=3)<AS_OF,
      SHARED[4]:san is not None and comp is None and term is not None and term+pd.DateOffset(months=18)<AS_OF,
      SHARED[5]:amount is not None and bool(successful) and paid-amount>100,
      SHARED[6]:amount is not None and case['completion_paise'] is not None and case['completion_paise']-amount>100,
      SHARED[7]:len(fingerprints)>len(set(fingerprints)),
    }
    cost,z,ratio=peers.cost(amount,case['state'],case['activity_type'])
    exact,near,sim=peers.pair(case['description'],case['reference_description'],amount,case['reference_amount_paise'])
    return dict(case_id=case['case_id'],context_id=case['context_id'],split=case['split'],cohort=case['cohort'],**flags,exact_duplicate=exact,near_duplicate=near,high_cost_peer_flag=cost,cost_z=z,cost_ratio=ratio,pair_similarity=sim,successful_paise=paid)
