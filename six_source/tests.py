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
import os
from pathlib import Path

import nlq

HERE = Path(__file__).parent
from releases import resolve_active
LOCAL = Path(os.environ["MPLADS_DATA_DIR"]) if "MPLADS_DATA_DIR" in os.environ else resolve_active(HERE/"local")


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


class NLParsing(unittest.TestCase):
    """Each supported question maps to the intended metric / dimension / direction / filter."""
    @classmethod
    def setUpClass(cls):
        if not (LOCAL / "mplads.sqlite3").is_file():
            raise unittest.SkipTest("Run build.py first")
        cls.states = [r[0] for r in db().execute("SELECT DISTINCT state FROM Work_Features")]

    def parse(self, q):
        return nlq.parse(q, self.states)

    def test_pending_not_settled(self):
        i = self.parse("Top states by pending payments")
        self.assertEqual(i["metric"], "pending_paise"); self.assertEqual(i["dimension"], "state"); self.assertEqual(i["direction"], "DESC")

    def test_settled_metric(self):
        self.assertEqual(self.parse("states with the most settled payments")["metric"], "settled_paise")

    def test_overpaid_maps_to_paid_over(self):
        self.assertEqual(self.parse("which states have most overpaid works")["metric"], "paid_over")

    def test_completion_over(self):
        self.assertEqual(self.parse("districts by completion above sanction")["metric"], "completion_over")

    def test_cost_outlier_not_overrun(self):
        # "cost overrun" must NOT be treated as the peer cost-outlier metric
        self.assertFalse(self.parse("cost overruns by district")["metric_found"])
        self.assertEqual(self.parse("which activities have the most cost outliers")["metric"], "cost_outliers")

    def test_direction_and_limit(self):
        i = self.parse("bottom 5 states by settled-to-sanction ratio")
        self.assertEqual(i["metric"], "settled_pct"); self.assertEqual(i["direction"], "ASC"); self.assertEqual(i["limit"], 5)

    def test_state_filter_and_drill(self):
        i = self.parse("which districts in Bihar have the most delays")
        self.assertEqual(i["dimension"], "ida"); self.assertEqual(i["filters"].get("state"), "Bihar"); self.assertEqual(i["metric"], "open_over_year")

    def test_durations_and_years_never_set_row_limit(self):
        # "three months" and "2024-25" are not top-N requests.
        self.assertEqual(self.parse("which MPs have the most works with no payment after three months")["limit"], 10)
        self.assertEqual(self.parse("top states by completed works in 2024-25")["limit"], 10)
        self.assertEqual(self.parse("top five states by march rush")["limit"], 5)
        self.assertEqual(self.parse("10 districts with most delays")["limit"], 10)

    def test_short_fiscal_year_is_applied_and_unknown_year_refused(self):
        i = self.parse("how many works were completed in 2024-25")
        self.assertEqual(i["filters"].get("fy"), "2024-2025"); self.assertIn("sanction_fy = ?", i["clauses"]); self.assertTrue(i["aggregate"])
        r = nlq.answer(db(), "how many works in 2030-31")
        self.assertEqual(r["columns"], []); self.assertIn("not in the connected data", r["summary"])

    def test_national_totals_are_single_numbers(self):
        with db() as conn:
            for q, col in [("total sanctioned amount", "sanction_amount_paise"), ("what is the total amount spent", "successful_payment_paise")]:
                r = nlq.answer(conn, q)
                self.assertEqual(r["row_count"], 1, q)
                self.assertEqual(r["rows"][0][nlq.METRICS[self.parse(q)["metric"]][0]], conn.execute(f"SELECT SUM({col}) FROM Work_Features").fetchone()[0], q)
            self.assertEqual(nlq.answer(conn, "how many duplicate works are there")["row_count"], 1)

    def test_specific_signals_are_not_captured_by_generic_words(self):
        self.assertEqual(self.parse("top states by repeated payment reports")["metric"], "repeat_payments")
        self.assertEqual(self.parse("works with march rush in Bihar")["metric"], "march_rush")
        self.assertEqual(self.parse("which states have the most pending recommendations")["metric"], "pending_rec")
        self.assertEqual(self.parse("top districts by sanction delay")["metric"], "sanction_delay")
        self.assertEqual(self.parse("activities with most completed without payment")["metric"], "completed_no_payment")
        self.assertEqual(self.parse("average sanction amount by state")["metric"], "avg_sanction")
        self.assertTrue(self.parse("average settled payment by state")["averaged"])

    def test_signal_answers_reconcile_to_flags(self):
        with db() as conn:
            r = nlq.answer(conn, "works with march rush in Bihar")
            self.assertEqual(r["rows"][0]["march_rush"], conn.execute("SELECT SUM(march_rush_flag) FROM Work_Features WHERE state='Bihar'").fetchone()[0])
            ranked = nlq.answer(conn, "top states by repeated payment reports")
            self.assertTrue(ranked["rows"]); self.assertTrue(all(row["repeat_payments"] > 0 for row in ranked["rows"]))

    def test_zero_signal_ranking_is_not_a_ranked_list_of_zeros(self):
        with db() as conn:
            if conn.execute("SELECT SUM(completion_over_sanction_flag) FROM Work_Features").fetchone()[0]:
                self.skipTest("signal present in this build")
            r = nlq.answer(conn, "top states by works with completion over sanction")
            self.assertEqual(r["row_count"], 0); self.assertTrue(r["summary"].startswith("None found"))

    def test_mp_label_casing(self):
        r = nlq.answer(db(), "top 3 MPs by sanctioned amount")
        self.assertTrue(r["summary"].startswith("MPs ranked"), r["summary"])

    def test_vendor_filter_refused(self):
        r = nlq.answer(db(), "bottom five vendors by paid amount in Bihar")
        self.assertEqual(r["columns"], []); self.assertIn("cannot be filtered", r["summary"].lower())

    def test_loaded_refused(self):
        r = nlq.answer(db(), "who is the most corrupt MP")
        self.assertEqual(r["columns"], []); self.assertIn("fraud", r["summary"].lower())

    def test_full_authority_question_returns_profile_and_reproducible_totals(self):
        with db() as conn:
            q="JAUNPUR(DISTRICT MAGISTRATE JAUNPUR_IDA), give me details on this."
            result=nlq.answer(conn,q)
            self.assertEqual(result["entity"]["kind"],"ida")
            exact=dict(conn.execute(result["sql"],result["params"]).fetchone())
            self.assertEqual(result["rows"][0]["works"],exact["works"])
            self.assertEqual(exact["works"],2248)

    def test_short_authority_metric_is_filtered_not_national(self):
        with db() as conn:
            r=nlq.answer(conn,"How many high-priority works in Jaunpur?")
            self.assertEqual(r["row_count"],1)
            self.assertIn("ida_key = ?",r["sql"])
            self.assertEqual(r["rows"][0]["high"],283)

    def test_ambiguous_names_require_choice(self):
        from entities import resolve_names
        with sqlite3.connect(":memory:") as conn:
            conn.row_factory=sqlite3.Row
            conn.execute("CREATE TABLE Work_Features(state TEXT)")
            conn.execute("CREATE TABLE IDA_Features(ida_key TEXT, ida_name TEXT)")
            conn.execute("CREATE TABLE MP_Features(mp_key TEXT, mp_name TEXT)")
            conn.execute("CREATE TABLE Vendor_Features(vendor_id TEXT, vendor_name TEXT)")
            conn.executemany("INSERT INTO MP_Features VALUES (?,?)",[("cohort-a:1","Example Member"),("cohort-b:2","Example Member")])
            name="Example Member"
            matches=resolve_names(conn,name)
            self.assertGreater(len(matches),1)
            result=nlq.answer(conn,name+", give me details")
            self.assertNotIn("entity",result)
            self.assertGreater(len(result["matches"]),1)

    def test_named_entity_does_not_bypass_loaded_query_guard(self):
        result=nlq.answer(db(),"Jaunpur fraud details")
        self.assertNotIn("entity",result)
        self.assertEqual(result["columns"],[])

    def test_ranked_entities_have_exact_drilldown_keys(self):
        from entities import profile
        with db() as conn:
            for question,kind in [("Top 3 district authorities by high-priority works","ida"),("Top 3 MPs by sanctioned amount","mp"),("Top 3 vendors by settled payments","vendor")]:
                result=nlq.answer(conn,question)
                self.assertEqual(len(result["rows"]),3)
                for row in result["rows"]:
                    self.assertEqual(row["_entity_kind"],kind)
                    detail=profile(conn,kind,row["_entity_key"])
                    self.assertEqual(detail["name"],row["_dim"])


