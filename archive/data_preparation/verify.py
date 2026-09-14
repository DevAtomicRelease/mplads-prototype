"""Independent raw-CSV controls, output invariants and deterministic rebuild check."""
from __future__ import annotations
import argparse
import csv
from decimal import Decimal,ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as s:
        for b in iter(lambda:s.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def verify(folder,compare=None):
    m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    results=[]
    def eq(name,a,b):
        assert a==b,f'{name}: {a!r} != {b!r}'
        results.append(dict(check=name,passed=True))
    totals={k:0 for k in ['recommendation','sanction','completion','success','pending','allocation','consent']}
    works=set();payment_records=quarantined=source_rows=0;raw_controls={}
    def content_update(h,values):
        h.update((json.dumps(list(values),ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8'))
    for item in m['inputs']:
        path=ROOT/'Dataset'/item['source_file'];eq('Raw hash '+item['source_file'],digest(path),item['sha256'])
        with path.open(encoding='utf-8-sig',newline='') as stream:
            n=0;reader=csv.DictReader(stream);original_fields=reader.fieldnames;content_hash=hashlib.sha256()
            for row in reader:
                content_update(content_hash,[row[f] if row[f] is not None else '' for f in original_fields])
                n+=1;kind=item['kind'];wid=row.get('WORK_RECOMMENDATION_DTL_ID','')
                if kind in ['recommended','sanctioned']:
                    code={'Lok Sabha':'LS','Rajya_Sabha_retired':'RSR','Rajya_Sabha_sitting':'RSS'}[item['cohort']]
                    key=('rec2:'+code+':'+wid) if kind=='recommended' and row['FLAG']=='2' else 'work:'+wid
                    works.add(key)
                if kind=='allocations':totals['allocation']+=int(Decimal(row['ALLOCATED_AMT']).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)*100)
                elif kind=='consents':totals['consent']+=int(Decimal(row['CONSENTED_AMOUNT'])*100)
                elif kind=='recommended':totals['recommendation']+=int(Decimal(row['RECOMMENDED_AMOUNT'])*100)
                elif kind=='sanctioned':totals['sanction']+=int(Decimal(row['SANCTION_AMOUNT'])*100)
                elif kind=='completed':totals['completion']+=int(Decimal(row['ACTUAL_AMOUNT'])*100)
                elif kind=='payments':
                    if not wid or not row['FUND_DISBURSED_AMT']:quarantined+=1;continue
                    payment_records+=1
                    status={'Payment Success':'success','Payment In-Progress':'pending'}[row['WORK_STATUS']]
                    totals[status]+=int(Decimal(row['FUND_DISBURSED_AMT'])*100)
            eq('Original rows '+item['source_file'],n,item['source_rows']);source_rows+=n
            code={'Lok Sabha':'LS','Rajya_Sabha_retired':'RSR','Rajya_Sabha_sitting':'RSS'}[item['cohort']]
            raw_controls['Raw_'+code+'_'+item['kind']]=(original_fields,content_hash.hexdigest())
    db=sqlite3.connect(f'file:{(folder/"mplads_prepared.sqlite3").as_posix()}?mode=ro',uri=True)
    scalar=lambda sql:db.execute(sql).fetchone()[0]
    eq('SQLite integrity',scalar('PRAGMA integrity_check'),'ok')
    eq('Safe work union',scalar('SELECT COUNT(*) FROM Work_Features'),len(works))
    eq('Exact work key membership',set(r[0] for r in db.execute('SELECT work_id FROM Work_Features')),works)
    eq('Accepted payment row count',scalar('SELECT COUNT(*) FROM Payment_Features'),payment_records)
    eq('Quarantine row count',scalar('SELECT COUNT(*) FROM Quarantine'),quarantined)
    controls=[('Work_Features','recommended_amount_paise','recommendation'),('Work_Features','sanction_amount_paise','sanction'),('Work_Features','completion_actual_paise','completion'),('MP_Term_Features','allocated_paise','allocation'),('Calamity_Consents','consent_amount_paise','consent')]
    for table,column,total in controls:eq(table+' '+column,scalar(f'SELECT SUM({column}) FROM {table}'),totals[total])
    for table in ['Work_Features','MP_Term_Features','IDA_Features','Vendor_Features','Vendor_Connections','Monthly_Payments','Cohort_Summary']:
        for column,total in [('successful_payment_paise','success'),('pending_payment_paise','pending')]:eq(table+' '+column,scalar(f'SELECT SUM({column}) FROM {table}'),totals[total])
    eq('No duplicate master keys',scalar('SELECT COUNT(*)-COUNT(DISTINCT work_id) FROM Work_Features'),0)
    eq('No missing payment work links',scalar('SELECT COUNT(*) FROM Payment_Features p LEFT JOIN Work_Features w ON p.work_id=w.work_id WHERE w.work_id IS NULL'),0)
    eq('No mixed MP term in payment link',scalar('SELECT COUNT(*) FROM Payment_Features p JOIN Work_Features w ON p.work_id=w.work_id WHERE p.mp_key != w.mp_key'),0)
    eq('FLAG=2 never treated as sanctioned',scalar("SELECT COUNT(*) FROM Work_Features WHERE identity_namespace='recommendation_flag2' AND in_sanctioned=1"),0)
    eq('No ratio imputation for unknown successful payments',scalar('SELECT COUNT(*) FROM Work_Features WHERE has_successful_payment_evidence=0 AND paid_to_sanction_ratio IS NOT NULL'),0)
    eq('No ratio with zero sanction denominator',scalar('SELECT COUNT(*) FROM Work_Features WHERE sanction_amount_paise=0 AND paid_to_sanction_ratio IS NOT NULL'),0)
    eq('Pending rows never counted as successes',scalar("SELECT COUNT(*) FROM Payment_Features WHERE payment_status='Payment In-Progress' AND successful_paise!=0"),0)
    eq('INR 1 reconciliation tolerance',scalar('SELECT COUNT(*) FROM Work_Features WHERE paid_over_sanction_flag != COALESCE(payment_sanction_delta_paise>100,0)'),0)
    eq('Completion amount arithmetic',scalar('SELECT COUNT(*) FROM Work_Features WHERE completion_sanction_delta_paise != completion_actual_paise-sanction_amount_paise'),0)
    eq('Payment amount arithmetic',scalar('SELECT COUNT(*) FROM Work_Features WHERE has_successful_payment_evidence=1 AND payment_sanction_delta_paise != successful_payment_paise-sanction_amount_paise'),0)
    eq('Payment/sanction ratio arithmetic',scalar('SELECT COUNT(*) FROM Work_Features WHERE paid_to_sanction_ratio IS NOT NULL AND ABS(paid_to_sanction_ratio-1.0*successful_payment_paise/sanction_amount_paise)>0.000000001'),0)
    eq('Sanction delay arithmetic',scalar('SELECT COUNT(*) FROM Work_Features WHERE sanction_delay_days != JULIANDAY(sanction_date)-JULIANDAY(recommendation_date)'),0)
    eq('Completion duration arithmetic',scalar('SELECT COUNT(*) FROM Work_Features WHERE completion_days != JULIANDAY(completion_date)-JULIANDAY(sanction_date)'),0)
    eq('Unweighted screen counts match reasons',scalar('SELECT COUNT(*) FROM Work_Features w LEFT JOIN (SELECT work_id,COUNT(*) n FROM Work_Signals GROUP BY work_id) s ON s.work_id=w.work_id WHERE w.screening_signal_count != COALESCE(s.n,0)'),0)
    eq('Concentration bounds',scalar('SELECT COUNT(*) FROM IDA_Year_Concentration WHERE vendor_hhi<0 OR vendor_hhi>1.000000001 OR top_vendor_share<0 OR top_vendor_share>1.000000001'),0)
    eq('Candidate pair endpoints differ',scalar('SELECT COUNT(*) FROM Duplicate_Candidates WHERE work_id_a=work_id_b'),0)
    eq('Candidate foreign keys',scalar('SELECT COUNT(*) FROM Duplicate_Candidates d LEFT JOIN Work_Features a ON a.work_id=d.work_id_a LEFT JOIN Work_Features b ON b.work_id=d.work_id_b WHERE a.work_id IS NULL OR b.work_id IS NULL'),0)
    eq('All pipeline checks exported',scalar('SELECT COUNT(*) FROM Validation_Checks'),len(m['checks']))
    eq('No failing exported checks',scalar('SELECT COUNT(*) FROM Validation_Checks WHERE passed=0'),0)
    raw_tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Raw_%'")]
    eq('All 18 raw tables',len(raw_tables),18)
    eq('Raw SQLite record conservation',sum(scalar(f'SELECT COUNT(*) FROM "{name}"') for name in raw_tables),source_rows)
    for name,(fields,expected_content) in raw_controls.items():
        selected=','.join('"'+f.replace('"','""')+'"' for f in fields)
        actual_content=hashlib.sha256()
        for row in db.execute(f'SELECT {selected} FROM "{name}" ORDER BY source_record'):content_update(actual_content,row)
        eq('Raw SQLite original strings '+name,actual_content.hexdigest(),expected_content)
    for table in m['outputs']:
        fields={row[1] for row in db.execute(f'PRAGMA table_info("{table}")')}
        defined={row[0] for row in db.execute('SELECT field FROM Feature_Dictionary WHERE "table"=?',(table,))}
        eq('Dictionary complete for '+table,defined,fields)
    for name,info in m['outputs'].items():eq('Output record count '+name,scalar(f'SELECT COUNT(*) FROM "{name}"'),info['rows'])
    db.close()
    for filename,expected in m['csv_sha256'].items():eq('CSV hash '+filename,digest(folder/filename),expected)
    for filename,expected in m['code_sha256'].items():eq('Reproduction code hash '+filename,digest(ROOT/filename),expected)
    rebuilt=None
    if compare:
        other=json.loads((compare/'manifest.json').read_text(encoding='utf-8'))
        eq('Rebuild file set',sorted(m['csv_sha256']),sorted(other['csv_sha256']))
        for filename,expected in m['csv_sha256'].items():eq('Rebuilt CSV '+filename,digest(compare/filename),expected)
        rebuilt=dict(directory=str(compare),matching_csv_files=len(m['csv_sha256']))
    report=dict(checks_passed=len(results),raw_source_rows=source_rows,work_rows=len(works),payment_rows=payment_records,totals_paise=totals,rebuild=rebuilt,checks=results)
    (folder/'independent_verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--folder',type=Path,default=ROOT/'data_preparation'/'local'/'release_2026-09-10_v2');parser.add_argument('--compare-dir',type=Path)
    args=parser.parse_args();verify(args.folder,args.compare_dir)
