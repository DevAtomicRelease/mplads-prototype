"""Explicit field dictionary and user-facing review materials."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from contracts import VERSION

DEFINITIONS={
 'check':'Explicit validation or reconciliation assertion name.',
 'actual':'Observed value from the pipeline check; text preserves mixed numeric, hash and structural comparisons.',
 'expected':'Expected source control, reference value or invariant for the pipeline assertion.',
 'passed':'True only when the actual and expected values compare equal. Failed pipeline checks stop the build.',
 'table':'Prepared CSV/SQLite table that contains the documented field.',
 'grain':'What one row represents in the documented table. Do not sum nonadditive measures across grains.',
 'dtype':'In-memory pandas data type before CSV export; SQLite stores nullable date columns as ISO text.',
 'unit':'Measurement or identifier convention for this field.',
 'definition':'Exact interpretation and construction of the documented field, including important missing-data limits.',
 'source':'Source role, input field or feature transformation that supplies the documented value.',
 'availability':'Feature timing or source-coverage qualification. Event date is not evidence of when a value was known.',
 'model_use':'Permitted interpretation and prediction-time caveat; not a claim that the feature is validated for a model.',
 'mp_key':'Term-level join key: SHA-256 (first 24 hex digits) of house code, normalized MP name, exact supplied tenure-start and tenure-end strings. Validated unique against allocations; never merges terms by Sitting MP label.',
 'source_id':'Unique source reference: cohort code (LS, RSR, RSS), file kind and one-based CSV data-record number. Quoted multiline fields mean record number is not physical file line.',
 'source_file':'Path relative to the immutable Dataset directory.',
 'source_record':'One-based CSV data-record ordinal, excluding header; not physical line number.',
 'cohort':'Original folder selection: Lok Sabha, Rajya_Sabha_retired or Rajya_Sabha_sitting. Not inferred from TENURE text.',
 'house_name':'Original HOUSE_NAME in allocation source. House codes 1 and 2 denote Rajya Sabha and Lok Sabha in these exports.',
 'allocation_state':'STATE_NAME from MP allocation row; may differ from a work implementation state. No geographic breach inferred.',
 'allocated_raw':'Unmodified ALLOCATED_AMT string, including floating-point export residues.',
 'allocated_paise':'Allocation-limit snapshot converted to integer paise. Only residues <= INR 0.000001 from nearest paise rounded half-up, each logged. Not yearly entitlement, available balance or cash.',
 'consented_paise':'Sum of source 02 consent amounts once per MP term. Not expenditure and not assigned to individual works.',
 'recommended_paise':'Sum of observed recommended amounts once per namespaced work key in this group. An empty MP group means zero observed amount, not complete historical coverage.',
 'sanction_paise':'Sum of sanctioned-export amounts once per work key in this group. Not payment or certified expenditure.',
 'work_count':'Number of unique work entities in the indicated grouping; payment groups count only works with observed payment rows.',
 'recommended_record_count':'Works in group present in recommendation source 03, including separate FLAG=2 records.',
 'sanctioned_count':'Works in group present in sanctioned source 04.',
 'completed_count':'Works in group present in completed source 05.',
 'screened_work_count':'Works with one or more investigation screens. Not confirmed irregularities.',
 'open_over_one_year_count':'Count with open_over_one_year_flag in this group.',
 'no_success_three_months_count':'Count with no_success_three_months_flag in this group.',
 'open_after_demission_18m_count':'Count with open_after_demission_18m_flag in this group. Requires actual demission verification.',
 'recommendation_to_allocation_ratio':'Observed recommended amount divided by allocation-limit snapshot. Null for zero/missing allocation. Portal recommendation use differs from cash expenditure.',
 'sanction_to_allocation_ratio':'Observed sanctioned amount divided by allocation-limit snapshot, not annual spending. Null for zero/missing allocation.',
 'observed_paid_to_allocation_ratio':'Observed successful payment sum divided by allocation-limit snapshot. Coverage differs across cohorts. Not certified cash utilization or current balance.',
 'completion_to_sanction_ratio':'Completed-export work count divided by sanctioned-export count for this grouping. Null when denominator zero. Cross-sectional, not a cohort survival rate.',
 'vendor_id':'Exact supplied VENDOR_ID, retained as text. Vendor names are not used to merge IDs.',
 'vendor_name':'Supplied vendor name. Vendor aggregate displays the first source name; name_variant_count and raw records retain ambiguity.',
 'name_variant_count':'Distinct reported names attached to this VENDOR_ID. No legal-entity verification performed.',
 'same_name_vendor_id_count':'Number of distinct vendor IDs with the exact displayed vendor name. Identical names are not automatically merged.',
 'mp_count':'Distinct MP-term keys with observed payment rows for this vendor, not a count of distinct people across terms.',
 'ida_count':'Distinct normalized state/IDA keys with observed payment rows for this vendor.',
 'ia_name':'Original implementing agency name. No stable agency or ownership ID supplied.',
 'payment_status':'Original WORK_STATUS: Payment Success or Payment In-Progress. Only success enters observed expenditure.',
 'payment_work_id_raw':'Original expenditure WORK_ID string. It has a different format from the completed-source secondary WORK_ID and is not the join key.',
 'report_fingerprint':'Full SHA-256 of JSON array of all original expenditure fields sorted by column name, excluding Sno. Excludes derived fields and provenance. Identical content is not a proven duplicate transaction.',
 'same_fingerprint_count':'Number of expenditure rows with identical report content. Every accepted row remains in the main ledger.',
 'fingerprint_first_row':'True on the first input-order member of a report fingerprint. Used only for sensitivity calculations.',
 'repeat_excess_row':'True on identical report content after the first member. No transaction was deleted.',
 'repeat_excess_rows':'Count of repeat_excess_row in this vendor group.',
 'payment_date':'EXPENDITURE_DATE parsed as calendar date. Record creation and bank settlement timestamps are not supplied.',
 'amount_paise':'FUND_DISBURSED_AMT converted exactly to integer paise, regardless of payment status.',
 'is_success':'True only when source WORK_STATUS equals Payment Success.',
 'successful_paise':'Original amount_paise on Payment Success rows, otherwise zero.',
 'pending_paise':'Original amount_paise on Payment In-Progress rows, otherwise zero. Not settled expenditure.',
 'fingerprint_sensitivity_paise':'successful_paise on first fingerprint member, otherwise zero. Alternative scenario, not a corrected payment value.',
 'payment_after_completion_flag':'Payment report date later than reported completion. Retention or final settlement may be legitimate.',
 'fiscal_year':'Indian financial year April to March derived from the table event date (payment or consent), formatted YYYY-YYYY.',
 'payment_month':'Calendar year-month of expenditure date, YYYY-MM. Across different rows, distinct work counts are not additive over months.',
 'march_payment_flag':'Expenditure date month is March. Context for year-end patterns, not automatic misuse.',
 'round_10000_inr_flag':'Payment amount is exactly divisible by INR 10,000. Descriptive pattern only; round budget amounts are common.',
 'vendor_hhi':'Sum of squared vendor shares of successful payment amounts within IDA and financial year. Range 0-1. Concentration of payments, not tender wins or proof of collusion.',
 'top_vendor_share':'Largest single vendor share of observed successful payment amounts within IDA and financial year.',
 'calamity_name':'Original CALAMITY_NAME from consent source 02.',
 'calamity_type':'Original TYPE in consent source 02, without inferred event severity.',
 'consent_date':'CRT_DT from consent source 02 parsed as a calendar date.',
 'consent_amount_paise':'CONSENTED_AMOUNT in exact integer paise. Consent, not transfer or work expenditure.',
 'work_link_available':'False: consent exports contain no link assigning these amounts to a particular work.',
 'pair_id':'Stable SHA-256 prefix of the sorted pair of namespaced work keys.',
 'work_id_a':'One endpoint of the candidate pair; foreign key to Work_Features.work_id.',
 'work_id_b':'Other endpoint of the candidate pair; distinct from work_id_a.',
 'similarity':'Inverse-frequency-weighted token Jaccard similarity, or 1 for equal nonempty normalized text. Not geospatial or semantic embedding similarity.',
 'same_amount':'Both works have known and equal sanctioned amounts in integer paise.',
 'number_conflict':'Both descriptions contain numbers and their number-token sets differ. Signals a possible distinct location, quantity or phase.',
 'generic_text':'Either description has fewer than four non-stopword tokens; weaker evidence.',
 'continuation_cue':'Either description mentions a phase, repair, continuation, part, renovation or extension.',
 'high_similarity_review':'Similarity >=0.96 with equal known sanction, no numeric conflict, generic text or continuation cue. Review candidate only.',
 'signal':'Name of the active boolean work-screening feature.',
 'family':'Investigation theme of the signal: Delay, Payment, Financial, Cost or Duplicate candidate.',
 'reason':'Plain-language description of the triggered screen. Not an adjudicated finding.',
 'verification_needed':'Specific evidence needed to accept or dismiss the screen.',
 'kind':'Source role: allocations, consents, recommended, sanctioned, completed or payments.',
 'sha256':'SHA-256 digest of the exact original CSV bytes, used for source locking and unchanged-input verification.',
 'source_rows':'Number of CSV data records excluding header, including quarantined records.',
 'accepted_rows':'Source records used by the preparation after required-field validation.',
 'quarantined_rows':'Records retained separately because required fields are absent. Never silently imputed or discarded.',
 'column_count':'Number of original columns in the source CSV.',
 'field':'Name of original field being profiled, compared or normalized.',
 'missing_rows':'Records with empty-string or literal NA in this original field. Zero values are not missing.',
 'distinct_values':'Distinct nonmissing original string values for this source field.',
 'preferred_source_id':'Sanction-source row retained for the chosen master value.',
 'other_source_id':'Recommendation or completion row carrying a different reported value.',
 'preferred_value':'Original value retained from the sanction source for this comparison.',
 'other_value':'Differing original value from the other source, preserved for review.',
 'quarantine_reason':'Reason the original row is not admitted to the analytical fact table.',
 'original_value':'Unmodified source value before an explicitly logged normalization.',
 'prepared_paise':'Normalized exact integer-paise value.',
 'adjustment_inr':'Exact decimal prepared-minus-original difference in INR, written as text to preserve tiny residues.',
}

GRAINS={
 'Feature_Dictionary':'one prepared table and field',
 'Validation_Checks':'one executed pipeline check',
 'Work_Features':'one namespaced work/recommendation entity',
 'Payment_Features':'one accepted expenditure report record',
 'MP_Term_Features':'one supplied MP parliamentary term allocation record',
 'IDA_Features':'one normalized state and implementing district authority',
 'Cohort_Summary':'one source-folder cohort',
 'Vendor_Features':'one exact vendor ID',
 'Vendor_Connections':'one vendor, MP term, IDA, agency name and payment financial year',
 'IDA_Year_Concentration':'one IDA and payment financial year',
 'Monthly_Payments':'one cohort, state, payment financial year and month',
 'Calamity_Consents':'one consent report record',
 'Work_Signals':'one work and active screen',
 'Duplicate_Candidates':'one retained work pair',
 'Source_Audit':'one original CSV file',
 'Source_Column_Profile':'one original file and field',
 'Field_Conflicts':'one compared work, field and pair of sources',
 'Quarantine':'one excluded but preserved source row',
 'Normalization_Log':'one corrected numeric-export residue',
}

TABLE_DEFINITIONS={
 ('MP_Term_Features','mp_name'):'Original MP_NAME from allocation source 01; honourifics and tenure suffixes are retained for display.',
 ('MP_Term_Features','tenure'):'Original TENURE text from allocation source 01. Sitting MP is not a reliable retirement-status label.',
 ('MP_Term_Features','constituency'):'Original CONSTITUENCY from allocation source 01. Generic Rajya Sabha labels are not geographic jurisdiction codes.',
 ('IDA_Year_Concentration','vendor_count'):'Distinct vendor IDs with observed Payment Success rows in this IDA and financial year.',
 ('Vendor_Features','first_payment_date'):'Earliest observed expenditure date, any status, for this exact vendor ID.',
 ('Vendor_Features','last_payment_date'):'Latest observed expenditure date, any status, for this exact vendor ID.',
 ('Normalization_Log','reason'):'Why the specific source numeric residue was rounded; original and exact adjustment retained.',
 ('Feature_Dictionary','field'):'Column name in the documented prepared table.',
}

def dictionary(tables,engineered):
    rows=[]
    all_tables={**tables,'Feature_Dictionary':pd.DataFrame(columns=['table','grain','field','dtype','unit','definition','source','availability','model_use'])}
    for table,df in all_tables.items():
        for c in df:
            if (table,c) in TABLE_DEFINITIONS:desc,src,timing=TABLE_DEFINITIONS[table,c],'See source IDs and table grain','Snapshot descriptive'
            elif c in DEFINITIONS:desc,src,timing=DEFINITIONS[c],'See source IDs, table grain and definition','Snapshot descriptive'
            elif c in engineered:desc,src,timing=engineered[c]
            elif c.isupper() or c=='Sno':desc,src,timing=f'Original source field {c}, preserved verbatim; no inferred meaning assigned to opaque codes.','Original CSV; source_id','Raw snapshot'
            else:raise ValueError(f'Undocumented field {table}.{c}')
            if c.endswith('_paise') or c=='prepared_paise':unit='integer paise (100 = INR 1)'
            elif c in ['vendor_hhi','similarity','duplicate_similarity','top_vendor_share','march_payment_share']:unit='ratio, 0 to 1'
            elif c.endswith(('_ratio','_share')):unit='ratio; may exceed 1 when numerator exceeds denominator'
            elif c.endswith('_days'):unit='calendar days'
            elif c.endswith(('_date','_fy')) or c in ['fiscal_year','payment_month']:unit='ISO date or labelled period'
            elif c.endswith(('_count','_rows')):unit='count'
            elif df[c].dtype==bool:unit='boolean'
            else:unit='see definition'
            usage='Investigative context, not a prediction label'
            if table=='Work_Features' and c in ['activity_type','state','house','sanction_amount_paise','recommended_amount_paise','sanction_delay_days','mp_strict_prior_sanction_count','ida_strict_prior_sanction_count','log_sanction_inr','cost_peer_log_z','cost_peer_ratio']:
                usage='Candidate sanction-time input; verify knowledge timestamps and fit preprocessing on training data only'
            elif 'completion' in c or 'payment' in c or 'success' in c or 'screen' in c or c.endswith('_flag'):
                usage='Snapshot evidence; exclude from earlier-time predictions unless reconstructable at that time'
            rows.append(dict(table=table,grain=GRAINS[table],field=c,dtype=str(df[c].dtype),unit=unit,definition=desc,source=src,availability=timing,model_use=usage))
    return pd.DataFrame(rows)

LIMITS=[
 ('Fraud labels','No confirmed fraud, audit outcomes or investigation labels supplied. Screens are review candidates; no real-world accuracy or A/B superiority is claimed.'),
 ('Completeness','All 18 supplied files are included. This does not establish full national or historical coverage. Lok Sabha payments start later than Rajya Sabha payments.'),
 ('Identifier collisions','FLAG=2 recommendations reuse some numeric IDs belonging to unrelated main-work records. Namespace these rows; never join on the numeric ID alone.'),
 ('Money and allocation','Allocation is a term-selection snapshot, not yearly cash. Pending requests are separate from Payment Success. Consent is not work expenditure.'),
 ('Payment repetition','No transaction, invoice, bank reference or revision ID. Repeated report rows remain. One-fingerprint sensitivity is not corrected expenditure.'),
 ('Timelines','Recommendation substitutes for unavailable IDA receipt date. One-year and term-end+18-month checks need sanction exceptions and verified demission dates.'),
 ('Costs','No quantity, dimension, unit price, bill of quantities or approved change orders. Peer checks compare category amounts, not like-for-like unit costs.'),
 ('Duplicates and assets','No coordinates or verified asset photos. Text matching is bounded and non-exhaustive. Attachment IDs cannot establish physical asset existence.'),
 ('Compliance','No work beneficiary SC/ST tags, trust/society classification, effective trust rules or authoritative jurisdiction mapping. These compliance screens are disabled.'),
 ('Predictive use','Completion, payment totals and snapshot flags leak future information into recommendation/sanction-time prediction. Prior-year benchmarks still lack historical knowledge timestamps.'),
 ('Local handling','No source data uploaded or published. Machine-readable CSV preserves text; import IDs as Text. The Excel review escapes formula-like text and is a labelled subset.'),
]

def create_review_data(t,m):
    from common import to_records
    from prepare import SIGNALS
    w=t['Work_Features']
    source=t['Source_Audit'].drop(columns=['sha256'])
    summary=t['Cohort_Summary'][['cohort','work_count','recommended_record_count','sanctioned_count','completed_count','successful_payment_paise','pending_payment_paise']].copy()
    for c in ['successful_payment_paise','pending_payment_paise']:summary[c.replace('_paise','_inr')]=summary.pop(c)/100
    rules=[]
    for c,(family,label,caution) in SIGNALS.items():rules.append(dict(signal=label,works=int(w[c].sum()),interpretation=caution))
    mp=t['MP_Term_Features'][['mp_key','cohort','mp_name','allocation_state','tenure_start_date','tenure_end_date','allocated_paise','work_count','sanctioned_count','completed_count','successful_payment_paise','pending_payment_paise','open_over_one_year_count']].copy()
    for c in ['allocated_paise','successful_payment_paise','pending_payment_paise']:mp[c.replace('_paise','_inr')]=mp.pop(c)/100
    priority=w.loc[w.screening_signal_count.gt(0)].sort_values(['screening_signal_count','sanction_amount_paise','work_id'],ascending=[False,False,True]).head(1000)[['work_id','cohort','mp_name','state','activity_type','sanction_amount_paise','successful_payment_paise','screening_signal_count','screening_reasons']].copy()
    for c in ['sanction_amount_paise','successful_payment_paise']:priority[c.replace('_paise','_inr')]=priority.pop(c)/100
    overview=[['Assessment date',m['as_of']],['Original CSV files',18],['Original source records',int(source.source_rows.sum())],['Prepared work entities',len(w)],['Accepted payment records',len(t['Payment_Features'])],['MP term records',len(mp)],['Quarantined rows',len(t['Quarantine'])],['Logged allocation rounding adjustments',len(t['Normalization_Log'])],['Works with at least one screen',int(w.screening_signal_count.gt(0).sum())],['Confirmed fraud labels supplied',0]]
    return dict(overview=overview,cohorts=to_records(summary),sources=to_records(source),signals=rules,mp_terms=to_records(mp),review_sample=to_records(priority),dictionary=to_records(t['Feature_Dictionary'][['table','field','unit','definition','model_use']]),limits=[dict(topic=a,limitation=b) for a,b in LIMITS],checks_passed=len(m['checks']))

def write_report(out,t,m):
    w=t['Work_Features'];p=t['Payment_Features'];from prepare import SIGNALS
    rows=['# MPLADS PS 26102: prepared dataset report','',f'Version: {VERSION}. Assessment date: {m["as_of"]}.','',
        f'Included all 18 supplied CSVs: {int(t["Source_Audit"].source_rows.sum()):,} original data records. Prepared {len(w):,} work entities, {len(p):,} accepted payment records, {len(t["MP_Term_Features"]):,} MP terms and {len(t["Vendor_Features"]):,} vendor IDs. Original records also remain in SQLite Raw_* tables.','',
        '## Important findings','',
        'Numeric recommendation IDs are not globally safe: 278 IDs identify both a FLAG=1 and an unrelated FLAG=2 recommendation. FLAG=2 business meaning is not assumed. All 1,205 FLAG=2 rows are retained as separate entities. MP identity includes exact tenure dates; Sitting MP is not a retirement-status field.','',
        f'{len(t["Quarantine"]):,} incomplete expenditure row is quarantined. {len(t["Normalization_Log"]):,} allocation values have sub-micro-rupee decimal-export residues; exact source values and rounding deltas are retained. {int(p.repeat_excess_row.sum()):,} payment report rows repeat earlier content excluding serial number. All remain in the main payment table.','',
        f'Reported Payment Success total: INR {int(p.successful_paise.sum())/100:,.2f}. In-progress requests: INR {int(p.pending_paise.sum())/100:,.2f}. One-fingerprint-only success sensitivity: INR {int(p.fingerprint_sensitivity_paise.sum())/100:,.2f}; this is not an adjudicated correction.','',
        f'One work has a positive payment-minus-sanction difference of INR 0.10. The material reconciliation screens use an explicitly chosen INR 1 tolerance, not a government threshold. The exact delta and small-difference flag remain visible; no material paid-over-sanction case is implied by this ten-paise difference.','',
        '## Investigation screens','', '| Screen | Work count | Required interpretation |','|---|---:|---|']
    for c,(_,label,caution) in SIGNALS.items():rows.append(f'| {label} | {int(w[c].sum()):,} | {caution} |')
    rows += ['', 'Screen counts overlap. An unweighted count helps organise review but is not a calibrated risk score. Data-quality checks remain separate.', '', '## Delivered tables', '', '| Table | Rows | Grain |','|---|---:|---|']
    for name,frame in t.items():rows.append(f'| {name} | {len(frame):,} | {GRAINS.get(name,"Dictionary or validation record")} |')
    rows += ['', '## Interpretation limits','']
    for topic,limit in LIMITS:rows.append(f'- {topic}: {limit}')
    rows += ['', '## Verification','', f'{len(m["checks"])} checks passed, including locked source hashes, safe key uniqueness, joined identity agreement, exact paise financial reconciliation across seven aggregations, SQLite integrity and unchanged raw files. CSV hashes in manifest.json support an independent rebuild. Workbook verification is recorded separately.', '',
        'All joins are many-to-one or one-to-one. Payment aggregation precedes joining to works. Allocation/consent amounts are not copied to every work and then summed. A work without observed payment has zero observed amount and an explicit coverage flag; payment-to-sanction ratios remain unavailable when there is no success evidence.', '',
        'The recommendation/sanction source governs work identity; the sanction export alone establishes sanctioned amount; completion export establishes reported completion. Every source disagreement retained in Field_Conflicts identifies both original records. Raw_* tables retain fields not selected into the master.', '',
        '## Research used','',
        'Official monitoring definitions support receipt-based 45-day decisions, a general one-year completion period and completion within 18 months of demitting office. We implement documented proxies where evidence is missing. [MoSPI, eSAKSHI Portal, 6 August 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2153066&lang=2&reg=48).','',
        'The official dashboard distinguishes recommendations, sanctions, completions and released vendor payments. Different stakeholders update different stages. Pre-2023 work coverage is limited; legacy dates in this extract are preserved, not treated as comprehensive historical coverage. [MoSPI, revamped dashboard, 6 March 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2235932&lang=1&reg=3).','',
        'The supplied context file is background, not an executable rulebook. Its unverified trust ceiling and universal beneficiary/geography checks are not activated. No synthetic data is mixed with the real prepared tables.', '',
        '## Feature and model design','',
        'Prior-year cost peers: state plus activity with at least 20 prior-financial-year sanctioned works; activity-only fallback. Log(1+INR) median/MAD with scale max(1.4826*MAD, 0.1). High cost requires z>3.5 and amount/peer median>=2. Specifications and quantities are unavailable. Same-year and later records do not define a work\'s benchmark.', '',
        'Text candidates: Unicode normalization, stopwords, inverse-frequency weighted token overlap, same IDA/activity block, three rare-token anchors, last 150 postings per anchor, at most 60 candidates per work and three retained matches >=0.88. This is a bounded snapshot search, not proven duplicate-asset detection. Exact parameters and cap hits appear in manifest.json.', '',
        'No supervised label or held-out A/B result is manufactured. Before model evaluation, obtain adjudicated outcomes, define a prediction/knowledge cutoff, reconstruct time-valid features, separate train/calibration/test and fit all preprocessing on training data. Current completion/payment/flags are investigation-time features, not valid earlier-time predictors.', '',
        'The Excel summary contains all MP-term summaries, all field definitions and a top-1,000 screened-work review extract. Use Work_Features.csv and mplads_prepared.sqlite3 for the full population.', '']
    (out/'DATA_REPORT.md').write_text('\n'.join(rows),encoding='utf-8',newline='\n')
