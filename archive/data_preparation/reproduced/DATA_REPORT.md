# MPLADS PS 26102: prepared dataset report

Version: all-cohorts-2026-09-10-v2. Assessment date: 2026-09-10.

Included all 18 supplied CSVs: 459,965 original data records. Prepared 160,701 work entities, 113,691 accepted payment records, 1,023 MP terms and 34,242 vendor IDs. Original records also remain in SQLite Raw_* tables.

## Important findings

Numeric recommendation IDs are not globally safe: 278 IDs identify both a FLAG=1 and an unrelated FLAG=2 recommendation. FLAG=2 business meaning is not assumed. All 1,205 FLAG=2 rows are retained as separate entities. MP identity includes exact tenure dates; Sitting MP is not a retirement-status field.

1 incomplete expenditure row is quarantined. 15 allocation values have sub-micro-rupee decimal-export residues; exact source values and rounding deltas are retained. 1,795 payment report rows repeat earlier content excluding serial number. All remain in the main payment table.

Reported Payment Success total: INR 45,925,599,703.04. In-progress requests: INR 1,465,844,341.00. One-fingerprint-only success sensitivity: INR 45,673,022,370.04; this is not an adjudicated correction.

One work has a positive payment-minus-sanction difference of INR 0.10. The material reconciliation screens use an explicitly chosen INR 1 tolerance, not a government threshold. The exact delta and small-difference flag remain visible; no material paid-over-sanction case is implied by this ten-paise difference.

## Investigation screens

| Screen | Work count | Required interpretation |
|---|---:|---|
| Recommendation without sanction beyond 45 days | 24,356 | Confirm receipt, rejection and FLAG=2 meaning. |
| Recommendation-to-sanction exceeds 45 days | 86,264 | IDA receipt date is missing. |
| No completion beyond one calendar year | 18,495 | Check sanction deadline and extensions. |
| No observed success three months after sanction | 39,144 | Obtain full ledger and pending-request status. |
| Open beyond reported term end plus 18 months | 3,030 | Verify actual demission and legacy applicability. |
| Reported successful payments exceed sanction by > INR 1 | 0 | Reconcile transaction IDs and revised sanctions. |
| Reported completion amount exceeds sanction by > INR 1 | 0 | Check revised scope and sanction orders. |
| Repeated payment report content | 528 | No transaction IDs; do not delete as proven duplicates. |
| High amount versus prior-year peers | 4,792 | Category costs are not unit costs; quantities missing. |
| Highly similar descriptions and equal amounts | 6,350 | Verify location, distinct scope and phases. |

Screen counts overlap. An unweighted count helps organise review but is not a calibrated risk score. Data-quality checks remain separate.

## Delivered tables

| Table | Rows | Grain |
|---|---:|---|
| MP_Term_Features | 1,023 | one supplied MP parliamentary term allocation record |
| IDA_Features | 1,045 | one normalized state and implementing district authority |
| Cohort_Summary | 3 | one source-folder cohort |
| Vendor_Features | 34,242 | one exact vendor ID |
| Vendor_Connections | 46,817 | one vendor, MP term, IDA, agency name and payment financial year |
| IDA_Year_Concentration | 2,551 | one IDA and payment financial year |
| Monthly_Payments | 2,215 | one cohort, state, payment financial year and month |
| Calamity_Consents | 33 | one consent report record |
| Work_Features | 160,701 | one namespaced work/recommendation entity |
| Payment_Features | 113,691 | one accepted expenditure report record |
| Work_Signals | 182,959 | one work and active screen |
| Duplicate_Candidates | 37,091 | one retained work pair |
| Source_Audit | 18 | one original CSV file |
| Source_Column_Profile | 306 | one original file and field |
| Field_Conflicts | 27,087 | one compared work, field and pair of sources |
| Quarantine | 1 | one excluded but preserved source row |
| Normalization_Log | 15 | one corrected numeric-export residue |
| Validation_Checks | 116 | one executed pipeline check |
| Feature_Dictionary | 332 | one prepared table and field |

## Interpretation limits

