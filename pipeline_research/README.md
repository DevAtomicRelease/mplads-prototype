# MPLADS reproducible data pipeline

This folder contains the local raw-data pipeline for Problem Statement 26102. The pipeline reads the three supplied Excel exports with a style-independent ZIP/XML reader because their style records do not load reliably in normal Excel libraries. Source workbooks are never rewritten.

Run `python build_features.py` with Python 3.11+ and NumPy/Pandas available. The default input folder is the sibling `Dataset` directory. All outputs are created beneath this folder in `artifacts`. Run `python test_pipeline.py` for regression checks.

The generated `audit.json`, `QA_REPORT.md`, `feature_dictionary.csv`, and `snapshot.json` document the exact data used, feature definitions, missing inputs, source hashes, validation results, and machine-readable output. CSV tables are included for independent analysis.

The pipeline produces investigation priorities. These are observational screening signals and have no fraud ground truth. The works export contains 10,000 rows and its visible sanctioned value is materially below its reported total. It must not be treated as complete national coverage or used to infer expenditure/utilization. Historical features use dates strictly before the current sanction date. Peer, duplicate, entity, and isolation-forest outputs use the complete supplied snapshot and must be recomputed inside training folds for predictive evaluation.

The 45-day flag uses the supplied recommendation date as a proxy for date of receipt by the implementing district authority. Receipt timestamps and Model Code of Conduct exclusion periods are absent. Status age uses the latest observed sanction date as a snapshot proxy; no progress-update timestamp or completion timestamp is supplied.

The final review workbook from the prior task is preserved separately. This reproducible pipeline is versioned as `core-2026-09-06-v1`, so scores and duplicate-candidate counts may differ from the earlier exploratory workbook. Each output records its version to keep those results distinguishable.

## Output contract

`artifacts/snapshot.json` has `meta`, `tables`, `rules`, and `audit` keys. Each table is packed as `{ "columns": [field names], "rows": [value arrays] }`. Join work/MP/consent tables using `mp_name_key`; join works/IDA using `ida_key`; join candidate-pair endpoints using `work_id_a`/`work_id_b` to `work_id`. Dates are ISO `YYYY-MM-DD`, money is numeric INR, unknown values are JSON null, and flags are booleans. Rules are objects with `code`, `weight`, `definition`, and `caution`.

The core output contains 10,000 work rows with 92 total fields (including raw and derived fields), 543 MP profiles, 381 IDA profiles, 12 consent rows, and 21,092 candidate pairs covering 1,375 works. The feature dictionary contains 179 field/table definitions. All 19 build-time audit checks and nine regression tests passed on 6 September 2026. One source allocation amount is null. For the 269 MPs with no visible work rows, work counts are zero and amount/rate aggregates are null.

Do not mix core-v1 scores with the earlier workbook or with the independent A/B research variants. The separate temporal A/B experiment has frozen train/test scoring rules and is the source of held-out comparison results. This pipeline's complete-snapshot peer/candidate/Isolation Forest results are operational descriptive features.
