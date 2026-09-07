# MPLADS Insight — final local solution for PS 26102

## Outcome and evidence boundary

The delivered project turns all three supplied datasets into a reproducible investigation dataset and a local officer-review workspace. It supports sanctions monitoring, explainable anomaly queues, duplicate-candidate comparison, connected MP/authority profiles, persistent review notes and an offline A/B validation lab.

A score is investigation priority, not a probability of fraud. The requested payment, utilization, overrun and predictive capabilities are represented in the production architecture, but cannot be honestly validated from the supplied sanctions, allocation and consent records alone. The delivered scope is a complete local research solution, not an authenticated government production deployment.

## Problem-to-capability mapping

| PS requirement | Delivered now | Evidence needed to extend it |
|---|---|---|
| Unusual expenditure and fund use | Sanction-value distributions and allocation context, kept separate | Payments, expenditure ledger, dated allocation periods and reconciliations |
| Cost anomalies and overruns | Leave-one-out peer amount benchmarks, robust deviations, descriptive Isolation Forest ranks | Original/revised estimates, quantities, specifications, unit costs, procurement records |
| Duplicate works | Blocked weighted text candidates with amount/entity/date corroboration and phase/number safeguards | Asset identifiers, coordinates, dimensions and approved scope |
| Delayed projects | Recommendation-to-sanction interval and early-stage sanction-age signals | IDA receipt, MCC exclusions, work start/due/completion dates and dated progress |
| Risk alerts and dashboards | Portfolio, queue, evidence, MP/IDA profiles, exports and review dispositions | Official case assignment, authenticated roles and notification channels |
| Predictive insights | Descriptive anomaly ranking plus separate historical-reference A/B experiment | Longitudinal outcomes and independently adjudicated labels |
| Compliance monitoring | Versioned proxy rules with explanations and explicit evidence limits | Effective-date rule registry and documentary verification |

## Architecture delivered on this computer

```text
3 unchanged raw XLSX exports
  -> style-independent ZIP/XML ingest and source hashes
  -> validated work / MP / IDA / consent / pair tables + dictionary
  -> CSV + packed JSON + plain final Excel workbook
                         |
                         v
Python loopback service (127.0.0.1:8765)
  - allowlisted data and report endpoints
  - SQLite review history outside the static application
                         |
                         v
React/Vite investigation workspace (local static assets)
  - filters, search, evidence drawers, pair comparison, entity profiles
  - A/B lab, case dispositions, notes and exports

Same raw-derived work fields
  -> frozen historical-reference A and B ranking methods
  -> temporal holdout + controlled injected-evidence benchmark
  -> scores, split manifest, metrics, report and independent rerun checks
```

There is one row per work ID. MP and IDA joins are many-to-one. Calamity consents remain MP-level context; no source work-level funding relation is invented. Candidate pairs are a separate edge table. Joining either child table directly into a financial aggregation would multiply amounts and is explicitly avoided.

The browser receives real data only from the local service. Real records are not bundled into application assets. The service listens only on loopback and rejects external Host headers and non-local write origins. There are no analytics or external font requests. The GitHub repository contains the audited source code and documentation only. No hosting deployment or publication of raw/derived records or review notes is authorized or configured. Early scaffold registration metadata is inert and does not authorize deployment.

Review saves use parameterized SQLite transactions with append-only application history. Each save stores record key, disposition, note, timestamp and dataset version. This is a single-user local store, not a tamper-proof official audit system and not authenticated officer attribution. Keep the entire project and local review database under appropriate device access controls.

## Reproducible feature engineering

Read the PS and context first; treat the context as background rather than authoritative current rules. Preserve the source bytes and retain original worksheet row identifiers. Malformed Excel style metadata is bypassed by reading the workbook XML without modifying the files.

1. Validate row counts, IDs, source totals, missing amounts and dates. Normalize names conservatively, then verify uniqueness and many-to-one cardinality before joining.
2. Derive financial year, recommendation delay, sanction age, status stage, description characteristics, batch context and explicit data-quality indicators. The maximum observed sanction date, 2026-09-01, is a snapshot proxy.
3. Build strictly prior MP/IDA histories. Same-day works are excluded from prior features. Keep absent history distinct from zero.
4. Compute leave-one-out robust cost peers with documented fallback and scale safeguards. Full-snapshot peers are descriptive, not prediction-time features.
5. Generate blocked weighted-token candidates. Corroborate descriptions with authority, MP, amount and dates; retain continuation/generic-description/number-conflict evidence. This is candidate generation, not asset identity verification.
6. Fit the deterministic NumPy Isolation Forest screening implementation (seed 26102, 100 trees, subsample 256) to five descriptive work features. Its rank is uncalibrated and full-snapshot; it is not a trained fraud classifier.
7. Apply the versioned explainable rule registry. Every score decomposes into its stored reason codes. Preserve MP/IDA and consent tables with null-aware aggregation.
8. Export all tables, field-level definitions, QA report and source hashes. Rebuild independently and compare outputs.

