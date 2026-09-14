"""Run after independent rebuilds; preserve raw inputs and compare meaningful outputs."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical_snapshot(path):
    result = json.loads(path.read_text(encoding='utf-8'))
    result.get('audit', {}).pop('generated_at_utc', None)
    return result

def main():
    core = ROOT / 'pipeline_research/artifacts'
    rerun = ROOT / 'pipeline_research/artifacts_reproduced'
    research = Path(__file__).resolve().parent
    checks = {}
    for path in core.glob('*.csv'):
        checks['core_' + path.name] = digest(path) == digest(rerun / path.name)
    checks['core_snapshot_except_generation_timestamp'] = canonical_snapshot(core / 'snapshot.json') == canonical_snapshot(rerun / 'snapshot.json')
    for name in ['metrics.json', 'actual_test_scores.csv', 'controlled_benchmark.csv', 'split_manifest.csv', 'AB_Validation_Report.md']:
        checks['ab_' + name] = digest(research / name) == digest(research / 'reproduced' / name)
    payload = json.loads((core / 'snapshot.json').read_text(encoding='utf-8'))
    for key, source in payload['meta']['sourceFiles'].items():
        checks['raw_' + key + '_unchanged'] = digest(ROOT / 'Dataset' / source['file']) == source['sha256']
    report = {'checks': checks, 'all_equal': all(checks.values()), 'note': 'Core generation timestamp excluded; all data tables and features compared. A/B outputs compared byte for byte.', 'core_snapshot_sha256': digest(core / 'snapshot.json'), 'ab_metrics_sha256': digest(research / 'metrics.json')}
    (research / 'reproducibility_check.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    assert report['all_equal']

if __name__ == '__main__':
    main()
