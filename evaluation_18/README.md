# PS 26102: all-cohort A/B evaluation

This folder contains the new **offline paired comparison** for the verified 18-source release. It supersedes the older three-source experiment for this dataset. No live reviewer trial has been run and there are no adjudicated real fraud labels.

The [11 September AI/ML research and design](AI_ML_RESEARCH_AND_DESIGN.md) documents recommended next methods, feature eligibility, alternatives and validation gates. It does not change or extend the frozen experiment's measured results.

## Result and decision

At a fixed 720-review budget on 7,200 constructed test cases, baseline A recovers 601 positives and enhanced B recovers 610: **+9 cases, or +0.25 percentage points of recovery**. The 1,000-draw paired-context bootstrap interval is +0.028 to +0.472 points **conditional on the main tie seed**. Across the 20 predeclared alternative tie seeds, B wins 15, ties once and loses four times (difference -0.111 to +0.306 points). The small advantage is not robust to tie-breaking. This does not establish operational superiority.

At score >0 with unlimited capacity, B raises controlled recovery from 77.78% to 89.44%, but raises selection of constructed normal cases from 33.33% to 37.53%. That is a workload/false-alarm tradeoff, not a free improvement. Check all families, including baseline cases displaced at fixed capacity. On real data, the 10% queues share 14,389 of 16,071 works; 1,682 A cases are displaced in B. These counts have no confirmed-good/confirmed-bad interpretation.

Decision: preserve the operational queue; keep enhanced cost/text findings separately visible with source evidence and adjudication. Architecture and workflow are planned in `ARCHITECTURE_AND_WORKFLOW.md`; the app has not been migrated to the new release in this evaluation step.

## Local deliverables

- `local/run_v1/RESULTS.md`: generated results and interpretation.
- `local/run_v1/metrics.json`: exact computed metrics.
- `local/run_v1/Real_Scores.csv`: all 160,701 namespaced work IDs, components and both ranks. A 10% queue is `rank_a <= 16071`; B is `rank_b <= 16071`. Never cast work IDs to integers.
- `local/run_v1/Controlled_Families.csv`: all 18 families at 5%, 10% and 20% budgets.
- `local/run_v1/Synthetic_Primitives.csv`, `Synthetic_Oracle.csv`, `Test_Scores.csv`: separate inputs/truth, computed components and saved selections. The oracle is joined only after scoring.
- `local/run_v1/Reference_Membership.csv`: historical cost/frequency reference keys and dates, not a duplicate-retrieval truth set.
- `local/run_v1/Paired_Bootstrap.csv`, `Tie_Sensitivity.csv`, `Threshold_Workload.csv`: uncertainty, primary synthetic tie sensitivity and alert workload.
- `local/repro_verification.json`: all 71 checks passed; 17 result artifacts and the manifest rebuild byte-for-byte; 18 raw files, 19 prepared CSVs and nine preparation-code files remain unchanged.
- `local/independent_audit_v2.json`: all 117 independent accounting checks passed, including every saved rank/selection, the 9,000 primitive operational/payment feature rows, 20 tie seeds and 1,000 bootstrap draws. The separate audit implements ranking and multiplicity-based bootstrap allocation independently. It does not establish real fraud truth or independently re-execute cost/text model formulas.

Results are local-only and excluded from publication. The workbook contains aggregates, no member names or individual real work records. It is still a local artifact, not publication authorization.

## Reproduce

Use Python 3.12 with pandas 3.0.1 and NumPy 2.3.5 (the recorded run versions). From the project root, with those dependencies available:

```powershell
python -B evaluation_18/tests.py
python -B evaluation_18/run_ab.py --output-dir evaluation_18/local/my_run
python -B evaluation_18/run_ab.py --output-dir evaluation_18/reproduced/my_run
python -B evaluation_18/verify_repro.py evaluation_18/local/my_run evaluation_18/reproduced/my_run --report evaluation_18/local/my_verification.json
python -B evaluation_18/audit_results.py evaluation_18/local/my_run --report evaluation_18/local/my_independent_audit.json
```

Use new empty run directories and a new report filename. The verifier restricts reports to `evaluation_18/local` or `evaluation_18/reproduced` and rejects existing destinations. Do not use Python's optimization flag: invariant assertions are intentionally active. The pipeline reads the frozen CSV release, validates its hashes and does not write to its SQLite database. Regenerating this benchmark does not regenerate the feature release. A refreshed dataset requires a new versioned feature release and a separately declared evaluation protocol.

25 known-answer tests cover monetary/date boundaries, missing inputs, duplicate guards, minimum peers, future-reference exclusion, namespace/tie behavior and confusion-matrix accounting. Synthetic labels are not used to fit any model or threshold. The development partition is reserved for debugging; no reported superiority was selected by trying seeds, severities or weights.

## Interpretation limits

The real queue is retrospective snapshot screening. The synthetic benchmark has intentionally artificial 50% positive prevalence and nine anomaly families, not observed national prevalence. Source recommendation date may differ from authority receipt date; one-year completion can have exceptions; source term end may differ from actual demission. Bank references, invoices, quantities, official extensions and physical-asset identifiers are not supplied. Do not interpret screening flags as legal findings, verified fraud, probabilities or forecasts.

The benchmark has no dedicated exact-description duplicate-positive family: its duplicate-positive variants all change the wording. Exact matching is covered by known-answer tests and the identical-visible/distinct-assets control, not a positive recovery stratum. Pending-recommendation screening likewise has known-answer tests but no dedicated benchmark family. These scope choices limit comparisons across the full production mix; the frozen benchmark was not expanded or retuned after observing results.

The 20-seed sensitivity analysis applies to the **synthetic primary-budget** result. Real queue boundary-tie sizes are reported, but real queue membership sensitivity across alternative tie seeds has not been evaluated. A live study and held-out real adjudication remain prerequisites for claims about operational effectiveness.

Reference methods and primary research links are in `PROTOCOL.md`; it and the evaluation source are frozen in the run manifest. Supporting documentation/workbook/audit code may be extended without altering the frozen scoring algorithm or its results.
