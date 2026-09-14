"""Loopback-only paginated investigation API; new source data never leave this device."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import shutil
import sqlite3
from urllib.parse import parse_qs, unquote, urlsplit

WORK_KEY=re.compile(r"[a-z_]+:[a-z0-9]*:\d+")

ROOT=Path(__file__).resolve().parents[1]
LOCAL=Path(__file__).parent/"local"
SORTS={"priority_score","sanction_amount_paise","successful_payment_paise","sanction_age_days","isolation_percentile","work_id"}
SIGNALS={"pending_recommendation_45d_flag","sanction_delay_45d_flag","open_over_one_year_flag","no_payment_three_months_flag","paid_over_sanction_flag","completion_over_sanction_flag","repeat_payment_report_flag","high_cost_peer_flag","high_similarity_review_flag","completion_without_payment_flag","description_changed_flag","recommendation_missing_flag"}
OUTCOMES={"Needs evidence","Expected variation","Data issue","Substantiated issue"}
TABLES={"mps":("MP_Features","mp_name","successful_payment_paise"),"idas":("IDA_Features","ida_name","successful_payment_paise"),"vendors":("Vendor_Features","vendor_name","successful_payment_paise"),"payments":("Payment_Features","vendor_name","source_record"),"dictionary":("Feature_Dictionary","field","table")}


def connect(path,readonly=True):
    db=sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True,timeout=15) if readonly else sqlite3.connect(path,timeout=15)
    db.row_factory=sqlite3.Row
    return db


def scalar(params,name,default=""):
    return params.get(name,[default])[0]


def filters(params,prefix=""):
    clauses=[];values=[]
    for key,column in [("state","state"),("fy","sanction_fy"),("lifecycle","lifecycle"),("mp","mp_key"),("ida","ida_key")]:
        value=scalar(params,key)
        if value:
            if len(value)>300: raise ValueError("Filter too long")
            clauses.append(f"{prefix}{column} = ?");values.append(value)
    signal=scalar(params,"signal")
    if signal:
        if signal not in SIGNALS: raise ValueError("Unknown signal")
        clauses.append(f"{prefix}{signal} = 1")
    query=scalar(params,"q").strip()
    if query:
        if len(query)>200:raise ValueError("Search is limited to 200 characters")
        escaped=query.replace("\\","\\\\").replace("%","\\%").replace("_","\\_")
        clauses.append("("+" OR ".join(f"{prefix}{col} LIKE ? ESCAPE '\\'" for col in ["work_id","description","mp_name","ida_name"])+")")
        values.extend(["%"+escaped+"%"]*4)
    vendor=scalar(params,"vendor")
    if vendor:
        if not vendor.isdigit():raise ValueError("Invalid vendor ID")
        clauses.append(f"{prefix}work_id IN (SELECT work_id FROM Payment_Features WHERE vendor_id=?)");values.append(vendor)
    return (" WHERE "+" AND ".join(clauses) if clauses else ""),values


def page(params):
    size=int(scalar(params,"limit","50"));offset=int(scalar(params,"offset","0"))
    if not 1<=size<=100 or not 0<=offset<=10000000:raise ValueError("Invalid page size or offset")
    return size,offset


def make_server(port=8766,local=LOCAL,review_db=None,directory=None):
    meta=json.loads((local/"audit.json").read_text(encoding="utf-8"))
    if not meta.get("all_checks_passed"):raise ValueError("Build is not verified")
    review_db=review_db or local/"reviews.sqlite3"
    review_db.parent.mkdir(parents=True,exist_ok=True)
    with connect(review_db,False) as db:
        db.execute("CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY, record_key TEXT NOT NULL, outcome TEXT NOT NULL, note TEXT NOT NULL, created TEXT NOT NULL, version TEXT NOT NULL)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_review_record_version ON reviews(record_key,version,id)")
    server=ThreadingHTTPServer(("127.0.0.1",port),partial(Handler,directory=str(directory or ROOT/"mplads-prototype/dist/six")))
    server.local,server.review_db,server.meta=local,review_db,meta
    server.version=meta["version"]+":"+meta["source_fingerprint"]+":"+meta.get("work_features_sha256",meta["as_of"])
    return server


class Handler(SimpleHTTPRequestHandler):
    def log_message(self,format,*args):
        # Do not write query strings, work IDs or review content into logs.
        pass

    def allowed_host(self):
        return self.headers.get("Host","") in {f"127.0.0.1:{self.server.server_port}",f"localhost:{self.server.server_port}"}

    def end_headers(self):
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Referrer-Policy","no-referrer")
        self.send_header("X-Frame-Options","DENY")
        self.send_header("Cross-Origin-Resource-Policy","same-origin")
        self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'")
        super().end_headers()

    def reply(self,payload,status=200):
        body=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode("utf-8")
        self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(body)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(body)

    def list_directory(self,path):
        self.send_error(403,"Directory listing disabled");return None

    def do_HEAD(self):
        if not self.allowed_host():return self.send_error(403)
        return super().do_HEAD()

    def download(self,name):
        allowed={"Work_Features.csv","Payment_Features.csv","Duplicate_Candidates.csv","MP_Features.csv","IDA_Features.csv","Vendor_Features.csv","Vendor_Connections.csv","Monthly_Payments.csv","Calamity_Consents.csv","Feature_Dictionary.csv","Quarantine.csv","audit.json","AB_Report.md","ab_metrics.json","ab_controlled_benchmark.csv","ab_actual_scores.csv","reproducibility.json"}
        if name=="MPLADS_Six_Source_Review.xlsx":
            file=ROOT/"outputs/six-source-2026-09-09/MPLADS_Six_Source_Review.xlsx"
        elif name in allowed:file=self.server.local/name
        else:return self.reply({"error":"Unknown download"},404)
        if not file.is_file():return self.reply({"error":"This artifact has not been generated yet"},503)
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if file.suffix==".xlsx" else ("text/csv; charset=utf-8" if file.suffix==".csv" else "application/json" if file.suffix==".json" else "text/markdown; charset=utf-8")
        self.send_response(200);self.send_header("Content-Type",mime);self.send_header("Content-Disposition",f'attachment; filename="{file.name}"');self.send_header("Content-Length",str(file.stat().st_size));self.send_header("Cache-Control","no-store");self.end_headers()
        with file.open("rb") as stream:shutil.copyfileobj(stream,self.wfile,1024*1024)

    def do_GET(self):
        if not self.allowed_host():return self.reply({"error":"Exact loopback host required"},403)
        url=urlsplit(self.path);route=unquote(url.path);params=parse_qs(url.query)
        if route=="/api/health":return self.reply({"application":"MPLADS Six Source","version":self.server.version,"localOnly":True})
        if route=="/api/meta":return self.reply({**self.server.meta,"review_version":self.server.version})
        if route=="/api/validation":
            path=self.server.local/"ab_metrics.json"
            return self.reply(json.loads(path.read_text(encoding="utf-8"))) if path.is_file() else self.reply({"error":"Run six_source/validate.py first"},503)
        if route.startswith("/api/download/"):return self.download(route.removeprefix("/api/download/"))
        if route=="/api/reviews":
            with connect(self.server.review_db) as db:
                rows=[dict(r) for r in db.execute("SELECT * FROM reviews WHERE version=? ORDER BY id",[self.server.version])]
            latest={r["record_key"]:r for r in rows}
            return self.reply({"reviews":list(latest.values()),"history":rows,"version":self.server.version})
        try:
            with connect(self.server.local/"mplads.sqlite3") as db:
                if route=="/api/options":
                    states=[r[0] for r in db.execute("SELECT DISTINCT state FROM Work_Features ORDER BY state")]
                    years=[r[0] for r in db.execute("SELECT DISTINCT sanction_fy FROM Work_Features WHERE sanction_fy IS NOT NULL ORDER BY sanction_fy")]
                    return self.reply({"states":states,"years":years})
                if route=="/api/overview":
                    metrics="COUNT(*) works, SUM(in_sanctioned) sanctioned, SUM(in_completed) completed, SUM(CASE WHEN priority_band='High' THEN 1 ELSE 0 END) high, SUM(open_over_one_year_flag) open_over_year, SUM(no_payment_three_months_flag) no_payment_3m, SUM(sanction_amount_paise) sanction_paise, SUM(successful_payment_paise) successful_payment_paise, SUM(pending_payment_paise) pending_payment_paise, AVG(priority_score) mean_priority"
                    national=dict(db.execute(f"SELECT {metrics}, COUNT(DISTINCT mp_key) mp_count, COUNT(DISTINCT ida_key) ida_count FROM Work_Features").fetchone())
                    cohorts=[dict(r) for r in db.execute(f"SELECT cohort, {metrics} FROM Work_Features GROUP BY cohort ORDER BY works DESC")]
                    states=[dict(r) for r in db.execute(f"SELECT state, {metrics} FROM Work_Features GROUP BY state ORDER BY high DESC")]
                    top_idas=[dict(r) for r in db.execute(f"SELECT ida_key, ida_name, state, {metrics} FROM Work_Features GROUP BY ida_key ORDER BY high DESC, sanction_paise DESC LIMIT 20")]
                    payload={"national":national,"cohorts":cohorts,"states":states,"top_idas":top_idas}
                    state=scalar(params,"state")
                    if state:
                        if len(state)>300:raise ValueError("Filter too long")
                        payload["state"]=state
                        payload["idas"]=[dict(r) for r in db.execute(f"SELECT ida_key, ida_name, state, {metrics} FROM Work_Features WHERE state=? GROUP BY ida_key ORDER BY high DESC, sanction_paise DESC",[state])]
                    return self.reply(payload)
                if route=="/api/works":
                    where,args=filters(params);size,offset=page(params)
                    sort=scalar(params,"sort","priority_score");order=scalar(params,"order","desc")
                    if sort not in SORTS or order not in {"asc","desc"}:raise ValueError("Invalid sort")
                    summary=dict(db.execute("SELECT COUNT(*) total, SUM(in_sanctioned) sanctions, SUM(in_completed) completions, SUM(sanction_amount_paise) sanction_paise, SUM(successful_payment_paise) successful_payment_paise, SUM(pending_payment_paise) pending_payment_paise, SUM(open_over_one_year_flag) open_over_year, SUM(no_payment_three_months_flag) no_payment_three_months FROM Work_Features"+where,args).fetchone())
                    columns="work_id,mp_name,state,ida_name,activity_type,description,lifecycle,sanction_date,recommendation_date,completion_date,sanction_amount_paise,successful_payment_paise,pending_payment_paise,priority_score,priority_band,reason_codes,isolation_percentile,data_quality_issue_count"
                    rows=db.execute(f"SELECT {columns} FROM Work_Features"+where+f" ORDER BY {sort} {order}, work_id LIMIT ? OFFSET ?",[*args,size,offset])
                    return self.reply({"items":[dict(r) for r in rows],"summary":summary,"limit":size,"offset":offset})
                if route.startswith("/api/work/"):
                    key=route.removeprefix("/api/work/")
                    if not WORK_KEY.fullmatch(key):raise ValueError("Invalid work ID")
                    row=db.execute("SELECT * FROM Work_Features WHERE work_id=?",[key]).fetchone()
                    if row is None:return self.reply({"error":"Work not found"},404)
                    reasons=[dict(r) for r in db.execute("SELECT * FROM Rule_Contributions WHERE work_id=? ORDER BY points DESC,rule",[key])]
                    pairs=[dict(r) for r in db.execute("SELECT * FROM Duplicate_Candidates WHERE work_id_a=? OR work_id_b=? ORDER BY similarity DESC LIMIT 100",[key,key])]
                    return self.reply({"work":dict(row),"reasons":reasons,"pairs":pairs,"pairs_returned_limit":100,"version":self.server.version})
                if route=="/api/table":
                    kind=scalar(params,"kind","mps")
                    if kind not in TABLES:raise ValueError("Unknown table")
                    table,search,sort=TABLES[kind];size,offset=page(params);clause=[];args=[]
                    query=scalar(params,"q").strip()
                    if len(query)>200:raise ValueError("Search too long")
                    if query:clause.append(f'"{search}" LIKE ?');args.append("%"+query+"%")
                    for key in (["work_id","vendor_id"] if kind=="payments" else []):
                        value=scalar(params,key)
                        if value:clause.append(f'"{key}"=?');args.append(value)
                    where=" WHERE "+" AND ".join(clause) if clause else ""
                    total=db.execute(f'SELECT COUNT(*) FROM "{table}"'+where,args).fetchone()[0]
                    rows=db.execute(f'SELECT * FROM "{table}"'+where+f' ORDER BY "{sort}" DESC LIMIT ? OFFSET ?',[*args,size,offset])
                    return self.reply({"items":[dict(r) for r in rows],"total":total,"limit":size,"offset":offset})
                if route=="/api/months":return self.reply({"items":[dict(r) for r in db.execute("SELECT payment_month,SUM(successful_payment_paise) successful_payment_paise,SUM(pending_payment_paise) pending_payment_paise FROM Monthly_Payments GROUP BY payment_month ORDER BY payment_month")]})
                if route=="/api/duplicates":
                    size,offset=page(params)
                    total=db.execute("SELECT COUNT(*) FROM Duplicate_Candidates").fetchone()[0]
                    rows=db.execute("SELECT p.*, a.description description_a,b.description description_b,a.sanction_amount_paise amount_a,b.sanction_amount_paise amount_b FROM Duplicate_Candidates p JOIN Work_Features a ON a.work_id=p.work_id_a JOIN Work_Features b ON b.work_id=p.work_id_b ORDER BY p.high_similarity_review DESC,p.similarity DESC,p.pair_id LIMIT ? OFFSET ?",[size,offset])
                    return self.reply({"items":[dict(r) for r in rows],"total":total})
        except (ValueError,TypeError) as exc:return self.reply({"error":str(exc)},400)
        except sqlite3.Error:return self.reply({"error":"Local data query failed; verify the dataset build"},500)
        if route.startswith("/api/"):return self.reply({"error":"Unknown endpoint"},404)
        if route=="/":self.path="/six.html"
        return super().do_GET()

    def do_POST(self):
        origin=self.headers.get("Origin","")
        if not self.allowed_host() or origin!=f'http://{self.headers.get("Host", "")}':return self.reply({"error":"Local same-origin write required"},403)
        if urlsplit(self.path).path!="/api/reviews":return self.reply({"error":"Unknown endpoint"},404)
        try:
            size=int(self.headers.get("Content-Length","0"))
            if not 0<size<=16384:return self.reply({"error":"Review payload limit is 16 KiB"},413)
            if self.headers.get("Content-Type","").split(";")[0]!="application/json":return self.reply({"error":"JSON required"},415)
            data=json.loads(self.rfile.read(size));key=data.get("key");note=data.get("note");outcome=data.get("outcome")
            if not isinstance(key,str) or len(key)>100 or not isinstance(note,str) or not 1<=len(note.strip())<=3000 or outcome not in OUTCOMES:raise ValueError("Valid record, disposition and 1-3000 character evidence note required")
            if data.get("version")!=self.server.version:return self.reply({"error":"Dataset changed; reload before saving"},409)
            with connect(self.server.local/"mplads.sqlite3") as db:
                found=db.execute("SELECT 1 FROM Duplicate_Candidates WHERE pair_id=?",[key]).fetchone() if key.startswith("pair:") else db.execute("SELECT 1 FROM Work_Features WHERE work_id=?",[key]).fetchone()
            if not found:raise ValueError("Record not in this dataset")
            with connect(self.server.review_db,False) as db:
                cur=db.execute("INSERT INTO reviews(record_key,outcome,note,created,version) VALUES (?,?,?,?,?)",[key,outcome,note.strip(),datetime.now(timezone.utc).isoformat(),self.server.version]);identifier=cur.lastrowid
            return self.reply({"saved":True,"id":identifier,"version":self.server.version})
        except (ValueError,TypeError,AttributeError,json.JSONDecodeError):return self.reply({"error":"Invalid review payload"},400)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--port",type=int,default=8766);args=parser.parse_args()
    server=make_server(args.port)
    print(f"MPLADS Six Source: http://127.0.0.1:{server.server_port}/",flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
