"""Loopback-only service. Real data and append-only reviews stay outside the web build."""
import argparse
import gzip
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT.parent / 'pipeline_research/artifacts/snapshot.json'
REVIEW_DB = ROOT.parent / 'prototype-local-data/reviews.sqlite3'
LOCAL_FILES = {
    '/api/download/final.xlsx': (ROOT.parent / 'outputs/01a06d6b-9b94-7a61-b28b-6f9116f20942/MPLADS_Final_Core_Dataset_2026-09-06.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    '/api/snapshot': (CACHE, 'application/json'),
    '/api/validation': (ROOT.parent / 'validation_research/metrics.json', 'application/json'),
    '/api/pipeline-audit': (ROOT.parent / 'pipeline_research/artifacts/audit.json', 'application/json'),
    '/api/download/works.csv': (ROOT.parent / 'pipeline_research/artifacts/Work_Features.csv', 'text/csv'),
    '/api/download/ab-scores.csv': (ROOT.parent / 'validation_research/actual_test_scores.csv', 'text/csv'),
    '/api/download/ab-report.md': (ROOT.parent / 'validation_research/AB_Validation_Report.md', 'text/markdown'),
    '/api/download/plan.md': (ROOT / 'SOLUTION_PLAN.md', 'text/markdown'),
}
OUTCOMES = {'Needs evidence', 'Expected variation', 'Data issue', 'Substantiated issue'}

@contextmanager
def connect_db(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY, record_key TEXT NOT NULL, outcome TEXT NOT NULL, note TEXT NOT NULL, updated TEXT NOT NULL, version TEXT NOT NULL)')
    try:
        with db:
            yield db
    finally:
        db.close()

def make_server(port=8765, db_path=REVIEW_DB, snapshot_path=CACHE, directory=None):
    payload = json.loads(snapshot_path.read_text(encoding='utf-8'))
    work = payload['tables']['Work_Features']
    pair = payload['tables']['Duplicate_Candidates']
    keys = {str(row[work['columns'].index('work_id')]) for row in work['rows']}
    a, b = (pair['columns'].index(k) for k in ('work_id_a', 'work_id_b'))
    keys.update(f'pair:{row[a]}-{row[b]}' for row in pair['rows'])
    server = ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, directory=str(directory or ROOT / 'dist/local')))
    server.review_db, server.valid_keys = db_path, keys
    fingerprints = '-'.join(payload['meta']['sourceFiles'][key]['sha256'][:12] for key in sorted(payload['meta']['sourceFiles']))
    server.version = payload['meta']['pipelineVersion'] + ':' + fingerprints
    return server

class Handler(SimpleHTTPRequestHandler):
    def allowed_host(self):
        return self.headers.get('Host', '').split(':')[0] in ('127.0.0.1', 'localhost')

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'")
        super().end_headers()

    def reply(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.allowed_host():
            return self.reply({'error': 'Loopback host required'}, 403)
        route = urlsplit(self.path).path
        if route in ('/api/reviews', '/api/reviews/history'):
            with connect_db(self.server.review_db) as db:
                rows = [dict(row) for row in db.execute('SELECT * FROM reviews ORDER BY id')]
            if route.endswith('/history'):
                return self.reply({'history': rows, 'version': self.server.version})
            latest = {}
            for row in rows:
                if row['version'] == self.server.version:
                    latest[row.pop('record_key')] = row
            return self.reply({'reviews': latest, 'version': self.server.version})
        if route == '/api/health':
            return self.reply({'application': 'MPLADS Insight', 'version': self.server.version, 'localOnly': True})
        local_file = LOCAL_FILES.get(route)
        if local_file:
            target, mime = local_file
            if not target.exists():
                return self.reply({'error': 'Run REBUILD_PROJECT first'}, 503)
            body = target.read_bytes()
            self.send_response(200)
            if 'gzip' in self.headers.get('Accept-Encoding', ''):
                body = gzip.compress(body)
                self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Type', mime + ('; charset=utf-8' if mime.startswith('text/') or mime == 'application/json' else ''))
            if '/download/' in route:
                self.send_header('Content-Disposition', 'attachment; filename="' + target.name + '"')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if route.startswith('/api/'):
            return self.reply({'error': 'Unknown endpoint'}, 404)
        return super().do_GET()

    def do_HEAD(self):
        if not self.allowed_host():
            return self.send_error(403)
        return super().do_HEAD()

    def do_POST(self):
        origin = self.headers.get('Origin', '')
        allowed_origins = {f'http://{self.headers.get("Host", "")}', 'http://127.0.0.1:3000', 'http://localhost:3000'}
        if not self.allowed_host() or origin not in allowed_origins:
            return self.reply({'error': 'Local same-origin request required'}, 403)
        if urlsplit(self.path).path != '/api/reviews':
            return self.reply({'error': 'Unknown endpoint'}, 404)
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.reply({'error': 'JSON required'}, 415)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 16384:
                return self.reply({'error': 'Request must be 1 to 16384 bytes'}, 413)
            value = json.loads(self.rfile.read(size))
            if not isinstance(value, dict):
                raise ValueError('Object required')
            key, outcome, note, version = (value.get(k) for k in ('key', 'outcome', 'note', 'version'))
            if not isinstance(key, str) or key not in self.server.valid_keys:
                raise ValueError('Unknown work or candidate pair')
            if not isinstance(outcome, str) or outcome not in OUTCOMES:
                raise ValueError('Unknown disposition')
            if not isinstance(note, str) or not 1 <= len(note.strip()) <= 3000:
                raise ValueError('Evidence note must be 1 to 3000 characters')
            if version != self.server.version:
                return self.reply({'error': 'Dataset version changed; reload before saving'}, 409)
            updated = datetime.now(timezone.utc).isoformat()
            with connect_db(self.server.review_db) as db:
                cursor = db.execute('INSERT INTO reviews(record_key,outcome,note,updated,version) VALUES (?,?,?,?,?)', (key, outcome, note.strip(), updated, version))
                identifier = cursor.lastrowid
            return self.reply({'review': {'id': identifier, 'outcome': outcome, 'note': note.strip(), 'updated': updated, 'version': version}}, 201)
        except (ValueError, TypeError, UnicodeDecodeError) as exc:
            return self.reply({'error': str(exc)}, 400)
        except sqlite3.Error:
            return self.reply({'error': 'Local review store unavailable; no success recorded'}, 503)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = make_server(args.port)
    print(f'Local prototype: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
