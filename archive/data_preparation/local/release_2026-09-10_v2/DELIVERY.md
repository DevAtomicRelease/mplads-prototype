# PS 26102 dataset handoff

All 18 supplied datasets have been prepared locally. Assessment date: 10 September 2026. This release supersedes earlier three-source, six-source and diagnostic builds.

## Files to use

| File | Contents |
|---|---|
| `Work_Features.csv` | Full work-level dataset: **160,701 rows, 119 fields**. Namespaced IDs prevent false joins. |
| `Payment_Features.csv` | All **113,691 accepted payment report rows**. Success and in-progress amounts are separate. |
| `mplads_prepared.sqlite3` | All 19 prepared tables and 18 original-source tables. Approximately 549 MB. |
| `MP_Term_Features.csv` | **1,023 parliamentary terms** with allocation, recommendations, payments, completion and delay summaries. |
| `Vendor_Features.csv` | **34,242 vendor IDs**, with payment counts, amounts and entity connections. |
| `Feature_Dictionary.csv` | **332 field definitions**, including units, table grain, sources and prediction-time cautions. |
| `DATA_REPORT.md` | Findings, feature methods, primary research citations and data limitations. |
| `manifest.json` | Locked input hashes, code hashes, output counts, CSV hashes and search parameters. |
| `independent_verification.json` | Independent checks and exact rebuild comparison. |

The plain Excel review is at `../../../outputs/ps26102-all-cohorts-20260910/MPLADS_Data_Review.xlsx`. It contains all MP-term summaries, all definitions and a **labelled 1,000-work sample**. It is not a substitute for the full CSV/database population.

## What was checked

- **17 unit tests passed**: key collisions, term separation, currency precision, missing versus zero, fiscal/calendar boundaries and historical peer exclusion.
- **116 pipeline checks passed**: source contracts, join cardinalities, identity agreement, exact-paise reconciliations, record conservation and database integrity.
- **185 independent/rebuild checks passed**: an independent CSV reader verifies the financial controls, original SQLite field strings, output schemas, arithmetic and key relationships. All **19 CSV files reproduce byte-for-byte** in a second build.
- **43 saved-workbook checks passed**, comparing **24,178 data cells** against the prepared data. Dates and currency are typed, filters and frozen identifiers are saved, formula totals recalculate, and no saved formula errors were found.
- All six workbook sheets were visually reviewed, including long definitions, repeated MP names in different terms, monetary headings and explanatory notes. Native Excel UI was not tested.

Raw CSV hashes were checked again after building. Original files remain unchanged. No data was uploaded, published, committed or pushed during this preparation. New data and outputs are excluded from Git. Older user-deleted workbook files and unrelated prototype edits were left alone.

## Important interpretation

There are **278 numeric-ID collisions** between unrelated FLAG=1 and FLAG=2 recommendations. Use `work_id`, never the raw numeric ID alone. All 1,205 FLAG=2 rows remain, without guessing their business meaning. Member keys identify terms, not lifetime persons.

One malformed payment row is quarantined, 15 tiny allocation-export rounding residues are logged, and all 1,795 repeated payment-report rows are preserved. Transaction duplication cannot be established without transaction IDs. The only positive observed payment/sanction difference is INR 0.10; it is retained as a small reconciliation difference rather than a material overrun.

Features support delays, payment reconciliation, historical cost comparisons, similar-work investigation, vendor concentration and retired-term follow-up. These are **screening signals, not confirmed fraud or legal findings**. Missing receipt dates, sanction exceptions, actual demission evidence, bills of quantities, bank references, beneficiary tags, asset coordinates and photos limit what can be concluded. Zero observed payments does not prove zero real expenditure.

## Remaining project work

Dataset preparation is complete; the existing prototype and A/B experiment have not yet been updated to this release.

1. Adapt the local read-only API to `mplads_prepared.sqlite3`. Treat all work and MP-term keys as strings. Add cohort/term filters, payment-status separation, dictionary help and record-level provenance. The older six-source app expects a different schema and should not be pointed at this database without an adapter and tests.
2. Let investigators inspect source disagreements, repeated-payment scenarios, cost peers and text-pair evidence. Store their decisions in a separate review database with work key, reviewer, decision date and evidence references. Do not alter prepared facts or equate a triggered screen with an adjudicated outcome.
3. Predeclare a baseline and enhanced detection method with equal review budgets. Use independent adjudicated labels for real-world precision and false-positive estimates. Separate calibration and test sets by entity/time and prevent future-event leakage. Controlled synthetic injections must be kept separate from real records and reported as mechanism tests, not real-world fraud accuracy.

No real-data A/B superiority, predictive model accuracy or completed prototype integration is claimed in this handoff.
