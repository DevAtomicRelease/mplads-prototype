# MPLADS PS 26102: prototype architecture and workflow plan

Planning date: 10 September 2026. Status: **proposed implementation**, informed by the completed first offline A/B run. This document does not mean that the existing application is integrated with the new data, that its security controls are implemented, or that a live trial has occurred. Exact rebuild verification is reported separately in the evaluation handoff.

AI/ML research addendum, 11 September 2026: [AI/ML approach and evaluation gates](AI_ML_RESEARCH_AND_DESIGN.md) selects a hybrid rules/peer/text evidence design, character TF-IDF as the first retrieval challenger and a separately evaluated Isolation Forest discovery channel. Local E5 embeddings and supervised/survival models are conditional later studies. This refines the proposed model layer without changing the frozen A/B experiment or claiming new models are implemented.

## 1. Decision after the offline comparison

Build a **local evidence-led investigation prototype**. Keep the baseline operational screens available, show enhanced cost and similar-work signals in a separate comparison/shadow view, and record human findings independently of the source data. Do not replace baseline selection or call a high score a fraud probability.

At the predeclared 10% synthetic review budget, each method reviews 720 of 7,200 cases. A recovers 601 constructed positives; B recovers 610: **nine additional constructed positives**, or +0.25 percentage points of recovery. The paired-context interval is approximately +0.03 to +0.47 points, but B loses under four of the 20 alternative tie seeds and ties under one. These intervals and labels describe constructed cases, not operational fraud accuracy.

The aggregate conceals trade-offs. At that budget B gains 12 inflated-cost and 23 near-duplicate constructed cases, while selecting eight fewer completion overruns, six fewer repeated-payment cases, four fewer stalled cases, three fewer overpayments, three fewer missing-success cases and two fewer late sanctions. Some legitimate large-scope cases and identical-looking distinct assets are also selected. This is a reason to expose evidence and displaced cases, not to retune silently until B wins. In the real snapshot, each 10% list has 16,071 works; 1,682 enter B and 1,682 A cases are displaced. Their actual correctness is unknown.

Source artifacts: `local/run_v1/RESULTS.md`, `metrics.json`, `Controlled_Families.csv`, `Tie_Sensitivity.csv` and the locked `PROTOCOL.md`, all under this document's evaluation folder. Synthetic labels must never be displayed as labels on real works.

Coverage limitation: the constructed duplicate-positive family always changes wording; there is no dedicated exact-description duplicate-positive recovery stratum. Exact matching and pending recommendations have known-answer boundary tests but are not separately represented as positive benchmark families. This is another reason not to extrapolate the small aggregate gain to the real production case mix.

## 2. Problem-statement coverage and limits

The product should help MPs, District Authorities, State Nodal Authorities and the Ministry follow approvals, expenditure, progress and durable-asset creation. Its first usable outcome is an explainable work dossier and an auditable action queue, not an automated allegation or sanction.

| PS 26102 need | First prototype capability | Boundary on interpretation |
|---|---|---|
| Delayed projects and approvals | Dated lifecycle, age and baseline screen views; receipt/extension evidence request | Recommendation is not proven receipt; approved extensions are not supplied |
| Expenditure and cost overruns | Successful and pending payments separately; exact-paise reconciliation; completion/sanction comparison | An export is not a bank ledger; no material paid/sanction overrun was observed above the declared INR 1 tolerance |
| Unusual cost estimates | Historical peer count, state/activity fallback, median, ratio and robust deviation | Missing quantities and specifications prevent a finding of overpricing |
| Potential duplicate works | Side-by-side descriptions, amounts, number/phase guards and source records | Bounded candidate retrieval is not exhaustive; text resemblance does not prove the same physical asset |
| Fund use and agency patterns | Term-level allocations/consents/work/payment context; vendor and IDA connections | Do not equate consent with expenditure, report repeats with repeated bank transfers, or concentration with misconduct |
| Alerts and accountability | Versioned screening reasons, evidence checklist, owner and review history | Screens are investigation prompts; findings require responsible human adjudication |
| Trends and predictive insights | Retrospective payment and lifecycle trends, clearly dated | No forecast or predictive accuracy claim until repeated event-time snapshots and validated outcomes exist |

## 3. Architecture: keep facts, scores and decisions separate

