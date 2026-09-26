# Implemented architecture and rollout — PS 26102

Status: local investigation prototype; no production or fraud-accuracy certification.
This document supersedes implementation claims in earlier design proposals.

## Data and decision flow

```text
18 immutable CSV exports (6 types × 3 cohorts)
  → hash/schema contracts + invalid-row quarantine
  → namespaced work master + payment ledger + source row references
  → lifecycle / historical cost / text / payment / entity features
      ├─ 10 explained rules → capped priority score + review bands
      ├─ Isolation Forest + DBSCAN → separate atypicality signals
      └─ monthly settlements → chronological baseline/mean forecast
  → 21 reconciliation checks + controlled benchmark + regression tests
  → sealed CSV / SQLite / reports / workbook release
  → atomic active-release pointer
  → loopback Python API → React investigation frontend
                          → independent append-only review ledger
```

The implementation uses Python/pandas, a vendored deterministic Isolation Forest,
scikit-learn DBSCAN, SQLite and a React/Vite/Recharts interface. It is not the proposed
cloud microservice/GNN/LLM architecture from early planning documents. At this data
volume, an indexed local database and batch release are sufficient and inspectable.

## Joining the sources without multiplying money

| Source | Grain and use |
|---|---|
| 01 allocated limit | Cohort/MP allocation context; allocation-only MPs remain visible. |
| 02 calamity consent | Consent context; absence does not establish prohibited work. |
| 03 recommended | Recommendation identity, purpose, amount and date. |
| 04 sanctioned | Sanction identity, amount and date; union with recommendations forms the master. |
| 05 completed | Reported completion evidence linked to work; not proof of physical assets. |
| 06 expenditure | Individual reported payment rows; successful and in-progress amounts remain separate. |

Rajya Sabha identifiers are reused across MPs, so a work key includes cohort, MP key
and source work ID. Preserve source row references and missingness. Aggregate payments
at work grain before joining to the one-row-per-work table; never sum sanctions after
a one-to-many payment join. Store money in integer paise; display rupees/crore with
explicit conversions. Identical payment rows remain reported evidence, with a separate
one-row-per-fingerprint sensitivity, not an invented “corrected” total.

Current inventory: 160,701 works; 113,691 accepted payment rows; one quarantined row;
1,023 MP records; 1,045 authorities; 34,242 vendors. The complete derived dataset is
13 CSV tables plus indexed SQLite. See the release audit for exact reconciliations,
all source hashes and coverage. The assessment date is fixed at 2026-09-14, not today.

## Features, scores and limits

- Lifecycle: recommendation-to-sanction delay, open age, missing observed payments,
  reported completion. Receipt dates, contractual deadlines and extensions are absent;
  elapsed-day checks are monitoring proxies, not proven statutory breaches.
- Cost: comparisons use strictly earlier financial-year peers with minimum support
  and fallback grouping. Scope, quantities and unit rates are absent. A higher amount
  may reflect a legitimately larger work.
- Similarity: bounded same-authority/activity text candidates, guarded by number,
  phase/repair and generic-description cues. An exact text/amount index supplements
  crowded candidate blocks. Retained pairs prioritize stronger evidence, but bounded
  search can miss pairs. No measured real duplicate recall or asset-location proof.
- Financial patterns: successful payments relative to sanctions, repeated reports,
  March concentration, vendor links and authority/year HHI. HHI is descriptive;
  specialization, small denominators or coverage can explain high concentration.
- Score: sum of reason-code points capped at 100. Routine=0, Low=1–19, Medium=20–39,
  High=40–80, Critical=81–100. These are priority bands, not probabilities; a score of
  60 does not mean a 60% chance of fraud. Current snapshot has 6,641 High-band works;
  Critical is empty (highest observed score is 64). Two screens — payments over sanction
  and completion over sanction — flag zero works in this extract because no reported
  settlement or completion amount exceeds its sanction. They remain active, are tested on
  constructed cases in the A/B benchmark, and are shown as "0 — not observed" in the
  rule registry rather than hidden.
