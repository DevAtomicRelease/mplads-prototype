# PS 26102: restart with six source exports

## Objective

Build a local, reproducible investigation system joining recommendations, sanctions, completion records, vendor payments, MP allocations and calamity consents. Detect explainable financial exceptions, execution bottlenecks and duplicate candidates; help an officer inspect evidence and record follow-up. No score constitutes fraud evidence or a legal finding.

## Ordered delivery plan

1. Read the problem statement and context; research current official scheme definitions and monitoring practices. Record source dates, implementation implications and unsupported assumptions.
2. Inventory and hash all six original CSVs. Profile schema, null tokens, duplicate keys, dates, amounts, status meaning and coverage. Quarantine invalid records without altering source files.
3. Establish data contracts and cardinalities. Use the union of recommendation/sanction work IDs, not an inner join. Join completion one-to-one. Aggregate expenditure rows before joining to a work. Join MP allocations many-to-one using checked normalized names plus tenure/house. Keep calamity consents as MP-level context.
4. Engineer traceable work, transaction, vendor, MP, authority, month and duplicate-candidate features. Preserve raw source fields, row provenance, missingness and unsupported checks. Distinguish successful from in-progress payments and report repeat-row sensitivity without asserting which rows are duplicates.
5. Implement separate data-quality checks, researched monitoring rules, cost/text/graph screening and a reproducible unsupervised anomaly model. Explain every queue contribution. Keep unavailable compliance and asset-verification capabilities visibly unavailable.
6. Compare fixed baseline and enhanced methods offline at equal review budgets. Freeze rules/seeds, keep controlled injections separate from real data, record actual queue overlap, per-scenario trade-offs and uncertainty. Do not claim fraud accuracy or a live randomized A/B test. Independently rerun and compare outputs.
7. Build a local investigation workspace with server-side filtering/pagination for the larger data, financial and lifecycle evidence, payment ledger, vendor/MP/authority views, exports, local review history and validation results. Preserve the older three-source implementation.
8. Deliver full machine-readable datasets plus a plain Excel review workbook, research/architecture/rollout documentation, launch/rebuild controls and automated integrity, financial, model, service and build checks. Keep all new source records and generated outputs local unless explicitly authorized for publication.

## Initial observations (read-only audit, 9 September 2026)

| Source | Rows | Grain / handling |
|---|---:|---|
| Allocated limit | 543 | MP, house and tenure; one explicit zero, not a missing amount |
| Calamity consent | 12 | Consent record; no work-level funding link |
| Recommended works | 107,562 | Unique work recommendation ID |
| Sanctioned works | 79,881 | Unique work recommendation ID; 375 absent from recommendation export |
| Completed works | 34,940 | Unique work recommendation ID; all match sanctions |
| Expenditure | 57,349 | Report row, not verified transaction ID; one incomplete row requires quarantine |

The valid union contains 107,937 works. The four work-related files are not disjoint datasets or a synchronized event log. The recommendation file's `SANCTION_AMOUNT` is populated on unsanctioned rows; only membership in the sanction export establishes observed sanction. Its 28,056 `NA` sanction dates are missing values, not parseable dates. Status labels differ between exports and physical inspection appears on 30,969 completed records.

Successful payment rows total INR 17,509,756,810.43; in-progress rows total INR 966,143,799.00 and must not be added to settled expenditure. There are 753 excess identical expenditure-report fingerprints after excluding `Sno`, affecting 301 works. Distinct vendor IDs must remain distinct even when names match. No valid work currently has reported successful payments or completion actual amount above its sanction; zero detected exceptions is a legitimate result.

The exports cover the 18th Lok Sabha, not all historical MPLADS or all chambers. An incomplete expenditure row and cross-export membership differences prevent a claim of verified full national completeness. Source extraction timestamps, receipt dates, contractual due dates, transaction/invoice IDs, revised sanctions, tax/retention breakdowns, beneficiary-area tags, trust registration IDs and asset photos are still absent.

## Design decisions to preserve

- Snapshot reference date: 2026-09-09, explicitly recorded; not an invented historic observation timestamp.
- Source data are immutable. New outputs live under `six_source/local/`, not the old published artifacts.
- The UI processes records locally through a loopback service; it does not send data to an external language model or cloud service.
- No attribution of liability to MPs, vendors or authorities based on an anomaly flag. Every alert requests evidence and review.
- A/B comparisons are offline screening experiments; prospective officer randomization and independently adjudicated outcomes remain rollout gates.
