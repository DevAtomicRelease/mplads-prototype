"""Verify artifact hashes and input preservation for two completed runs."""
import argparse
import json
from pathlib import Path
from run_ab import sha,save_json,ROOT,HERE

def main():
    ap=argparse.ArgumentParser();ap.add_argument('first',type=Path);ap.add_argument('second',type=Path);ap.add_argument('--report',type=Path,required=True);a=ap.parse_args()
    a.report=a.report.resolve()
    if a.report.exists() or a.report.suffix!='.json' or a.report.parent not in [(HERE/'local').resolve(),(HERE/'reproduced').resolve()]:raise ValueError('Report must be a new JSON directly inside evaluation_18/local or evaluation_18/reproduced')
    first=json.loads((a.first/'manifest.json').read_text());second=json.loads((a.second/'manifest.json').read_text());checks=[]
    def check(name,ok):checks.append(dict(check=name,passed=bool(ok)))
    check('Manifests byte-identical',sha(a.first/'manifest.json')==sha(a.second/'manifest.json'))
    check('Same artifact set',set(first['output_sha256'])==set(second['output_sha256']))
    for name,h in first['output_sha256'].items():
        check('Artifact '+name,sha(a.first/name)==h==sha(a.second/name)==second['output_sha256'][name])
    for p,h in first['verified_input_sha256'].items():check('Input remains unchanged '+p,sha(ROOT/p)==h)
    for p,h in first['code_sha256'].items():check('Frozen evaluation source '+p,sha(HERE/p)==h)
    data=dict(passed=all(x['passed'] for x in checks),checks=checks,first_manifest_sha256=sha(a.first/'manifest.json'),second_manifest_sha256=sha(a.second/'manifest.json'))
    save_json(a.report,data);print(json.dumps(dict(passed=data['passed'],checks=len(checks),artifacts=len(first['output_sha256'])),indent=2))
    if not data['passed']:raise SystemExit(1)

if __name__=='__main__':main()