Core version: `core-2026-09-06-v1`. This supersedes the earlier exploratory workbook for application use. The earlier workbook remains preserved; its 121 fields and older scores are not mixed with the current 92-field work table. The independent A/B methods also have distinct scores.

## Reconciled current output

| Table / measure | Verified result |
|---|---:|
| Works / total fields | 10,000 / 92 |
| MPs / authorities / consents | 543 / 381 / 12 |
| Candidate pairs / works with candidates | 21,092 / 1,375 |
| Field/table definitions | 179 |
| Visible sanctioned value | INR 5,276,800,278.00 |
| Allocation total | INR 83,336,673,298.01 |
| Calamity consent total | INR 40,567,400.00 |
| Priority High / Medium / Low / Routine | 1 / 811 / 1,680 / 7,508 |

The works extract ends at exactly 10,000 records and includes 12.75% of its reported INR 41,388,495,369.08 value. It may be selected rather than representative. Counts and amounts describe the supplied extract; rates/ranks are sample-specific, not necessarily lower bounds. One allocation amount is missing. For 269 MPs without visible works, counts are zero but unobserved work amount/rate aggregates remain null.

## Honest A/B validation

The experiment compares A (continuous delay and early-stage aging rules) with B (A plus robust historical peer cost and same-IDA/type historical duplicate evidence). This narrow baseline isolates the added signals; it is not claimed to be the strongest alternative.

Train/reference: 7,013 works sanctioned through 2025-02-20. Test: 2,987 later works. Peers and text references are fitted only on training records. Full-snapshot core cost, duplicate, aggregate and priority features are not used as model inputs. The test uses current snapshot status/age and is retrospective screening, not a forecast made at sanction time.

The controlled benchmark uses 1,200 eligible held-out rows: 100 assignments each for delay, aging, high cost and duplicate evidence, plus 800 unchanged rows. Those unchanged rows are not verified negatives. Some assigned scenarios reinforce existing signals; 371 of 400 increase the corresponding scoring component. All injection occurs in a separate in-memory/output copy. Fixed seeds and formulas are recorded; no test-based weight search was performed.

At a 20% review budget (240 benchmark cases), A recovers 37.25% of scenario-assigned cases and B recovers 52.75%: +15.5 percentage points, with a paired bootstrap 95% interval of +12.0 to +18.25 points. This interval is conditional on this controlled benchmark and does not measure uncertainty about real-world fraud detection.

The scenario trade-off is material: delay recovery 100% -> 38%; aging 27% -> 5%; cost 12% -> 84%; duplicate 10% -> 84%. On real test records, both methods select 598 cases and their queues overlap by 77.59%. Without adjudicated labels there is no valid real fraud precision, recall, false-positive rate or claimed time saving. The 5% benchmark interval includes zero.

All data tables reproduce exactly on independent rebuild. Core JSON matches after removing its run timestamp. All five A/B outputs reproduce byte for byte. See the separate validation report and reproducibility JSON for the evidence.

## Prospective randomized A/B pilot — not yet conducted

Obtain authority, define eligible units and freeze the protocol before review. Use comparable district-review-team clusters, stratified by region and workload, to avoid the same officer seeing both rankings for overlapping cases. Randomize clusters 1:1 to frozen A or B, with identical eligibility windows and review capacity. Do not replace the assigned ranking after seeing outcomes.

Primary endpoint: independently substantiated, actionable issues per completed review. Report intention-to-treat results and a separate completion analysis. Secondary endpoints: time to a documented decision, evidence-request completion, reviewer agreement and appeal/reversal rates. Sample unreviewed cases independently to assess missed-case risk. Blinded adjudicators see source evidence, not variant or score.

Guardrails: track delay/aging coverage and unresolved aged cases, given the observed trade-off; assess geographic/category coverage and case burden. A protected delay-review quota is a candidate next variant, not a validated result from this experiment. Log outages, non-adherence, missing adjudication and cross-cluster contamination.

