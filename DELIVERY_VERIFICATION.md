# Delivery verification — PS 26102

Verified on 6 September 2026. Local application: http://127.0.0.1:8765/

## Requirement-by-requirement evidence

| Requirement | Verified delivery and evidence |
|---|---|
| Understand the problem and research before feature engineering | The solution plan maps PS 26102 requirements to available evidence, cites official MPLADS sources, corrects the context's outdated trust-limit assumption and documents unsupported claims. |
| Connect all three datasets without corrupting the sources | The raw pipeline preserves 10,000 works, 543 allocations and 12 consents, validates unique normalized join keys and reconciles amounts. All original SHA-256 values still match `pipeline_research/artifacts/audit.json`. |
| High-quality engineered dataset | 92 work fields, 29 MP fields, 21 IDA fields, 18 consent fields, 19 pair fields and 179 field/table definitions. Nulls, source rows, time availability, proxy rules and descriptive-model limits are documented. |
| Reproducibility | Independent feature rebuild: all six CSV tables match byte for byte; packed snapshot matches after excluding the generation timestamp. Independent A/B rerun: all five outputs match byte for byte. See `validation_research/reproducibility_check.json`. |
| Simple reviewable Excel | `MPLADS_Final_Core_Dataset_2026-09-06.xlsx` contains all connected tables, formula-linked summary, rule/source notes and A/B summary. Every exported table value was compared against the current core, not just a sample. Summary cached totals, six filterable tables and frozen header/ID panes pass. See `pipeline_research/workbook/verification.json`. |
| Interactive investigation prototype | Local React/Vite app implements portfolio filters, search/sort/export queue, case evidence and score explanations, pair comparison, MP/IDA profiles, dictionary, roadmap and A/B budget controls. Six model/filter/export tests and type checking pass; the final static production build succeeds. |
| Review persistence | Six isolated local-service tests pass: append-only history, save/reload, new-service access to the same database, pair reviews, invalid-input rejection, stale-version rejection and host/origin/payload guards. No fabricated decisions were added to the delivered user database by these tests. |
| Local runtime | START successfully launched the loopback service. STOP terminated only the recorded launcher-owned process; START successfully restarted it. The frontend's review-version fingerprint matches the service. |
| Local HTTP and data boundary | Nineteen final HTTP/asset/data checks pass. Served snapshot equals the current local snapshot; original hashes match; allowlisted downloads respond; static assets have usable MIME types. No Excel/CSV/database files or tested real-work description sentinels appear in the static build. The final Excel download additionally matches the on-disk file's SHA-256. |
| Architecture and rollout | `mplads-prototype/SOLUTION_PLAN.md` documents current and production architecture, joins, role scopes, security, ingestion contracts, monitoring, rollback, owners, phase gates and prospective trial design. |
| Honest baseline/enhanced validation | Temporal reference/test split: 7,013 / 2,987 works. Eight A/B design assertions pass. Report includes frozen formulas, seeded controlled benchmark, paired uncertainty, actual queue overlap, per-scenario trade-offs and clear absence of real fraud labels or a live randomized trial. |
| Packaged rebuild | `REBUILD_PROJECT.ps1 -SkipWorkbook` completed raw ingest, both feature builds, both A/B runs, equality checks, pipeline tests, dashboard tests, service tests, type checking and final app build. Excel generation and its exhaustive verifier were separately completed successfully with the corrected type-based date formatting. |
| Dependency review | The final full npm audit returned zero reported vulnerabilities after removing unused hosting/server-rendering dependencies and updating Vite/Undici. This is a dependency-advisory check, not a security certification. |

## Key reconciliations

- Visible sanctions: INR 5,276,800,278.00; reported works total: INR 41,388,495,369.08. Visible value coverage is 12.75%.
- Allocation total: INR 83,336,673,298.01. One amount remains null.
- Calamity consent total: INR 40,567,400.00.
- Unique candidate pairs: 21,092; candidate-linked works: 1,375.
- Current work priorities: High 1, Medium 811, Low 1,680, Routine 7,508.
- At 20% controlled-benchmark review capacity: A 37.25%, B 52.75% scenario recovery; +15.5 percentage points, paired 95% interval +12.0 to +18.25. Real queues each contain 598 records with 77.59% overlap.

## What is deliberately not claimed

- No substantiated fraud accuracy, false-positive rate, saved reviewer time, live A/B result or prediction-time forecast accuracy. B trades delay/aging coverage for cost/duplicate coverage.
- No national completeness, expenditure utilization, measured cost overruns, verified duplicate assets or automatic compliance findings.
- No authenticated government deployment, real-time source integration, multi-officer authorization or tamper-proof official audit trail. These are documented rollout gates.
- No automated browser click-through or visual acceptance of the web app. The user was offered that optional test; current web evidence consists of implementation inspection, automated logic/service checks, compilation and HTTP verification. The Excel workbook was rendered and visually reviewed on every sheet.
- No raw-data mutation, external publication or deployment. The complete data and review store remain local.

## Reproduction

Use `REBUILD_PROJECT.cmd` for the full packaged workflow. Use `-SkipWorkbook` for the verified code/data workflow without Excel regeneration. Run `pipeline_research/workbook/verify_workbook.py` with openpyxl available to repeat the exhaustive Excel comparison. Run `mplads-prototype/scripts/verify_delivery.py` against the running service for final read-only HTTP and source-boundary checks.

Core runtime verified: Python 3.12.14, NumPy 2.3.5, pandas 3.0.1; local app built with Node 24.19.0 and Vite 8.2.2. The lockfile pins application dependencies. Pipeline and A/B seeds are 26102.