- ML: Isolation Forest percentile and DBSCAN noise flag remain separate from rules.
  They fit the retrospective feature snapshot; diagnostics are descriptive/in-sample,
  not future prediction evidence. No supervised fraud model is trained without labels.
- Forecast: use complete observed pre-snapshot months, select last-month vs trailing
  three-month mean on earlier rolling validation folds, reserve the final three months
  for rolling one-step tests. Missing months suppress forecasting rather than being
  silently zero-filled. This forecasts aggregate reported settlement, not fraud,
  physical progress or remaining liability. Reporting revisions are unknown.

Field definitions, transformations and caveats are available in Data & research and
Feature_Dictionary.csv. Unavailable SC/ST tags, receipt dates, trust eligibility,
GPS, photos, quantity schedules and physical progress are not reported as passed.

## Frontend and serving contract

The launcher serves the compiled frontend and /api on the same loopback origin.
All normal investigation, review, report access and maintenance controls are in the
frontend. The browser cannot start an absent operating-system service; START.cmd
performs that one initial action. It checks raw/artifact/code freshness and dependency
pins, builds if necessary and waits for health before opening the page.

API SQL is read-only and parameterized; the natural-language parser chooses bounded
templates rather than accepting arbitrary SQL or contacting an LLM. Security measures
include loopback binding, Host validation, same-origin write checks, a CSP and an
allow-list of maintenance actions. There is no officer authentication or authorization
system. Do not bind the service to a public/LAN address or treat this as multi-tenant.

### Presentation and investigation modules

- `components/ui/table.tsx` supplies search, 50-row pages, counts and a bounded
  one-based **Jump to page** control. Small evidence tables search their complete
  supplied row set. Large tables opt into server mode: API search applies before
  counting/paging, escapes literal wildcards and uses deterministic tie ordering.
  Search resets pagination; a no-match state keeps the search control available.
- `six_source/entities.py` and `/api/entity` return exact-key authority, member and
  vendor profiles. Sanction totals aggregate unique works, never payment-join rows.
  Vendor-only payments are distinguished from totals for connected works. Overview,
  concentration and supported query results open the profile; opening its work queue
  is a separate explicit action. Authority labels are not geocoded district boundaries.
- `six_source/nlq.py` resolves full entity names and bounded authority aliases, asks
  for a choice on ambiguity, and returns SQL/parameters and stable drill-down keys.
  Unsupported requests and loaded allegations remain refused. This is a local
  deterministic parser, not general natural-language reasoning or an external LLM.
  Supported signals: high-priority, open >1 year, pending recommendation >45 days,
  sanction delay >45 days, no payment after 3 months, cost outliers, similar works,
  repeated payment reports, March concentration, completed without observed payment,
  payments/completion over sanction, settled/pending/sanctioned amounts, average
  sanction per work, settled ratio and completion rate. "How many"/"total" questions
  without a grouping return one national or filtered number; top-N limits are read only
  from ranking phrases ("top 5", "10 districts"), never from durations or years; short
  financial years ("2024-25") filter sanction year and unknown years are refused; a
  "most X" ranking lists only groups with any X and says "None found" when X is absent.
- `app/india-map.tsx` draws bundled geoBoundaries/DataMeet ADM1 geometry locally,
  with no remote tiles or data transmission. All 36 snapshot state/UT labels match.
  Color encodes High-band works / connected works, with numerator, denominator,
  missing-data legend, keyboard selection and an equivalent dropdown/table.
  `public/india-map-provenance.json` pins source, license, commit and SHA256.
  Publisher metadata says 2011 although separate Telangana/Ladakh and 36 units are
  present. This is an illustrative administrative map, not certified current Survey
  of India geometry or a statement on disputed boundaries; official use needs review.
- `app/report-view.tsx` and `lib/report-table.ts` render controlled local reports as
  escaped headings, paragraphs, lists and searchable tables. Fixed-width parsing
  preserves multi-word labels, financial years and signs; ambiguous blocks remain
  verbatim instead of dropping rows. No report HTML is executed.
