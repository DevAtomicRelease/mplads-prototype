# MPLADS PS 26102: all-cohort data preparation

This pipeline reads **all 18 CSV files** in `Dataset/Lok Sabha`, `Dataset/Rajya_Sabha_retired` and `Dataset/Rajya_Sabha_sitting`. It replaces the earlier three- and six-source *data assumptions*. It does not overwrite those earlier outputs or change the existing prototype.

The current prepared release is `local/release_2026-09-10_v2/`. Start with `DATA_REPORT.md`, then `Work_Features.csv` and `Feature_Dictionary.csv`. The complete database is `mplads_prepared.sqlite3`. Data and generated outputs are ignored by Git and remain on this computer. The earlier `local/prepared_2026-09-10/` and `local/final_2026-09-10/` builds are retained for traceability but are superseded.

## Reproduce

Use Python 3.12 with pandas 3.0.1 and NumPy 2.3.5 (exact running versions are recorded in the manifest). The bundled desktop Python can run this without installing new packages:

```powershell
& 'C:\Users\lenovo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\data_preparation\test_preparation.py
& 'C:\Users\lenovo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\data_preparation\prepare.py --output-dir .\data_preparation\reproduced
& 'C:\Users\lenovo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\data_preparation\verify.py --compare-dir .\data_preparation\reproduced
```

Run from the PPS_1 project directory. An ordinary Python installation with the recorded dependency versions can substitute for the bundled executable. Complete output directories are protected against accidental overwrite. Use a new output directory for another build.

`contracts.py` locks the reviewed 18 sources by row count and SHA-256. If files change, first run `profile_sources.py`, inspect schema/coverage/key/amount differences, then deliberately version the contract. Do not bypass a failed contract check. `--as-of` is the fixed assessment date, **not** an event-time reconstruction mechanism: do not backdate it for predictive training.

## Safe joins

- `Work_Features.work_id`: use the **namespaced key**, never the raw numeric detail ID alone. `FLAG=2` recommendations have an independently colliding ID namespace. Their actual business status remains unverified.
- `Payment_Features.work_id` and `Duplicate_Candidates.work_id_a/work_id_b` link to the master.
- `MP_Term_Features.mp_key` includes house, normalized name and exact supplied term dates. A single person in two parliamentary terms stays separate. This is not a universal person ID.
- Allocation and consent stay at MP-term grain. Do not repeat or sum allocation at work/payment grain.
- Payments are aggregated before joining to works. Retain all report rows; transaction-level deduplication cannot be established without transaction IDs.
- `Raw_*` SQLite tables preserve original strings and source ordinals, including fields omitted from the master and the quarantined record. `Field_Conflicts` and `Normalization_Log` explain changes and disagreements.

All currency columns ending `_paise` are integers (100 paise = INR 1). CSV dates are ISO. Empty values are unavailable, not zero. Observed payment sums may be zero with explicit coverage flags; this is not certified absence of expenditure. Read identifiers as strings. Machine-readable CSVs retain source text, so import text columns explicitly rather than allowing spreadsheet formula interpretation.

## Feature use

The feature dictionary maps every prepared field to its grain, unit, definition, source and timing caveat. The selected features support PS 26102's delay, payment, cost, duplicate-work and vendor-investigation needs. Post-event outcomes and full-snapshot features must not be used as earlier-time predictors. No fabricated fraud labels, bank-confirmed expenditure, ghost-asset claims or real-data A/B scores are produced.

The plain Excel review contains all MP-term summaries, all field definitions and a labelled 1,000-work review extract. The CSV/database includes the entire population. Workbook creation uses the bundled spreadsheet runtime; its author and checks are in `workbook/`, with the final file under the project `outputs` directory.

## Verified delivery

Dataset preparation is complete. See `local/release_2026-09-10_v2/DELIVERY.md` for exact artifacts, results and remaining project work. All 19 CSV outputs reproduced byte-for-byte. Passed 17 unit tests, 116 pipeline checks, 185 independent/rebuild checks and 43 saved-workbook checks comparing 24,178 data cells. All six workbook sheets were visually reviewed. Native Microsoft Excel application behaviour was not tested.

The existing prototype has **not** been switched to this all-cohort schema, and no real-data A/B outcome is claimed. It must consume namespaced string work keys and MP-term keys, use the new read-only database, and show source evidence and coverage limits. Store investigation outcomes separately from prepared features. A/B evaluation needs a predeclared baseline and enhanced method, fixed equal review budgets and properly separated calibration/test data. Controlled injected examples may test detection mechanics but cannot establish real-world fraud precision.

`prepare.py` reuses the deterministic lifecycle and prior-year cost calculations from `six_source/build.py`, but replaces its six-file loader, unsafe global-ID assumption, MP identity, source joins and payment processing. All transitive algorithm files are hashed in the manifest.
