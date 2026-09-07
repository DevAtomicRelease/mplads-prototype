"""Meaningful regression checks for provenance, time leakage and numeric edge cases."""
import unittest
import json
from pathlib import Path
import numpy as np
import pandas as pd
from build_features import mp_key, fiscal_year, prior_history, peer_features, duplicate_features, isolation_scores, json_safe, norm_text


class PipelineTests(unittest.TestCase):
    def test_normalized_mp_honorifics_and_punctuation(self):
        self.assertEqual(mp_key("Shri Example Person"), mp_key("EXAMPLE PERSON"))
        self.assertEqual(mp_key("Dr. Name A-B"), "nameab")
        self.assertEqual(mp_key("Shrikant Name"), "shrikantname")

    def test_fiscal_year_boundary(self):
        self.assertEqual(fiscal_year(pd.Timestamp("2025-03-31")), "2024-2025")
        self.assertEqual(fiscal_year(pd.Timestamp("2025-04-01")), "2025-2026")
        self.assertIsNone(fiscal_year(pd.NaT))

    def test_same_day_exclusion_and_ninety_day_boundary(self):
        frame = pd.DataFrame({"mp_name_key": ["a"] * 5, "work_id": [1, 2, 3, 4, 5],
            "sanction_date": pd.to_datetime(["2025-01-01", "2025-01-01", "2025-04-01", "2025-04-02", "2025-04-02"]),
            "sanction_amount": [10., 20., 30., 40., 50.]})
        got = prior_history(frame, "mp_name_key", "mp")
        self.assertEqual(got.mp_prior_work_count.tolist(), [0, 0, 2, 3, 3])
        self.assertEqual(got.mp_prior_sanction_total.tolist(), [0, 0, 30, 60, 60])
        self.assertEqual(got.mp_prior90d_work_count.tolist(), [0, 0, 2, 1, 1])
        self.assertTrue(got.mp_previous_sanction_date.iloc[:2].isna().all())

    def test_missing_historical_amount_does_not_become_zero(self):
        frame = pd.DataFrame({"mp_name_key": ["a"] * 3, "work_id": [1, 2, 3],
            "sanction_date": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
            "sanction_amount": [np.nan, 20., 30.]})
        got = prior_history(frame, "mp_name_key", "mp")
        self.assertEqual(got.mp_prior_sanction_total.iloc[0], 0)
        self.assertTrue(got.mp_prior_sanction_total.iloc[1:].isna().all())

    def test_degenerate_peer_scale_and_leave_one_out(self):
        frame = pd.DataFrame({"state": ["A"] * 12, "work_type": ["School"] * 12,
            "sanction_amount": [100.] * 11 + [10000.]})
        got = peer_features(frame)
        self.assertEqual(got.peer_count.iloc[-1], 11)
        self.assertEqual(got.peer_median_amount.iloc[-1], 100)
        self.assertEqual(got.peer_scale_method.iloc[-1], "10% median floor (degenerate peers)")
        self.assertTrue(got.high_cost_outlier_flag.iloc[-1])
        self.assertFalse(got.high_cost_outlier_flag.iloc[0])

    def test_isolation_forest_determinism_and_extreme_recovery(self):
        rng = np.random.default_rng(30)
        x = np.vstack([rng.normal(size=(400, 2)), [[30, 30]]])
        a = isolation_scores(x, seed=55, tree_count=50)
        b = isolation_scores(x, seed=55, tree_count=50)
        self.assertTrue(np.array_equal(a, b))
        self.assertEqual(int(np.argmax(a)), 400)
        self.assertTrue(((a > 0) & (a <= 1)).all())
        self.assertTrue(np.allclose(isolation_scores(np.ones((20, 2)), tree_count=5), .5))

    def test_duplicate_corroboration_and_continuation_safeguard(self):
        text = "Construction science laboratory chemistry equipment room adjacent western library building ward 12"
        frame = pd.DataFrame({"work_id": [1, 2, 3], "state": ["A"] * 3,
            "work_description": [text, text, text + " continued phase"],
            "description_normalized": [norm_text(text), norm_text(text), norm_text(text + " continued phase")],
            "ida_key": ["a|authority"] * 3, "mp_name_key": ["m"] * 3,
            "sanction_amount": [100000.] * 3, "sanction_date": pd.to_datetime(["2025-01-01"] * 3),
            "description_continuation_flag": [False, False, True]})
        got, pairs, audit = duplicate_features(frame)
        exact = pairs[(pairs.work_id_a == 1) & (pairs.work_id_b == 2)].iloc[0]
        self.assertEqual(exact.evidence_strength, "Strong")
        self.assertEqual(exact.similarity, 1)
        self.assertFalse(pairs.work_id_a.eq(pairs.work_id_b).any())
        self.assertFalse(pairs.loc[pairs.continuation_or_phase_flag, "evidence_strength"].eq("Strong").any())
        self.assertEqual(len(pairs), audit["candidate_pairs"])

    def test_json_missing_and_date_serialization(self):
        self.assertEqual(json_safe({"a": np.nan, "b": pd.NaT, "c": pd.Timestamp("2025-01-01")}),
            {"a": None, "b": None, "c": "2025-01-01"})

    def test_saved_audit_and_conservation(self):
        path = Path(__file__).parent / "artifacts" / "audit.json"
        if not path.exists():
            self.skipTest("Run build_features.py first")
        audit = json.loads(path.read_text("utf-8"))
        self.assertTrue(all(audit["checks"].values()))
        self.assertEqual(audit["source_reconciliation"]["works"]["records"], 10000)
        self.assertEqual(audit["source_reconciliation"]["allocations"]["records"], 543)
        self.assertEqual(audit["source_reconciliation"]["consents"]["records"], 12)
        self.assertEqual(audit["data_quality"]["allocation_amount_missing"], 1)
        self.assertLess(audit["visible_works_value_fraction"], .13)


if __name__ == "__main__":
    unittest.main(verbosity=2)
