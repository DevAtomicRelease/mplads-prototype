"""Read-only final HTTP, asset-boundary and source checks; no fabricated user reviews."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
def fetch(url):
    with urlopen(url, timeout=30) as response:
        return response.status, response.headers, response.read()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    args = parser.parse_args()
    checks = {}
    status, headers, html = fetch(args.url + '/')
    checks['static_index'] = status == 200 and b'id="root"' in html
    assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', html.decode())
    checks['local_assets_present'] = len(assets) >= 2
    for asset in assets:
        status, headers, body = fetch(args.url + asset)
        checks['asset_' + asset] = status == 200 and len(body) > 100
        if asset.endswith('.js'):
            checks['javascript_mime'] = 'javascript' in headers.get('Content-Type', '')
    _, _, body = fetch(args.url + '/api/snapshot')
    snapshot = json.loads(body)
    expected = json.loads((ROOT / 'pipeline_research/artifacts/snapshot.json').read_text(encoding='utf-8'))
    checks['served_snapshot_matches_disk'] = snapshot == expected
    for name, spec in snapshot['meta']['sourceFiles'].items():
        checks['raw_' + name + '_hash'] = hashlib.sha256((ROOT / 'Dataset' / spec['file']).read_bytes()).hexdigest() == spec['sha256']
    for route in ['/api/health', '/api/validation', '/api/pipeline-audit', '/api/reviews', '/api/reviews/history', '/api/download/works.csv', '/api/download/ab-scores.csv', '/api/download/ab-report.md', '/api/download/plan.md']:
        checks[route] = fetch(args.url + route)[0] == 200
    work = snapshot['tables']['Work_Features']
    description_index = work['columns'].index('work_description')
    sentinels = [str(row[description_index]).encode() for row in work['rows'][:20] if len(str(row[description_index])) > 30]
    shipped = ROOT / 'mplads-prototype/dist/local'
    for file in shipped.rglob('*'):
        if file.is_file():
            assert file.suffix not in {'.xlsx', '.csv', '.sqlite3'}, 'Data file inside static build'
            content = file.read_bytes()
            assert not any(sentinel in content for sentinel in sentinels), 'Real work description inside static build'
    checks['real_data_not_in_static_build'] = True
    print(json.dumps({'checks': checks, 'all_passed': all(checks.values())}, indent=2))
    assert all(checks.values())

if __name__ == '__main__':
    main()