class MapCoverage(unittest.TestCase):
    def test_local_geometry_matches_all_state_labels(self):
        import re, unicodedata
        def key(name):
            name=unicodedata.normalize("NFD",name).lower().removeprefix("the ").replace("&","and")
            return re.sub("[^a-z]","",name)
        geometry=json.loads((HERE.parent/"mplads-prototype/public/india-adm1-geoboundaries.geojson").read_text(encoding="utf-8"))
        names={key(f["properties"]["shapeName"]) for f in geometry["features"]}
        self.assertEqual(len(names),36)
        self.assertIn("telangana",names);self.assertIn("ladakh",names)
        with db() as conn:
            states={key(r[0]) for r in conn.execute("SELECT DISTINCT state FROM Work_Features")}
        self.assertEqual(states-names,set())
        self.assertTrue(all(f["geometry"]["type"] in ("Polygon","MultiPolygon") and f["geometry"]["coordinates"] for f in geometry["features"]))


class Validation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = LOCAL / "ab_metrics.json"
        if not p.is_file():
            raise unittest.SkipTest("Run validate.py first")
        cls.m = json.loads(p.read_text(encoding="utf-8"))

    def test_budgets_and_shape(self):
        # Shape and internal consistency only. The evaluation is NOT constrained to make
        # the enhanced method win; B is allowed to lose at any budget.
        self.assertTrue(self.m["budgets"])
        for b in self.m["budgets"]:
            self.assertEqual(len(b["ci95"]), 2)
            self.assertEqual(len(b["scenarios"]), 9)
            self.assertAlmostEqual(b["difference"], b["b_recovery"] - b["a_recovery"], places=6)
            for arm in ("a", "b"):
                self.assertEqual(b[f"{arm}_false_alerts"], b[f"{arm}_reviewed"] - round(b[f"{arm}_recovery"] * self.m["synthetic_positives"]))

    def test_enhancement_recovers_b_only_families(self):
        # Definitional (baseline A scores the cost/duplicate families zero, so it can only
        # pick them by tie luck): B must not recover FEWER of them than A. Not a win guarantee.
        b10 = next(b for b in self.m["budgets"] if abs(b["fraction"] - 0.10) < 1e-9)
        bonly = [s for s in b10["scenarios"] if "B only" in s["scenario"]]
        self.assertEqual(len(bonly), 2)
        for s in bonly:
            self.assertGreaterEqual(s["b_selected"], s["a_selected"])


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