- Insights labels forecast currency, series and periods and shows the last 12 rolling
  folds plus validation/test errors. A/B uses six sections: methods, workload/results,
  mechanisms, sensitivity/separate ML, reproducible evidence, and limits. Research
  uses five: coverage, feature pipeline, sources, dictionary, and evidence gaps.

Charts disclose incomplete periods and units; every active data table has search and
page controls. Table scope is explicit: a top-20 list is not a search of all authorities;
use Entities for that. Full local downloads remain available for independent review.

## Release safety, review persistence and reproducibility

New builds go to six_source/releases/<id>. A manifest records artifact and pipeline
code hashes. Required outputs, SQLite integrity, reconciliation and tests are checked
before a same-volume atomic pointer replacement in six_source/local/active_release.json.
Readers resolve one release per request. Failed preparation leaves the previous pointer
unchanged. Historical releases are retained; they are not copied into a live database.

An OS file lock prevents concurrent maintenance across processes; frontend job status
and full logs explain failures. Source and artifact checks run at startup and in project
status/preflight. The release directory is application-immutable, not protected against
a malicious local administrator. Hashes are integrity evidence, not digital signatures.

Review data lives separately in six_source/local/reviews.sqlite3. Each entry includes
work key, analytical version, disposition, note, owner label, due date and case status.
Writes with an obsolete displayed version return a conflict instead of silently filing
against another release. Historical reviews remain readable after switches. This is
append-only application history, not an authenticated or tamper-proof government audit.
Back up the review database while the service is stopped, alongside its release manifest.

Independent reproduction rebuilds all features from original inputs and compares actual
bytes for all 13 exported feature CSVs, not merely stored hash manifests. Its versioned
report and test result stay outside immutable releases. Workbook/SQLite binary identity,
cross-platform floating-point identity and a live-data refresh SLA are not promised.

## Validation and research basis

The production-rule A/B benchmark contains injected mechanisms and legitimate exceptions.
It is versioned development evidence, revised after inspection. Complete generated
contexts are resampled together (including both duplicate endpoints), conditional on
their fitted scores. Shared construction, full-snapshot ML fitting and small scenario
families limit inference. Equal capacity can mean unequal actual review workload.
Read README and the generated ab_metrics.json for the current results and limitations.

The separate forecasting experiment uses forward-time evaluation, consistent with the
[scikit-learn cross-validation guidance](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split).
The existing research registry exposed by Data & research retains the official MPLADS
sources and feature-specific cautions. Scheme rules must be reviewed by the responsible
authority against the applicable guideline edition before operational enforcement.

## Rollout gates

1. **Local demonstration:** fixed authorized snapshot, traceable counts, complete review
   walkthrough, passing release tests and independent feature reproduction. This is the
   deliverable implemented here, not an autonomous fraud adjudicator.
2. **Authorized shadow pilot:** agree data rights, custodians, sampled districts and review
   capacity. Freeze a protocol before scoring; obtain blinded independent adjudication,
   sample unflagged controls, separate investigators where feasible, track time per case,
   evidence quality, false-alert burden, subgroup/coverage differences and uncertainty.
   Prevent a work/authority family leaking between training and held-out evaluation.
3. **Operational acceptance:** independently validate value over the baseline under actual
   workload constraints. Agree escalation/appeal processes and human responsibility.
   Only then consider supervised ranking from adjudicated labels, with calibration,
   forward-time validation, drift monitoring and rollback criteria.
4. **Production engineering:** approved MIS integration and incremental source contracts,
   authenticated roles/SSO, least privilege, encrypted storage/backups, durable job queue,
   tamper-evident audit logs, retention/deletion policy, accessibility/load/security tests
   and disaster recovery. These need external authority and are not completed here.

Computer vision needs authorized images and ground truth; collusion inference needs
verified ownership/relationship evidence. Adding a GNN, LLM or deep model without those
inputs would not resolve the current evidence gaps.