```text
18 local raw exports (preserved; three cohorts x six dataset types)
        |
        v
Reproducible preparation + reconciliation + manifest checks
        |
        v
Versioned prepared release [read-only SQLite + dictionary + provenance]
        |                                   |
        |                                   v
        |                        Versioned A/B evaluation outputs
        |                        [real ranks separate from synthetic tests]
        |                                   |
        +---------------+-------------------+
                        v
             Typed local Python API
        [read adapters, scoped queries, evidence service]
                  /                    \
                 v                      v
       React investigation UI      Separate local reviews DB
       served on loopback          + controlled evidence folder
                 |                      |
                 +----human decisions---+
```

### Components and ownership

| Layer | Proposed design | Contract and responsibility |
|---|---|---|
| Immutable facts | Existing `data_preparation/local/release_2026-09-10_v2/mplads_prepared.sqlite3` | 19 prepared tables and 18 raw-source tables; 160,701 works, 1,023 MP terms, 113,691 accepted payment-report rows and 34,242 vendor IDs. Open with SQLite read-only mode; never create tables or indexes in this release |
| Evaluation read adapter | Load verified `Real_Scores.csv` and evaluation metadata into a separate versioned read cache when needed | Join on exact namespaced `work_id`; require the prepared-release fingerprint to match; retain score A/B, rank, reasons, tie seed, budget and method version. Cache construction does not change facts |
| API | New `prototype_api/` using FastAPI/Pydantic and Python SQLite adapters | Explicit response schemas, parameter validation, request-scoped database connections, named allowlisted queries, domain error responses and generated API contract. Pin/test dependencies during implementation; FastAPI is a proposed addition, not an installed/verified integration |
| Presentation | Adapt the existing React/TypeScript/Vite application and reusable tables/charts | Paginated queries, readable INR presentation, keyboard-accessible evidence panels, loading/error/empty states and persistent release/as-of labels. Bundle assets locally; no CDN dependency |
| Case management | Separate `local_app_state/reviews.sqlite3` | Cases, links to work/pair entities, assignments, review events, evidence metadata and study assignments. Writable only through validated application actions; never write adjudications back into feature columns |
| Evidence files | Separate controlled local directory, referenced by generated IDs | No automatic document acquisition. Validate approved file types/signatures and size; safe generated filenames, hashes, access checks and no executable rendering. Reviewers attach only material they are authorized to hold |
| Quality/operations | Local startup checks, test suite, build/release manifests and backup/restore scripts | Refuse a mismatched release; show meaningful stale-data warnings; preserve previous releases and case history. Logs omit free-text evidence and sensitive query strings |

