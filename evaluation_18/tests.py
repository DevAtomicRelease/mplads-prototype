"""Known-answer checks independent of the scored synthetic test labels."""
import copy
import unittest
import numpy as np
import pandas as pd
from methods import AS_OF,SHARED,FrozenPeers,primitive_features,combine,tie_values,rank
from run_ab import queue_detail,confusion

def reference(n=20,amount=100000):
    return pd.DataFrame(dict(sanction_date=[pd.Timestamp('2025-03-01')]*n,state=['S']*n,activity_type=['A']*n,sanction_amount_paise=[amount]*n,description_normalized=['community learning building accessible toilet library roof']*n))

def case():
    return dict(case_id='synthetic:test',context_id='context',split='test',cohort='test',state='S',activity_type='A',recommended_date='2026-07-01',sanction_date='2026-07-20',completion_date=None,term_end_date='2029-06-01',sanction_paise=100000,completion_paise=None,description='community learning building accessible toilet library roof site 15',reference_description='different drinking water reservoir pump station site 20',reference_amount_paise=100000,payments=[dict(vendor_id='V',date='2026-08-01',amount_paise=40000,status='Payment Success')])

class TestMethods(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.peers=FrozenPeers(reference())
    def flags(self,c):return primitive_features(c,self.peers)
    def test_routine(self):self.assertFalse(any(self.flags(case())[k] for k in SHARED))
    def test_currency_boundary(self):
        for delta,expect in [(10,False),(100,False),(101,True)]:
            c=case();c['payments'][0]['amount_paise']=100000+delta;c['completion_paise']=100000+delta;f=self.flags(c)
            self.assertEqual(f['paid_over_sanction_flag'],expect);self.assertEqual(f['completion_over_sanction_flag'],expect)
    def test_pending_separate(self):
        c=case();c['payments'].append(dict(vendor_id='V',date='2026-08-02',amount_paise=80000,status='Payment In-Progress'));f=self.flags(c)
        self.assertEqual(f['successful_paise'],40000);self.assertFalse(f['paid_over_sanction_flag'])
    def test_repeat_preserved(self):
        c=case();c['payments'].append(copy.deepcopy(c['payments'][0]));f=self.flags(c);self.assertTrue(f['repeat_payment_report_flag']);self.assertEqual(f['successful_paise'],80000)
    def test_repeat_different_date(self):
        c=case();p=copy.deepcopy(c['payments'][0]);p['date']='2026-08-02';c['payments'].append(p);self.assertFalse(self.flags(c)['repeat_payment_report_flag'])
    def test_pending_recommendation_boundary(self):
        for days,expect in [(45,False),(46,True)]:
            c=case();c['sanction_date']=None;c['recommended_date']=(AS_OF-pd.Timedelta(days=days)).date().isoformat();self.assertEqual(self.flags(c)[SHARED[0]],expect)
    def test_sanction_delay_boundary(self):
        for days,expect in [(45,False),(46,True)]:
            c=case();c['recommended_date']=(pd.Timestamp(c['sanction_date'])-pd.Timedelta(days=days)).date().isoformat();self.assertEqual(self.flags(c)[SHARED[1]],expect)
    def test_missing_dates(self):
        c=case();c.update(recommended_date=None,sanction_date=None,term_end_date=None);f=self.flags(c);self.assertFalse(any(f[k] for k in SHARED[:5]))
    def test_open_calendar_year(self):
        for d,expect in [('2025-09-10',False),('2025-09-09',True)]:
            c=case();c['sanction_date']=d;self.assertEqual(self.flags(c)[SHARED[2]],expect)
    def test_complete_not_open(self):
        c=case();c.update(sanction_date='2025-05-01',completion_date='2026-08-01',term_end_date='2024-01-01');f=self.flags(c);self.assertFalse(f[SHARED[2]]);self.assertFalse(f[SHARED[4]])
    def test_no_success_calendar_months(self):
        for d,expect in [('2026-06-10',False),('2026-06-09',True)]:
            c=case();c['sanction_date']=d;c['payments']=[];self.assertEqual(self.flags(c)[SHARED[3]],expect)
    def test_ended_term_calendar_months(self):
        for d,expect in [('2025-03-10',False),('2025-03-09',True)]:
            c=case();c['term_end_date']=d;self.assertEqual(self.flags(c)[SHARED[4]],expect)
    def test_future_reference_rejected(self):
        r=reference();r.loc[0,'sanction_date']=pd.Timestamp('2025-04-01')
        with self.assertRaises(AssertionError):FrozenPeers(r)
    def test_peer_minimum_and_fallback(self):
        self.assertIsNone(FrozenPeers(reference(19)).peer('S','A'));self.assertIsNotNone(self.peers.peer('OTHER','A'))
    def test_mad_floor(self):self.assertEqual(self.peers.peer('S','A')[3],.1)
    def test_cost_ratio_guard(self):
        self.assertFalse(self.peers.cost(150000,'S','A')[0]);self.assertTrue(self.peers.cost(800000,'S','A')[0])
    def test_unknown_cost_peer(self):self.assertEqual(self.peers.cost(100000,'S','MISSING'),(False,None,None))
    def test_pair_exact_and_reordered(self):
        s=case()['description'];self.assertEqual(self.peers.pair(s,s,100000,100000)[:2],(True,True));self.assertEqual(self.peers.pair(s,' '.join(reversed(s.split())),100000,100000)[:2],(False,True))
    def test_pair_guards(self):
        s=case()['description']
        for t,a,b in [(s+' phase 1',100000,100000),(s.replace('15','16'),100000,100000),(s,100000,100001),(s,None,None),('road road',100000,100000)]:
            self.assertFalse(self.peers.pair(s,t,a,b)[1])
    def test_no_oracle_fields(self):
        c=case();c['synthetic_positive']=1
        with self.assertRaises(ValueError):self.flags(c)
    def test_stable_namespace_ties(self):
        ids=['work:123','rec2:LS:123'];t=tie_values(ids);self.assertNotEqual(t[0],t[1]);np.testing.assert_array_equal(t,tie_values(ids))
    def test_score_monotonicity(self):
        c=case();f=self.flags(c);f.update(exact_duplicate=True,near_duplicate=True,high_cost_peer_flag=True);r=combine(pd.DataFrame([f]));self.assertEqual(int(r.score_b.iloc[0]-r.score_a.iloc[0]),1)
    def test_equal_budget_label_independent_ties(self):
        scores=np.array([0,1,1,1]);ties=tie_values(['a','b','c','d']);r=rank(scores,ties);self.assertEqual(r[-1],0);self.assertEqual(len(r[:2]),2)
    def test_zero_fillers_and_boundary(self):
        f=pd.DataFrame({'score_a':[2,0,0]});d=queue_detail(f,np.array([0,1,2]),'a',2);self.assertEqual(d['zero_score_fillers'],1);self.assertEqual(d['boundary_tie_population'],2)
    def test_known_answer_confusion_at_capacity(self):
        scores=np.array([4,3,2,1]);y=np.array([1,0,1,0]);selected=np.zeros(4,dtype=bool);selected[rank(scores,tie_values(['a','b','c','d']))[:2]]=True
        self.assertEqual(confusion(y,selected),dict(true_positive=1,false_positive=1,false_negative=1,true_negative=1))

if __name__=='__main__':unittest.main(verbosity=2)
