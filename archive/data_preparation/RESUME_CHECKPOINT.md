# PS 26102 continuation checkpoint

## Completed handoff status

The dataset-preparation task is now complete. Use `local/release_2026-09-10_v2/`, not either earlier build. The second build in `reproduced/` produced byte-identical copies of all 19 CSVs. Passed 17 unit tests, 116 pipeline checks, 185 independent/rebuild checks and 43 saved-XLSX checks (24,178 compared data cells). Six workbook sheets and additional long-text, financial-header and term-boundary views were visually checked.

Final workbook: `outputs/ps26102-all-cohorts-20260910/MPLADS_Data_Review.xlsx`. Full work table: 160,701 rows and 119 fields. Full payment table: 113,691 rows. Dictionary: 332 definitions covering all prepared table schemas. All 18 raw CSV files remain unchanged; their original strings also match the SQLite Raw_* tables. No new data was published or pushed.

See `local/release_2026-09-10_v2/DELIVERY.md`. Remaining **project** work (not claimed complete): connect the existing prototype to this schema, collect adjudicated review outcomes and run an honest baseline/enhanced evaluation. Do not restart dataset preparation unless the sources change. The text below records the previous checkpoint for traceability.

## Previous checkpoint before final verification

Active request: prepare all 18 supplied CSVs against the problem statement. Raw data must remain unchanged and local. No current authorization to publish the new data. Existing prototype updates and A/B validation are not yet complete and must not be claimed as delivered.

Earlier complete build: `local/final_2026-09-10/` has 160,701 work entities (119 fields), 113,691 accepted payments, 1,023 MP terms, 34,242 vendors and 33 consents. It passed 116 pipeline checks and 17 unit tests. A later independent-checker edit invalidated its code manifest, so it is superseded rather than silently overwritten.

Current target: `local/release_2026-09-10_v2/`. Code has been updated to finish the dictionary (including its own schema and validation checks), check raw SQLite string fidelity and add independent arithmetic checks. Freeze all Python files before running two builds. Use `reproduced/` for the second run, then `verify.py --compare-dir` to require matching CSV hashes. Full independent verification and rebuild comparison are still pending at this checkpoint.

Critical findings: numeric IDs collide between 278 unrelated FLAG=1/FLAG=2 records. All 1,205 FLAG=2 recommendations stay separate using `rec2:<cohort>:<id>`. MP identity includes house and term dates, because retired files also say Sitting MP. One truncated payment row is quarantined, 15 tiny allocation decimal residues logged, all 1,795 repeated payment report rows retained. One positive payment/sanction difference is INR 0.10, below the explicit INR 1 investigation tolerance. Screens are not confirmed fraud.

Workbook builder: `workbook/build_review.mjs`, planned output `outputs/ps26102-all-cohorts-20260910/MPLADS_Data_Review.xlsx`. It has not run. The spreadsheet artifact-operation marker has not run. Before authoring, use the required marker once, a local node_modules junction to bundled packages, then create, recalculate, inspect and visually check all six sheets. Workbook has all MP terms and dictionary entries but only a clearly labelled 1,000-work sample; full data is CSV/SQLite.

Remaining: fresh release build; all independent and unit checks; second build with byte-identical CSVs; Excel creation and all-sheet visual/saved-file checks; final documentation and raw-hash/Git-ignore check; concise handoff. Continue in this task, not a new task. Do not restore the user-deleted old XLSX source files, touch unrelated unfinished prototype code, or push.

Runtime: use bundled Python and Node under `C:/Users/lenovo/.cache/codex-runtimes/codex-primary-runtime/dependencies/`. Spreadsheet skill is `C:/Users/lenovo/.codex/plugins/cache/openai-primary-runtime/spreadsheets/26.909.12148/skills/spreadsheets/` (fully read earlier). Use apply_patch for authored changes and approved escalation for generated local files. The previous attempt to save a checkpoint hit a usage-limit rejection; this file is the first successfully persisted checkpoint.