Estimate baseline yield and cluster correlation in a short discovery phase; then calculate sample size for a policy-approved minimum useful improvement, two-sided alpha 0.05 and at least 80% power. Inflate for clustering and incomplete reviews. Do not invent a sample size before those inputs exist. Pre-register the horizon and stopping rules, avoid repeated uncorrected significance checks, and use cluster-aware uncertainty. Roll out B only if useful-case yield improves without unacceptable guardrail deterioration.

## Production architecture and rollout

| Phase | Owner | Delivery and exit gate |
|---|---|---|
| 1. Local research solution — delivered | Data/ML and application engineers | Reconciled tables, working local investigation flow, persistence, automated checks and reproducible offline A/B |
| 2. Complete source contracts | Ministry/state data stewards with domain reviewer | Uncapped historical exports, stable IDs, dated allocations, payment/estimate/progress ledgers; source reconciliation and lawful access agreed |
| 3. Restricted operational pilot | Backend/security engineer and district review lead | PostgreSQL case store, SSO, MP/state/IDA/ministry role scopes, assignment, audit retention, encrypted backups and restore drill |
| 4. Evidence-rich detection | Data/ML engineer and technical auditors | Unit costs, payment reconciliation, vendor graph and geospatial/asset matching; each detector has reviewed labels and robustness tests |
| 5. Controlled validation and staged rollout | Independent evaluator and scheme owner | Prospective randomized trial, preregistered acceptance gates, monitoring, rollback and accountable sign-off |
| 6. Predictive monitoring | ML owner and domain reviewer | Point-in-time features, temporal holdouts, calibration and drift tests for delay/outcome models; only supported claims deployed |

Production flow: authenticated authorized ingestion -> immutable dated snapshots -> schema/reconciliation gates -> versioned time-aware feature jobs -> rule/model registry -> scoped case API -> officer evidence review -> independent adjudication -> evaluation and controlled updates.

Use separate work, MP, IDA, allocation-period, consent, payment, estimate-version, progress-event, asset and case tables. Store model/rule/source versions on every case. Enforce server-side row scopes; role-switching UI alone is not access control. Use encrypted transport/storage, secrets management, input limits, least privilege, retention policy and audit-access monitoring. Back up data and test restoration. Keep deployments within the approved data boundary; no public release of records without explicit authorization.

Monitor ingestion freshness, cap/coverage changes, unmatched keys, total reconciliation, missingness, score/rank drift, queue size, outcome yield, guardrail coverage and appeals. On schema or reconciliation failure, retain the last verified snapshot and visibly mark it stale; do not silently publish partial refreshes. Roll back by immutable data/rule/model version.

## Verification and handoff limits

Automated evidence includes 19 pipeline audit checks, nine pipeline regressions, six dashboard/model tests, eight A/B design assertions, six local service tests, independent reproducibility checks, type checking and a successful static production build. Final HTTP checks cover local assets, data/validation routes and absence of raw records from the static bundle.

The local service persistence tests use disposable databases, not fabricated decisions in the delivered user store. A browser interaction/visual acceptance checklist is included for the user; automated end-to-end browser interaction testing has not been claimed. Production permissions, real-time integrations, nationwide completeness and a live randomized trial require the additional evidence and authority described above.

## Official research sources

- [MPLADS Guidelines April 2023](https://www.mplads.gov.in/MPLADS/UploadedFiles/MPLADSGuidelinesApril2023.pdf): the 45-day period concerns IDA receipt; recommendation is only a proxy here. Trust limits are INR 50 lakh per MP/year across trusts and INR 1 crore for a particular trust during the term; the context file's INR 75 lakh figure must not drive current automatic findings.
- [Lok Sabha reply, 18 December 2024](https://sansad.in/getFile/loksabhaquestions/annex/183/AS338_TsKdbP.pdf?source=pqals): updated outside-jurisdiction provision and receipt-based sanction timing. Apply effective-date rules; geography alone is not a violation.
- [MoSPI Annual Report 2023–24](https://mospi.gov.in/sites/default/files/publication_reports/AnnualReport_2023-24.pdf): scheme and monitoring context.
- [Parliamentary proceedings, 2 April 2025](https://eparlib.sansad.in/bitstream/123456789/2989604/1/lsd_18_IV_02-04-2025.pdf): eSAKSHI context. This platform complements official processes with an investigation layer.

These sources support design choices, not a claim of exhaustive legal validation as of deployment. A responsible scheme authority must approve the effective rule registry before operational use.
