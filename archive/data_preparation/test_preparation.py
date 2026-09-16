"""Boundary tests for identifiers, paise, calendars and feature null semantics."""
import unittest
from decimal import Decimal
import pandas as pd
from prepare import work_keys,term_key,clean_allocation,stable_hash,legacy
from common import money,ratio,fy,norm

class PreparationTests(unittest.TestCase):
    def test_colliding_numeric_work_ids_are_separated(self):
        d=pd.DataFrame({'WORK_RECOMMENDATION_DTL_ID':['1437','1437'],'FLAG':['1','2'],'ACTIVITY_NAME':['WS/MP1/2024-2025/1437-Example','NA-Other'],'cohort':['Rajya_Sabha_retired','Lok Sabha']})
        self.assertEqual(work_keys(d,'recommended').tolist(),['work:1437','rec2:LS:1437'])

    def test_completed_secondary_id_is_not_primary(self):
        d=pd.DataFrame({'WORK_RECOMMENDATION_DTL_ID':['123'],'WORK_ID':['999']})
        self.assertEqual(work_keys(d,'completed').iloc[0],'work:123')

    def test_new_flag_fails_closed(self):
        d=pd.DataFrame({'WORK_RECOMMENDATION_DTL_ID':['2'],'FLAG':['9'],'ACTIVITY_NAME':['NA-a'],'cohort':['Lok Sabha']})
        with self.assertRaises(ValueError):work_keys(d,'recommended')

    def test_unreviewed_flag2_prefix_fails(self):
        d=pd.DataFrame({'WORK_RECOMMENDATION_DTL_ID':['2'],'FLAG':['2'],'ACTIVITY_NAME':['WS/a'],'cohort':['Lok Sabha']})
        with self.assertRaises(ValueError):work_keys(d,'recommended')

    def test_mp_terms_not_merged(self):
        d=pd.DataFrame({'HOUSE_OF_PARLIAMENT':['1','1'],'MP_NAME':['Shri Example','Shri Example'],'TENURE_START_DATE':['2018','2024'],'TENURE_END_DATE':['2024','2030']})
        self.assertNotEqual(*term_key(d).tolist())

    def test_honorific_only_does_not_break_same_term(self):
        d=pd.DataFrame({'HOUSE_OF_PARLIAMENT':['2','2'],'MP_NAME':['Shri Example Name','EXAMPLE NAME'],'TENURE_START_DATE':['a','a'],'TENURE_END_DATE':['b','b']})
        self.assertEqual(*term_key(d).tolist())

    def test_tiny_export_residue_is_logged_exactly(self):
        value,delta=clean_allocation('102221195.92999999')
        self.assertEqual(value,10222119593);self.assertEqual(Decimal(delta),Decimal('0.00000001'))

    def test_true_fractional_paise_is_not_rounded(self):
        with self.assertRaises(ValueError):clean_allocation('1.001')

    def test_large_integer_paise_stays_exact(self):
        self.assertEqual(int(money(pd.Series(['99996500.01'])).iloc[0]),9999650001)

    def test_zero_and_missing_distinguished(self):
        x=money(pd.Series(['0','','NA','1.05']))
        self.assertEqual(x.iloc[0],0);self.assertTrue(pd.isna(x.iloc[1]));self.assertTrue(pd.isna(x.iloc[2]));self.assertEqual(x.iloc[3],105)

    def test_ratio_does_not_impute_unknown_or_zero_denominator(self):
        x=ratio(pd.Series([0,1,None]),pd.Series([2,0,1]))
        self.assertEqual(x.iloc[0],0);self.assertTrue(pd.isna(x.iloc[1]));self.assertTrue(pd.isna(x.iloc[2]))

    def test_fiscal_year_boundary(self):
        self.assertEqual(fy(pd.Series(pd.to_datetime(['2026-03-31','2026-04-01']))).tolist(),['2025-2026','2026-2027'])

    def test_calendar_month_not_fixed_90_days(self):
        self.assertEqual(pd.Timestamp('2025-11-30')+pd.DateOffset(months=3),pd.Timestamp('2026-02-28'))

    def test_leap_year_anniversary(self):
        self.assertEqual(pd.Timestamp('2024-02-29')+pd.DateOffset(years=1),pd.Timestamp('2025-02-28'))

    def test_fingerprint_stable_and_not_delimiter_ambiguous(self):
        self.assertEqual(stable_hash(['a','b']),stable_hash(['a','b']))
        self.assertNotEqual(stable_hash(['a|b','c']),stable_hash(['a','b|c']))

    def test_prior_year_benchmark_excludes_same_year(self):
        rows=[dict(sanction_amount_paise=10000,in_sanctioned=True,sanction_fy='2024-2025',state='X',activity_type='Road') for _ in range(20)]
        rows.append(dict(sanction_amount_paise=10000000,in_sanctioned=True,sanction_fy='2025-2026',state='X',activity_type='Road'))
        w=legacy.cost_features(pd.DataFrame(rows))
        self.assertEqual(w.peer_count.iloc[-1],20)
        self.assertAlmostEqual(w.peer_median_inr.iloc[-1],100)
        self.assertTrue(w.cost_peer_log_z.iloc[:-1].isna().all())

    def test_unicode_text_normalization_preserves_words(self):
        self.assertEqual(norm('  ROAD,  School! '),'road school')

if __name__=='__main__':unittest.main(verbosity=2)