SQLite is a reasonable design choice here because the dataset and application stay on one device with low write concurrency. It is not a plan to place a writable SQLite file on a shared network drive; a server database should be reassessed for concurrent institutional use. This is an architectural inference from [SQLite's deployment guidance](https://sqlite.org/whentouse.html). FastAPI's documented database/session pattern supports a small typed adapter, but its tutorial's table-creation examples must **not** be applied to the frozen prepared database. See [FastAPI's relational-database documentation](https://fastapi.tiangolo.com/tutorial/sql-databases/).

### Migration from the existing prototype

The current `six_source/serve.py` is not schema-compatible: it expects `MP_Features`, `Rule_Contributions`, old priority/isolation fields and numeric-only work lookup. The new release has `MP_Term_Features`, `Work_Signals`, explicit current screening fields and namespaced string IDs. Existing UI files and unrelated changes must be preserved while introducing the adapter behind a separate configuration/entry point.

1. Freeze the API response contract and add fixtures for all three cohorts before changing screens.
2. Replace numeric identity assumptions and obsolete field names deliberately; do not merely point the old server at the new database.
3. Replace the old validation page's six-source artifacts with the new evaluation adapter. Show data release and method version together; reject a mismatch.
4. Reuse the existing components and styles where useful, but replace fake/demo totals and unsupported probability language. Show missing functionality explicitly.
5. Make the production-style local launch serve the compiled UI and API from the same loopback origin. Keep any development proxy loopback-only. A successful page load alone is not integration acceptance.

## 4. Data and API contracts

### Identity, units and provenance

- Treat `work_id`, `mp_key`, `ida_key`, vendor IDs and pair IDs as strings end to end. `work:<numeric-id>` and `rec2:<cohort>:<numeric-id>` are different identities. Preserve all 278 numeric-ID collision cases and 1,205 FLAG=2 recommendations without guessed joins.
- `mp_key` identifies a parliamentary term, not a lifetime person. Cohort, house, reported tenure and actual term dates remain separate. Do not merge people by display name.
- Store and calculate currency as integer paise. Serialize monetary values as base-10 **paise strings** plus an explicit `currency: INR` contract; format them without lossy floating-point conversion. Null means unavailable, not zero. Ratios may be finite numeric values or null; never return NaN/Infinity. Counts and bounded scores can be JSON integers.
- Use ISO calendar dates for source events, an explicit snapshot `as_of_date`, and UTC timestamps for application review events. Explain calendar-month/year screen boundaries in dictionary help. Do not convert source dates into invented times.
- A work dossier exposes its source-stage IDs, source-file/record references, payment `source_id` and report fingerprint, relevant raw field values, field conflicts and transformations. Raw-table access is a bounded evidence endpoint, not an unrestricted SQL/download endpoint.
- Keep `successful_payment_paise`, `pending_payment_paise` and `unique_fingerprint_sensitivity_paise` visibly distinct. The fingerprint sensitivity is a scenario, not an authoritative deduplicated ledger.
- Use the evaluated `no_success_three_months_flag` where the A/B method calls for absent successful payment. Do not silently substitute `no_payment_three_months_flag`, which has different meaning.
- Every response carries `api_schema_version`, `data_release_id`, `as_of_date` and applicable `method_version`. Every saved decision records the release/evidence viewed.

### Proposed endpoints

All endpoints below are **to be implemented and tested**. Use query parameters for namespaced entity IDs; encode them normally and bind them as values. Never interpolate user-supplied identifiers into SQL.

| Endpoint | Purpose and constraints |
|---|---|
| `GET /api/v1/meta` | Release fingerprint, row counts, as-of date, limitations, startup verification state and available methods |
| `GET /api/v1/options` | Scoped cohort/house/state/term/year/activity/lifecycle filters; MP display labels include term dates |
| `GET /api/v1/works` | Filters and search; allowlisted sorts; default 50 and maximum 100 rows; stable `(sort value, work_id)` cursor tied to release/filter hash |
| `GET /api/v1/work?work_id=...` | One dossier: lifecycle, separate monetary values, screening reasons and data-quality caveats |
| `GET /api/v1/payments?work_id=...` | Paginated report rows, payment status and repeat sensitivity; no invented transaction identity |
| `GET /api/v1/pairs?work_id=...` | Paginated candidate pairs and comparison evidence, with retrieval scope disclosed |
| `GET /api/v1/peers?work_id=...` | Historical cohort definition/count/median and bounded peer examples; no later-year reference leakage |
| `GET /api/v1/provenance?work_id=...` | Scoped source references, conflicts and quarantined-record context when relevant |
| `GET /api/v1/terms`, `/vendors`, `/idas`, `/trends` | Separately defined grains and aggregate denominators; never multiply totals through many-to-many joins |
| `GET /api/v1/queue?method=A&budget=0.10` | Frozen rank and membership with counts, reasons and tie policy. B is explicitly a comparison/shadow method |
| `GET /api/v1/validation` | Controlled benchmark results and real queue shifts in separate sections; real accuracy fields unavailable |
| `GET /api/v1/dictionary` | Searchable field definitions, units, sources, null meanings and time-availability limitations |
| `POST /api/v1/cases`, `GET /api/v1/cases` | Create/list scoped work or pair investigations, preventing accidental duplicate open cases |
| `POST /api/v1/case-events` | Version-checked assignment, evidence request, disposition or reopening event with author and rationale |
| `POST /api/v1/evidence` | Authorized local upload into the evidence store with limits, validation and audit metadata |

Saved evaluation ranks and top-budget membership refer to the full frozen population. Applying a user scope or display filter limits which of those rows may be shown; it must not silently recompute the experimental ranks, budget denominator or validation totals. Display global membership and the visible scoped count separately. A jurisdiction-relative quota or reranking scheme is a new operational policy and requires separate evaluation.

Mutation requests include an idempotency key and expected case revision; stale writes return a conflict rather than overwrite another decision. Enforce payload limits, permitted state transitions and entity existence on the server. An invalid entity returns not found without revealing an out-of-scope record. Downloads are disabled by default; any later local export is scoped, logged, formula-injection-safe for spreadsheets and clearly labelled. No bulk raw download button in the first release.

## 5. Screens and investigator workflow

### Main screens

1. **Overview:** current release, cohort/term filters, work counts, successful versus pending payments, baseline screen counts and data-quality warnings. Aggregates reconcile to the selected population; avoid adding overlapping screen counts into a unique-work total.
2. **Operational queue:** baseline reasons and rank, assigned owner and case status; screen-specific tabs keep important operational issues discoverable even when top-K ranking crowds them out. Tab availability does not imply a newly validated allocation policy.
3. **Work dossier:** recommendation-to-completion timeline, costs/payments, source conflicts, dictionary explanations, and a concise “what must be checked” panel.
4. **Pair/cost investigation:** side-by-side pair evidence, guarded exclusions, historical peer scope and cost comparison; clear missing location/specification warnings.
5. **Term/agency/vendor view:** connected entities with term and cohort context, plus concentration as a descriptive indicator, not a misconduct label.
6. **My cases:** evidence requests, deadlines supplied by the responsible authority, assignments, event history and dispositions.
7. **Method comparison:** A-only, B-only and overlapping works, fixed capacity, score components, synthetic family losses/gains and tie sensitivity. Synthetic case examples are visually separated and carry no real entity identifiers.

### Daily work sequence

Open the verified release -> choose authorized term/state/agency scope -> inspect baseline queue or a specific screen -> open the dossier -> check source/payment/pair evidence -> request missing documents -> record a reasoned disposition -> route substantiated issues to the authorized authority -> follow up and close with an audit trail.

For payments, obtain bank transaction references before treating repeated reports as repeated transfers. For cost comparisons, obtain quantities/specifications and comparable estimates. For duplicates, verify location, phase and physical asset identity. For delays, obtain authority receipt dates, sanction conditions and approved extensions. A missing export record alone cannot substantiate non-payment or non-creation of an asset.

### Case state machine

```text
New -> Triaged -> Evidence requested -> Under review -> Disposition recorded -> Closed
          |                              ^                                  |
          +------> Under review --------+                                  |
                                        Reopened <-------------------------+
```

Disposition is a separate field: **insufficient evidence, expected variation, source-data issue, or substantiated administrative/financial issue**. A disposition is not a legal finding of fraud. Closing requires the decision, reviewer, dated rationale and evidence reference; a high-impact substantiated issue requires independent approval before closure/escalation. Evidence requests can remain unresolved without forcing a false positive/negative label. Reopening records its reason and preserves earlier decisions; records are not silently deleted.

### Proposed responsibilities and access

These scopes require confirmation from the scheme/data owner. A role selector in a local demo is a viewing convenience, **not authentication or real access control**.

| Role | Intended scope | Proposed actions |
|---|---|---|
| MP/authorized office | Authorized parliamentary term and its works | View progress, request clarification and track actions; not unilaterally adjudicate allegations |
| District investigator | Assigned district/IDA cases, once authoritative scope mappings exist | Triage, request/upload evidence and propose findings |
| State Nodal supervisor | Authorized state | Assign/reassign cases, monitor overdue actions and independently approve permitted dispositions |
| Ministry analyst | Authorized cross-state oversight | Aggregate comparisons, approved case escalation and method/governance review |
| Data steward | Source-release operations | Validate/import a new release, investigate source errors and manage lineage; cannot rewrite raw facts or manufacture review labels |
| Adjudicator/auditor | Assigned study/audit cases | Independently assess evidence and inspect permitted history; no model tuning from held-out labels |

An IDA label is not automatically a district jurisdiction. Until a trusted user-to-jurisdiction mapping exists, do not claim district-level access isolation. The first single-user local prototype can demonstrate workflow with a clearly labelled local operator identity; a multi-user launch must authenticate real identities and enforce object-level scope in every endpoint. OWASP recommends default-deny and per-request authorization checks; these requirements also apply to evidence and export access, not just menus. See [OWASP's authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html).

## 6. Local privacy, security and operational controls

Bind the service to `127.0.0.1` only; use exact host/origin allowlists and same-origin requests, with protected state-changing operations and a local session secret. Loopback limits network exposure but is not a substitute for application security against local software or malicious browser requests. Disable directory listings, arbitrary paths, unrestricted SQL, telemetry, remote fonts/scripts and external model/API calls. Package dependencies/assets before offline use; installation may require an explicitly controlled network step.

Keep prepared data, review notes, evidence and generated artifacts outside the public application bundle and excluded from version control. A future repository share should contain code and synthetic fixtures only unless the owner expressly authorizes particular real material for publication. A private repository still counts as data leaving this device. This plan authorizes no push, hosting, external LLM processing or live portal integration.

Use Windows account permissions and approved device encryption; test encrypted/offline backup and restore of reviews/evidence separately from reproducible prepared facts. Backups need an approved destination, retention period and owner. Append-only application events improve accountability but are not tamper-proof against the device owner; do not market them as immutable institutional audit logs. Define incident handling, evidence retention and deletion authority before collecting sensitive attachments.

LAN or institutional deployment is a separate gate: approved hosting/data handling, authenticated users, server-side scope authorization, TLS, managed secrets, audit retention, backups and concurrent-write testing. Reassess the database for that workload; never expose the current loopback demo by changing the bind address alone.

## 7. Refresh, lineage and later modelling

1. Receive a new authorized export locally into a new dated source directory; record its hash and acquisition context. Never overwrite a previous export.
2. Validate all expected dataset/cohort contracts, record conservation, key namespaces, quarantine handling and exact monetary reconciliations. Fail the release on broken contracts; missing cohorts are not silently treated as zero.
3. Build a new prepared release and new evaluation output directory. Record code, parameters, input hashes and output hashes. Distinguish changed source data from a changed method.
4. Produce a release-difference report: added/removed works, changed amounts/statuses, joins, source conflicts and screen shifts. Do not carry a prior finding onto a newly ambiguous identity without review.
5. Approve and atomically switch the application's current-release pointer only after checks pass. Existing cases retain their original evidence snapshot and expose newer source changes explicitly.
6. Keep the prior pointer and versioned stores for rollback. A rollback must not erase new review events; restoration of a review backup is a separate controlled operation.

The current features are retrospective. Early-warning or learned models require repeated snapshots with event availability/receipt timestamps, reliable outcomes, exception records and leakage-safe entity/time splits. First gather these prospectively; then predeclare a separate modelling study. Do not train on synthetic oracle labels and describe the output as an operational fraud detector. A future alternative queue allocation or weighting policy also needs a new version and fresh evaluation, not an undocumented change to this benchmark.

## 8. Rollout sequence and objective acceptance gates

The preparation and offline evaluation artifacts exist. **All application gates below remain pending**; this is a delivery sequence, not a claim that tests have passed. Agree an implementation estimate after the contract/security scope is confirmed.

| Phase | Deliverable | Required gate before progressing |
|---|---|---|
| 0. Confirm evidence and scope | Read this A/B report, architecture and missing-data checklist with the owner | Accept screening-only language; nominate a local operator; confirm no publication; preserve baseline queue and B shadow status |
| 1. Read-only integration | Typed API, release checks, paginated work/payment/term views and dictionary | Exact full-population row/paise reconciliation; every namespaced ID resolves correctly; fixtures cover all cohorts, ID collisions, null/zero and payment statuses; mismatched release fails closed |
| 2. Investigation UI | Dossier, peer/pair provenance, baseline queue and comparison page | Source-to-screen spot checks; A/B rank/membership matches evaluation for 5/10/20% budgets; no hardcoded totals; filters reconcile; empty/error states and keyboard flow work. Measure cold/warm latency on the target device; initial target p95 under two seconds for a 100-row page, with hardware and exceptions recorded |
| 3. Local review workflow | Separate case/evidence store, assignments, state transitions and history | Concurrent/stale-write and idempotency tests; unauthorized transition/scope denial; attachment/path validation; restart persistence; backup/restore demonstration; facts' hashes unchanged after all review operations |
| 4. Supervised shadow pilot | Authorized investigators inspect operational and shadow examples | Independent evidence-based labels with unresolved cases retained; report family/cohort workload and disagreement; no automatic adverse decisions; baseline coverage and time burden reviewed by owner |
| 5. Prospective validation | Approved reviewer study described below | Pre-registration, power/feasibility assessment, consent/permissions, frozen methods and assignment audit; safety/stopping rules agreed before exposing study queues |
| 6. Controlled expansion | Only if evidence and owner approval support it | Demonstrated practical benefit with uncertainty and no unacceptable operational harm; security review and data-governance approval before multi-user/network use |

Cross-cutting tests must include SQL/filter injection attempts, malformed IDs, non-finite amounts, cursor tampering, record-level authorization, hostile review text, spreadsheet formula injection in any approved export, no outbound runtime requests, and no raw/evidence paths served as static assets. Add at least one end-to-end fixture for recommendation-only, completed-without-success-evidence, repeated-report, term-end follow-up and conflicting source stages. Snapshot sums must be checked independently of UI calculations.

## 9. Proposed genuine reviewer A/B study — not yet executed

The offline controlled benchmark cannot establish reviewer effectiveness, money saved or fraud accuracy. A subsequent study should test whether enhanced screening helps investigators substantiate relevant issues within an equal review budget, while protecting routine oversight.

1. **Permission and protocol:** obtain the responsible authority's approval and investigator participation agreement. Freeze A/B method versions, tie policy, eligibility, review budget, outcomes, analysis and stop rules before assignment. Keep legally required or urgent follow-up outside the experiment and handle it identically in both arms; record exclusions.
2. **Pilot for design inputs:** use a separately identified evidence-adjudication/feasibility sample to estimate time per case, finding frequency, reviewer disagreement and within-cluster correlation. Define the smallest operational improvement worth adopting. Calculate sample size and duration from those quantities and expected capacity; no arbitrary fixed study size or synthetic effect is a valid power calculation.
3. **Prevent contamination:** construct linked-work groups, including candidate duplicate pairs and connected open investigations, before randomization. Randomize these groups to A or B, stratified by relevant jurisdiction/cohort and group size where feasible; keep linked works in one arm. If shared reviewers or agencies create substantial spillover, use reviewer-team/authority-period clusters instead and account for them in the design. Predeclare the rule; do not choose the unit after seeing results.
4. **Equal capacity:** use the assigned arm's ranking within its eligible population with equal case-review quotas or a predeclared equal-hour policy. Record actual time and any deviations. Standardize evidence access, case forms and escalation rights. Do not show the alternative queue during the study; keep study cases out of ordinary duplicate assignments.
5. **Independent outcomes:** independent adjudicators assess the same evidence standard, blinded to method when feasible. Record evidence sufficiency, expected variation, source issue, substantiated administrative/financial issue and uncertainty separately. A second reviewer resolves high-impact findings/disagreements; record agreement and unresolved outcomes rather than forcing labels.
6. **Analysis:** compare substantiated issues per fixed review budget and investigator time per substantiated issue, with cluster-aware uncertainty and intention-to-treat assignment. Report evidence completion, unresolved cases, family/cohort coverage, workload, missed mandatory actions, appeals/reversals and reviewer burden. Predeclare minimum practical benefit and harm/non-inferiority margins with the owner. Evaluate sensitivity to missing outcomes; no selective dropping of unresolved cases.
7. **Detection completeness:** reviewed queues alone cannot estimate population recall. If recall/false-negative estimates are required, budget a separate probability sample outside both selected queues for independent adjudication and use sampling weights; do not report recall without that design and adequate evidence.
8. **Decision:** stop for privacy incidents, unsupported adverse actions or unacceptable disruption. Publish only authorized, appropriately de-identified study summaries. Advance B only if the predeclared benefit and safety conditions are met; otherwise retain baseline, diagnose the limitations and preregister a new method evaluation.

## 10. Decisions and missing information to resolve

Before implementation acceptance: confirm the operator and intended stakeholder scopes, authoritative district/IDA mappings, desired review capacity, supported device/browser, evidence-storage policy, and which prototype screens are essential for the first demonstration. Before a live study or predictive modelling: obtain confirmed findings, actual authority receipt/demission dates, approved exceptions, transaction references, quantities/specifications, physical-asset identity/location and repeated event-time snapshots. Their absence does not block a local evidence viewer, but it blocks stronger accuracy, legal-compliance and forecasting claims.

The immediate next implementation milestone is **a tested read-only adapter and complete work dossier**, followed by local case management and a supervised shadow pilot. The current user request covers testing and this plan; implementation, live study and publication remain separate actions.