class ReleaseSafety(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp=tempfile.TemporaryDirectory(prefix="mplads-release-tests-")
        self.root=Path(self.temp.name);self.local=self.root/"local"

    def tearDown(self):self.temp.cleanup()

    def release(self,marker):
        from releases import new_directory, seal, atomic_json, digest, REQUIRED, HERE
        rel=new_directory(self.local)
        for name in REQUIRED:
            if name!="mplads.sqlite3":(rel/name).write_text(marker,encoding="utf-8")
        with sqlite3.connect(rel/"mplads.sqlite3") as db:
            db.execute("CREATE TABLE Work_Features(work_id TEXT)");db.execute("INSERT INTO Work_Features VALUES ('lok_sabha:member:1')")
        db.close()
        atomic_json(rel/"audit.json",{"version":marker,"source_fingerprint":marker,"as_of":"2026-09-14","all_checks_passed":True,"checks":{"test":True},"sources":[],"pipeline_sha256":digest(HERE/"build.py"),"common_sha256":digest(HERE/"common.py"),"isolation_sha256":digest(HERE/"isolation.py")})
        atomic_json(rel/"artifact_hashes.json",{"Work_Features.csv":digest(rel/"Work_Features.csv")})
        seal(rel)
        return rel

    def test_failed_activation_preserves_old_pointer_and_bytes(self):
        import releases
        from unittest.mock import patch
        old,new=self.release("old"),self.release("new")
        releases.activate(old,self.local);before=(self.local/"active_release.json").read_bytes()
        with patch.object(releases.os,"replace",side_effect=OSError("simulated interruption")):
            with self.assertRaises(OSError):releases.activate(new,self.local)
        self.assertEqual((self.local/"active_release.json").read_bytes(),before)
        self.assertEqual(releases.resolve_active(self.local),old)
        self.assertEqual((old/"Work_Features.csv").read_text(),"old")

    def test_tampering_fails_closed(self):
        import releases
        rel=self.release("before");(rel/"Work_Features.csv").write_text("tampered")
        self.assertIn("Artifact",releases.integrity_reason(rel))
        with self.assertRaises(ValueError):releases.activate(rel,self.local)

    def test_pointer_cannot_escape_release_directory(self):
        from releases import atomic_json,resolve_active
        atomic_json(self.local/"active_release.json",{"dir":"../outside"})
        with self.assertRaises(ValueError):resolve_active(self.local)

    def test_cross_process_lock_is_exclusive_and_released(self):
        from releases import maintenance_lock
        with maintenance_lock(self.local):
            with self.assertRaises(ValueError):
                with maintenance_lock(self.local):pass
        with maintenance_lock(self.local):pass

    def test_all_job_types_are_serialized(self):
        import serve
        from unittest.mock import patch
        saved=dict(serve.JOBS);serve.JOBS.clear()
        try:
            with patch.object(serve.threading,"Thread"):
                serve.start_job("prepare_release",self.local)
                with self.assertRaises(ValueError):serve.start_job("workbook",self.local)
        finally:serve.JOBS.clear();serve.JOBS.update(saved)

    def test_release_switch_review_version_and_history(self):
        import releases,serve,threading,urllib.request,urllib.error
        old,new=self.release("old"),self.release("new");releases.activate(old,self.local)
        server=serve.make_server(port=0,local=self.local,verify=False)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        url=f"http://127.0.0.1:{server.server_port}"
        def get():
            with urllib.request.urlopen(url+"/api/health") as r:return json.loads(r.read())["version"]
        def post(version):
            payload={"key":"lok_sabha:member:1","version":version,"outcome":"Needs evidence","note":"Synthetic regression case","owner":"Test owner","due_date":"2026-10-01","status":"Escalated"}
            req=urllib.request.Request(url+"/api/reviews",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json","Origin":url})
            with urllib.request.urlopen(req) as r:return json.loads(r.read())
        try:
            v1=get();self.assertTrue(post(v1)["saved"])
            releases.activate(new,self.local);v2=get();self.assertNotEqual(v1,v2)
            with self.assertRaises(urllib.error.HTTPError) as error:post(v1)
            self.assertEqual(error.exception.code,409);self.assertTrue(post(v2)["saved"])
            with urllib.request.urlopen(url+"/api/reviews") as r:history=json.loads(r.read())
            self.assertEqual(len(history["history"]),2);self.assertEqual(history["reviews"][0]["status"],"Escalated")
            self.assertEqual(history["reviews"][0]["owner"],"Test owner")
        finally:server.shutdown();server.server_close()


class MechanismRegressions(unittest.TestCase):
    def test_crowded_exact_text_equal_amount_pair_is_retained(self):
        import pandas as pd
        from build import duplicate_candidates
        rows=[]
        for i in range(200):
            rows.append({"work_id":f"w{i:04d}","description_normalized":"construction concrete cross drainage culvert beside panchayat depot","ida_key":"ida","activity_type":"road","sanction_amount_paise":100000+i,"continuation_cue_flag":False})
        rows[-1]["sanction_amount_paise"]=rows[0]["sanction_amount_paise"]
        work,pairs,_=duplicate_candidates(pd.DataFrame(rows))
        self.assertTrue(((pairs.work_id_a=="w0000")&(pairs.work_id_b=="w0199")&pairs.high_similarity_review).any())
        self.assertTrue(work.iloc[0].high_similarity_review_flag)

    def test_forecast_never_uses_target_or_future_month(self):
        import forecast
        rows=[{"month":f"2025-{i:02d}","paise":i*100} for i in range(1,13)]+[{"month":f"2026-{i:02d}","paise":i*200} for i in range(1,10)]
        a=forecast.evaluate(rows,"2026-09-14")
        changed=[dict(r) for r in rows];changed[-1]["paise"]=10**12
        b=forecast.evaluate(changed,"2026-09-14")
        self.assertEqual(a,b);self.assertTrue(a["available"])
        self.assertTrue(all(r["train_through"]<r["month"] for r in a["folds"]))
        self.assertEqual(sum(r["split"]=="test" for r in a["folds"]),3)

    def test_forecast_missing_month_is_not_zero(self):
        import forecast
        rows=[{"month":f"2025-{i:02d}","paise":100} for i in range(1,13) if i!=7]+[{"month":f"2026-{i:02d}","paise":200} for i in range(1,9)]
        self.assertFalse(forecast.evaluate(rows,"2026-09-14")["available"])


class EndToEnd(unittest.TestCase):
    """Demo smoke test: start the loopback server and exercise the key endpoints."""
    @classmethod
    def setUpClass(cls):
        if not (LOCAL / "mplads.sqlite3").is_file():
            raise unittest.SkipTest("Run build.py first")
        import threading, serve, tempfile
        cls.temp=tempfile.TemporaryDirectory(prefix="mplads-tests-")
        cls.server = serve.make_server(port=0, local=LOCAL, review_db=Path(cls.temp.name)/"reviews.sqlite3", verify=False)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close();cls.temp.cleanup()

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
        s, forecast = self._get("/api/forecast"); self.assertEqual(s, 200); self.assertIn("available", forecast)
        self.assertTrue(all(f["month"] < forecast["forecast_month"] for f in forecast.get("folds", [])))
        s, reviews = self._get("/api/reviews"); self.assertEqual(s, 200); self.assertEqual(reviews["history"], [])

    def test_authority_profile_and_vendor_work_grain(self):
        from urllib.parse import urlencode
        with db() as conn:
            for kind,table,column in [("ida","IDA_Features","ida_key"),("mp","MP_Features","mp_key"),("vendor","Vendor_Features","vendor_id")]:
                key=conn.execute(f'SELECT "{column}" FROM "{table}" ORDER BY work_count DESC LIMIT 1').fetchone()[0]
                _, p=self._get("/api/entity?"+urlencode({"kind":kind,"key":key}))
                self.assertEqual(p["summary"]["works"],sum(y["works"] for y in p["years"]))
                exact=dict(conn.execute(p["sql"],p["params"]).fetchone())
                self.assertEqual(p["summary"],exact)
                if kind=="vendor":
                    expected=conn.execute("SELECT COUNT(DISTINCT work_id) FROM Work_Features WHERE work_id IN (SELECT work_id FROM Payment_Features WHERE vendor_id=?)",[key]).fetchone()[0]
                    self.assertEqual(p["summary"]["works"],expected)

    def test_concentration_search_uses_authority_name(self):
        _, result=self._get("/api/table?kind=concentration&q=Jaunpur")
        self.assertGreater(result["total"],0)
        self.assertTrue(all("jaunpur" in row["ida_name"].lower() for row in result["items"]))

    def test_concentration_ranks_material_multi_vendor_rows_first(self):
        _, result=self._get("/api/table?kind=concentration&limit=100")
        material=[r["vendor_count"]>=3 and r["successful_payment_paise"]>=500000000 for r in result["items"]]
        # Once a trivial row appears, no material row may follow it; HHI descends within the material block.
        self.assertEqual(material, sorted(material, reverse=True))
        head=[r["vendor_hhi"] for r,m in zip(result["items"],material) if m]
        self.assertEqual(head, sorted(head, reverse=True))
        self.assertTrue(material[0])

    def test_unknown_job_is_bad_request(self):
        import urllib.request, urllib.error
        url=f"http://127.0.0.1:{self.port}"
        req=urllib.request.Request(url+"/api/jobs",data=json.dumps({"name":"not-a-job"}).encode(),headers={"Content-Type":"application/json","Origin":url})
        with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(req,timeout=10)
        self.assertEqual(ctx.exception.code,400)

    def test_dictionary_search_definition_and_pagination(self):
        _, result=self._get("/api/table?kind=dictionary&q=paise")
        self.assertGreater(result["total"],0)
        self.assertTrue(all("paise" in str(row).lower() for row in result["items"]))
        _, first=self._get("/api/table?kind=dictionary&limit=10&offset=0")
        _, second=self._get("/api/table?kind=dictionary&limit=10&offset=10")
        keys=lambda result:{(r["table"],r["field"]) for r in result["items"]}
        self.assertFalse(keys(first)&keys(second))
        self.assertEqual(len(second["items"]),10)

    def test_duplicate_search_full_record_and_literal_wildcard(self):
        from urllib.parse import quote
        with db() as conn:
            key=conn.execute("SELECT work_id_a FROM Duplicate_Candidates LIMIT 1").fetchone()[0]
        _, result=self._get("/api/duplicates?q="+quote(key))
        self.assertGreater(result["total"],0)
        self.assertTrue(all(key in (row["work_id_a"],row["work_id_b"]) for row in result["items"]))
        _, wildcard=self._get("/api/table?kind=dictionary&q=%25")
        self.assertTrue(all("%" in str(row) for row in wildcard["items"]))

    def test_unknown_and_predictive_questions_are_refused(self):
        import urllib.parse
        for question in ("Predict tomorrow weather", "Weather in Bihar", "Predict future payments"):
            _, result = self._get("/api/ask?q=" + urllib.parse.quote(question))
            self.assertEqual(result["sql"], "")
            self.assertEqual(result["rows"], [])

    def test_unsupported_grain_metrics_are_refused(self):
        import urllib.parse
        for question in ("Top vendors by delays", "Monthly completed works", "Monthly payments for Lok Sabha", "Top months by payments"):
            _, result = self._get("/api/ask?q=" + urllib.parse.quote(question))
            self.assertEqual(result["sql"], "")

    def test_supported_monthly_payments_remain_available(self):
        import urllib.parse
        _, result = self._get("/api/ask?q=" + urllib.parse.quote("Monthly settled payments in Bihar"))
        self.assertTrue(result["sql"].startswith("SELECT"))
        self.assertGreater(result["row_count"], 0)
        for question, expected in (("States by pending payments", "pending_paise"), ("Activities by cost outliers", "cost_outliers")):
            _, result = self._get("/api/ask?q=" + urllib.parse.quote(question))
            self.assertIn(expected, {c["key"] for c in result["columns"]})
        _, result = self._get("/api/ask?q=" + urllib.parse.quote("Vendors by pending payments"))
        self.assertIn("pending", result["summary"])


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