- Fraud labels: No confirmed fraud, audit outcomes or investigation labels supplied. Screens are review candidates; no real-world accuracy or A/B superiority is claimed.
- Completeness: All 18 supplied files are included. This does not establish full national or historical coverage. Lok Sabha payments start later than Rajya Sabha payments.
- Identifier collisions: FLAG=2 recommendations reuse some numeric IDs belonging to unrelated main-work records. Namespace these rows; never join on the numeric ID alone.
- Money and allocation: Allocation is a term-selection snapshot, not yearly cash. Pending requests are separate from Payment Success. Consent is not work expenditure.
- Payment repetition: No transaction, invoice, bank reference or revision ID. Repeated report rows remain. One-fingerprint sensitivity is not corrected expenditure.
- Timelines: Recommendation substitutes for unavailable IDA receipt date. One-year and term-end+18-month checks need sanction exceptions and verified demission dates.
- Costs: No quantity, dimension, unit price, bill of quantities or approved change orders. Peer checks compare category amounts, not like-for-like unit costs.
- Duplicates and assets: No coordinates or verified asset photos. Text matching is bounded and non-exhaustive. Attachment IDs cannot establish physical asset existence.
- Compliance: No work beneficiary SC/ST tags, trust/society classification, effective trust rules or authoritative jurisdiction mapping. These compliance screens are disabled.
- Predictive use: Completion, payment totals and snapshot flags leak future information into recommendation/sanction-time prediction. Prior-year benchmarks still lack historical knowledge timestamps.
- Local handling: No source data uploaded or published. Machine-readable CSV preserves text; import IDs as Text. The Excel review escapes formula-like text and is a labelled subset.

## Verification

116 checks passed, including locked source hashes, safe key uniqueness, joined identity agreement, exact paise financial reconciliation across seven aggregations, SQLite integrity and unchanged raw files. CSV hashes in manifest.json support an independent rebuild. Workbook verification is recorded separately.

All joins are many-to-one or one-to-one. Payment aggregation precedes joining to works. Allocation/consent amounts are not copied to every work and then summed. A work without observed payment has zero observed amount and an explicit coverage flag; payment-to-sanction ratios remain unavailable when there is no success evidence.

The recommendation/sanction source governs work identity; the sanction export alone establishes sanctioned amount; completion export establishes reported completion. Every source disagreement retained in Field_Conflicts identifies both original records. Raw_* tables retain fields not selected into the master.

## Research used

Official monitoring definitions support receipt-based 45-day decisions, a general one-year completion period and completion within 18 months of demitting office. We implement documented proxies where evidence is missing. [MoSPI, eSAKSHI Portal, 6 August 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2153066&lang=2&reg=48).

The official dashboard distinguishes recommendations, sanctions, completions and released vendor payments. Different stakeholders update different stages. Pre-2023 work coverage is limited; legacy dates in this extract are preserved, not treated as comprehensive historical coverage. [MoSPI, revamped dashboard, 6 March 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2235932&lang=1&reg=3).

The supplied context file is background, not an executable rulebook. Its unverified trust ceiling and universal beneficiary/geography checks are not activated. No synthetic data is mixed with the real prepared tables.

## Feature and model design

Prior-year cost peers: state plus activity with at least 20 prior-financial-year sanctioned works; activity-only fallback. Log(1+INR) median/MAD with scale max(1.4826*MAD, 0.1). High cost requires z>3.5 and amount/peer median>=2. Specifications and quantities are unavailable. Same-year and later records do not define a work's benchmark.

Text candidates: Unicode normalization, stopwords, inverse-frequency weighted token overlap, same IDA/activity block, three rare-token anchors, last 150 postings per anchor, at most 60 candidates per work and three retained matches >=0.88. This is a bounded snapshot search, not proven duplicate-asset detection. Exact parameters and cap hits appear in manifest.json.

No supervised label or held-out A/B result is manufactured. Before model evaluation, obtain adjudicated outcomes, define a prediction/knowledge cutoff, reconstruct time-valid features, separate train/calibration/test and fit all preprocessing on training data. Current completion/payment/flags are investigation-time features, not valid earlier-time predictors.

The Excel summary contains all MP-term summaries, all field definitions and a top-1,000 screened-work review extract. Use Work_Features.csv and mplads_prepared.sqlite3 for the full population.
