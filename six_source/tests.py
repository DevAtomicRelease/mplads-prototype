"""Fast invariant tests for the six_source build, NL query engine and A/B metrics.

Reads the outputs already in local/ (run build.py, then validate.py first). Uses only
the standard library plus the project's own modules -- no pytest. Run:

    python tests.py                 # all suites against local/
    python -m unittest tests -v

The heavy end-to-end reproducibility check (rebuild + hash compare) is opt-in:

    python tests.py --rebuild
"""
from __future__ import annotations

import json
import sqlite3
import sys
import unittest
from pathlib import Path

import nlq

HERE = Path(__file__).parent
LOCAL = HERE / "local"


def db():
    c = sqlite3.connect((LOCAL / "mplads.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (LOCAL / "audit.json").is_file():
            raise unittest.SkipTest("Run build.py first (local/audit.json missing)")
        cls.meta = json.loads((LOCAL / "audit.json").read_text(encoding="utf-8"))
        cls.db = db()

    def test_all_reconciliation_checks_pass(self):
        self.assertTrue(self.meta["all_checks_passed"])
        failed = [k for k, v in self.meta["checks"].items() if not v]
        self.assertEqual(failed, [], f"failed checks: {failed}")

    def test_one_row_per_work_and_keys_namespaced(self):
        n, distinct = self.db.execute("SELECT COUNT(*), COUNT(DISTINCT work_id) FROM Work_Features").fetchone()
        self.assertEqual(n, distinct)
        self.assertEqual(n, self.meta["totals"]["works"])
        bad = self.db.execute("SELECT COUNT(*) FROM Work_Features WHERE work_id NOT LIKE '%:%:%'").fetchone()[0]
        self.assertEqual(bad, 0, "every work_id must be cohort:mpkey:id")

    def test_score_equals_sum_of_contributions(self):
        rows = self.db.execute(
            "SELECT w.work_id, w.priority_score, COALESCE(SUM(r.points),0) s "
            "FROM Work_Features w LEFT JOIN Rule_Contributions r ON r.work_id=w.work_id "
            "GROUP BY w.work_id HAVING w.priority_score <> MIN(w.priority_score, s) OR w.priority_score <> MIN(100, s)"
        ).fetchall()
        self.assertEqual(rows, [], "priority_score must equal min(100, sum of contribution points)")

    def test_bands_match_score_thresholds(self):
        q = ("SELECT COUNT(*) FROM Work_Features WHERE "
             "(priority_score=0 AND priority_band!='Routine') OR "
             "(priority_score BETWEEN 1 AND 19 AND priority_band!='Low') OR "
             "(priority_score BETWEEN 20 AND 39 AND priority_band!='Medium') OR "
             "(priority_score BETWEEN 40 AND 80 AND priority_band!='High') OR "
             "(priority_score BETWEEN 81 AND 100 AND priority_band!='Critical')")
        self.assertEqual(self.db.execute(q).fetchone()[0], 0)

    def test_money_never_exceeds_cap_illogically(self):
        # No settled payment or completion amount above sanction is a legitimate zero here.
        self.assertEqual(self.meta["rule_counts"]["paid_over_sanction_flag"],
                         self.db.execute("SELECT SUM(paid_over_sanction_flag) FROM Work_Features").fetchone()[0])

    def test_unsupervised_signals_are_separate_and_consistent(self):
        # DBSCAN outlier flag is exactly the -1 (noise) cluster label.
        mismatch = self.db.execute("SELECT COUNT(*) FROM Work_Features WHERE (dbscan_cluster=-1) <> (dbscan_outlier_flag=1)").fetchone()[0]
        self.assertEqual(mismatch, 0)
        self.assertTrue(self.db.execute("SELECT MIN(isolation_percentile)>=0 AND MAX(isolation_percentile)<=100 FROM Work_Features").fetchone()[0])

    def test_march_rush_requires_successful_payment(self):
        bad = self.db.execute("SELECT COUNT(*) FROM Work_Features WHERE march_rush_flag=1 AND has_successful_payment_evidence=0").fetchone()[0]
        self.assertEqual(bad, 0)

    def test_completed_are_subset_of_sanctioned(self):
        bad = self.db.execute("SELECT COUNT(*) FROM Work_Features WHERE in_completed=1 AND in_sanctioned=0").fetchone()[0]
        self.assertEqual(bad, 0)


class NLQuery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (LOCAL / "mplads.sqlite3").is_file():
            raise unittest.SkipTest("Run build.py first")
        cls.db = db()

    def test_injection_is_inert(self):
        # Malicious text must not execute; it is parsed to an allow-listed aggregate.
        before = self.db.execute("SELECT COUNT(*) FROM Work_Features").fetchone()[0]
        r = nlq.answer(self.db, "'; DROP TABLE Work_Features;-- most high works")
        self.assertIn("sql", r)
        self.assertTrue(r["sql"].lstrip().upper().startswith("SELECT"))
        after = self.db.execute("SELECT COUNT(*) FROM Work_Features").fetchone()[0]
        self.assertEqual(before, after)

    def test_known_ranking_query(self):
        r = nlq.answer(self.db, "Which states have the most high-priority works?")
        self.assertIn("state", r["interpretation"].lower())
        self.assertGreater(r["row_count"], 0)
        self.assertTrue(all(c["key"] for c in r["columns"]))

    def test_aggregate_query_single_row(self):
        r = nlq.answer(self.db, "How many works are open beyond one year in Uttar Pradesh?")
        self.assertEqual(r["row_count"], 1)

    def test_deterministic(self):
        q = "Top 5 district authorities by works open beyond one year"
        self.assertEqual(nlq.answer(self.db, q)["sql"], nlq.answer(self.db, q)["sql"])


class Validation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = LOCAL / "ab_metrics.json"
        if not p.is_file():
            raise unittest.SkipTest("Run validate.py first")
        cls.m = json.loads(p.read_text(encoding="utf-8"))

    def test_budgets_and_shape(self):
        self.assertTrue(self.m["budgets"])
        for b in self.m["budgets"]:
            self.assertEqual(len(b["ci95"]), 2)
            self.assertEqual(len(b["scenarios"]), 9)
            self.assertGreaterEqual(b["b_recovery"], b["a_recovery"] - 1e-9,
                                    "enhanced B should not recover less than baseline A")
            self.assertAlmostEqual(b["difference"], b["b_recovery"] - b["a_recovery"], places=6)

    def test_enhancement_recovers_b_only_families(self):
        b10 = next(b for b in self.m["budgets"] if abs(b["fraction"] - 0.10) < 1e-9)
        bonly = [s for s in b10["scenarios"] if "B only" in s["scenario"]]
        self.assertEqual(len(bonly), 2)
        for s in bonly:
            self.assertGreater(s["b_selected"], s["a_selected"])


class FailureHandling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (LOCAL / "audit.json").is_file():
            raise unittest.SkipTest("Run build.py first")
        cls.meta = json.loads((LOCAL / "audit.json").read_text(encoding="utf-8"))

    def test_unknown_cohort_fails_closed(self):
        import build
        from common import ROOT
        with self.assertRaises(ValueError):
            build.load_sources(ROOT / "Dataset", ["not_a_cohort"])

    def test_stale_build_detected(self):
        import serve
        self.assertEqual(serve.stale_reason(self.meta), "", "current build should be fresh")
        tampered = json.loads(json.dumps(self.meta))
        tampered["sources"][0]["sha256"] = "0" * 64
        self.assertTrue(serve.stale_reason(tampered), "a changed source hash must be reported stale")

    def test_missing_source_detected(self):
        import serve
        tampered = json.loads(json.dumps(self.meta))
        tampered["sources"] = [{"file": "Nowhere/missing.csv", "sha256": "0" * 64}]
        self.assertIn("missing", serve.stale_reason(tampered))


class EndToEnd(unittest.TestCase):
    """Demo smoke test: start the loopback server and exercise the key endpoints."""
    @classmethod
    def setUpClass(cls):
        if not (LOCAL / "mplads.sqlite3").is_file():
            raise unittest.SkipTest("Run build.py first")
        import threading, serve
        cls.server = serve.make_server(port=0, verify=False)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()

    def _get(self, path):
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=10) as r:
            return r.status, json.loads(r.read())

    def test_endpoints(self):
        import urllib.parse
        s, health = self._get("/api/health"); self.assertEqual(s, 200); self.assertTrue(health["localOnly"])
        s, works = self._get("/api/works?limit=1"); self.assertEqual(s, 200); self.assertGreater(works["summary"]["total"], 0)
        s, ov = self._get("/api/overview"); self.assertEqual(s, 200); self.assertGreater(ov["national"]["works"], 0)
        s, ask = self._get("/api/ask?q=" + urllib.parse.quote("which states have the most high-priority works")); self.assertEqual(s, 200); self.assertGreater(ask["row_count"], 0)
        s, val = self._get("/api/validation"); self.assertEqual(s, 200); self.assertTrue(val["budgets"])


def _reproducibility():
    import tempfile, subprocess
    from common import sha
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([sys.executable, str(HERE / "build.py"), "--output-dir", d], check=True, cwd=HERE)
        a = sha(Path(d) / "Work_Features.csv")
    b = sha(LOCAL / "Work_Features.csv")
    print("reproducible:", a == b, "\n  fresh:", a, "\n  local:", b)
    assert a == b, "independent rebuild produced a different Work_Features.csv"


if __name__ == "__main__":
    if "--rebuild" in sys.argv:
        _reproducibility()
    else:
        unittest.main(verbosity=2)
