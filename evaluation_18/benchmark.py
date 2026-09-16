"""Synthetic primitives and a separate oracle. No real work is labelled clean."""
import copy
import hashlib
import numpy as np
import pandas as pd
from methods import AS_OF,SEED

FAMILIES=[
 ('late_sanction',1,'observable'),('stalled_open',1,'observable'),('no_success',1,'observable'),
 ('overpayment',1,'observable'),('completion_overrun',1,'observable'),('retired_backlog',1,'observable'),
 ('repeated_payment',1,'information_limited'),('inflated_cost',1,'information_limited'),('near_duplicate',1,'information_limited'),
 ('routine',0,'observable'),('pending_not_spent',0,'observable'),('approved_extension',0,'information_limited'),
 ('large_legitimate_scope',0,'information_limited'),('distinct_phase',0,'observable'),('distinct_location',0,'observable'),
 ('export_repeat_artifact',0,'information_limited'),('small_rounding',0,'observable'),('identical_visible_distinct_assets',0,'information_limited'),
]

def generate(peers):
    keys=sorted(k for k in peers.stats if k[0]=='state_activity' and peers.stats[k][1]>0)
    cases=[];labels=[];contexts=[]
    for split,n,seed in [('development',100,SEED+101),('test',400,SEED+202)]:
        rng=np.random.default_rng(seed)
        for i in range(n):
            context=hashlib.sha256(f'{split}:{i}:{SEED}'.encode()).hexdigest()[:24]
            _,state,activity=keys[int(rng.integers(len(keys)))];stat=peers.peer(state,activity)
            amount=max(10000,int(round(stat[1]*100*float(rng.uniform(.85,1.15)))))
            cohort=['Lok Sabha','Rajya_Sabha_retired','Rajya_Sabha_sitting'][i%3]
            site=int(rng.integers(10000,99999))
            description=f'Public learning facility building at site {site} with reinforced roof accessible ramp toilet water storage seating windows electrical fittings drainage boundary gate paved entrance library room ventilation and secure equipment storage for local residents'
            date=lambda days:(AS_OF-pd.Timedelta(days=int(days))).date().isoformat()
            base=dict(context_id=context,split=split,cohort=cohort,state=state,activity_type=activity,recommended_date=date(80),sanction_date=date(60),completion_date=None,term_end_date='2029-06-03',sanction_paise=amount,completion_paise=None,description=description,reference_description='Unrelated public water supply pump reservoir',reference_amount_paise=amount+12345,payments=[dict(vendor_id='synthetic-vendor',date=date(30),amount_paise=int(.4*amount),status='Payment Success')])
            if cohort=='Rajya_Sabha_retired':base['term_end_date']='2026-08-15'
            contexts.append(dict(context_id=context,split=split,state=state,activity_type=activity,reference_peer_n=stat[0],reference_median_inr=stat[1],cohort=cohort))
            # Random ID assignment is independent of family ordering and label.
            ids=rng.choice(1000000,size=len(FAMILIES),replace=False)
            for j,(family,label,observability) in enumerate(FAMILIES):
                c=copy.deepcopy(base);c['case_id']='synthetic:'+hashlib.sha256(f'{context}:{int(ids[j])}'.encode()).hexdigest()[:24]
                explanation='Constructed normal context with no anomalous event.'
                if family=='late_sanction':
                    delay=int(rng.choice([60,140,400]));c['recommended_date']=(pd.Timestamp(c['sanction_date'])-pd.Timedelta(days=delay)).date().isoformat();explanation='Synthetic receipt equals recommendation; decision is late without an exception.'
                elif family in ['stalled_open','approved_extension']:
                    age=int(rng.integers(400,500));c['sanction_date']=date(age);c['recommended_date']=date(age+20)
                    explanation='No approved extension; synthetic work remains incomplete.' if label else 'Oracle has an approved completion extension; that document is absent from detector inputs.'
                elif family=='no_success':
                    age=int(rng.integers(120,300));c['sanction_date']=date(age);c['recommended_date']=date(age+20);c['payments'][0]['status']='Payment In-Progress';explanation='Oracle confirms no released payment despite continued sanctioned work.'
                elif family=='overpayment':
                    c['payments'][0]['amount_paise']=int(amount*float(rng.uniform(1.1,1.5)));explanation='Oracle confirms payments above unchanged approved sanction.'
                elif family=='completion_overrun':
                    c['completion_date']=date(10);c['completion_paise']=int(amount*float(rng.uniform(1.1,1.5)));explanation='Oracle confirms reported final cost above approved sanction without revision.'
                elif family=='retired_backlog':
                    c['term_end_date']='2025-01-01';c['recommended_date']='2024-12-01';c['sanction_date']='2025-05-01';explanation='Oracle confirms demission on reported term end and unresolved sanctioned backlog beyond 18 months.'
                elif family in ['repeated_payment','export_repeat_artifact']:
                    c['payments'].append(copy.deepcopy(c['payments'][0]));explanation='Oracle bank evidence confirms two charges for one invoice.' if label else 'Oracle bank evidence confirms one charge exported twice; bank IDs are unavailable to the detector.'
                elif family in ['inflated_cost','large_legitimate_scope']:
                    factor=float(rng.choice([1.5,2.5,8]));c['sanction_paise']=int(amount*factor);c['payments'][0]['amount_paise']=int(.4*c['sanction_paise']);explanation=f'Oracle confirms same quantities with unjustified {factor}x inflated estimate.' if label else f'Oracle confirms {factor}x legitimate physical scope; quantities are unavailable to the detector.'
                elif family=='near_duplicate':
                    c['reference_description']=description;c['reference_amount_paise']=amount
                    variant=int(rng.integers(3))
                    c['description']=[' '.join(reversed(description.split())),description+' near',description.replace('ventilation','ventiltion')][variant]
                    explanation='Oracle confirms the same asset/scope submitted twice; wording differs.'
                elif family=='pending_not_spent':
                    c['payments'].append(dict(vendor_id='synthetic-vendor',date=date(5),amount_paise=int(.8*amount),status='Payment In-Progress'));explanation='Only 40% is settled; an 80% pending request is not additional expenditure.'
                elif family=='distinct_phase':
                    c['reference_description']=description+' phase 1';c['description']=description+' phase 2';c['reference_amount_paise']=amount;explanation='Oracle confirms separately approved physical phases, visible in text.'
                elif family=='distinct_location':
                    c['reference_description']=description;c['description']=description.replace(str(site),str(site+1));c['reference_amount_paise']=amount;explanation='Oracle confirms two different sites, visible in numbered text.'
                elif family=='small_rounding':
                    c['payments'][0]['amount_paise']=amount+int(rng.choice([10,100]));explanation='Small rounding difference of INR0.10/INR1, within the declared investigation tolerance.'
                elif family=='identical_visible_distinct_assets':
                    c['reference_description']=description;c['reference_amount_paise']=amount;explanation='Oracle confirms distinct assets within the same compound with identical visible description/price; asset identifiers are absent.'
                assert pd.Timestamp(c['sanction_date'])>pd.Timestamp('2025-03-31')
                assert pd.Timestamp(c['recommended_date'])<=pd.Timestamp(c['sanction_date'])<=AS_OF
                cases.append(c);labels.append(dict(case_id=c['case_id'],context_id=context,split=split,family=family,synthetic_positive=label,observability=observability,oracle_explanation=explanation))
    return cases,pd.DataFrame(labels),pd.DataFrame(contexts)
