# Submission and demonstration guide — PS 26102

## Honest submission claim

“MPLADS-GUARD is a reproducible local decision-support prototype connecting six types
of MPLADS exports across three cohorts. It prioritizes explainable review signals,
provides separate unsupervised atypicality views and experimental payment forecasts,
and records version-linked human follow-up. It does not establish fraud.”

Submit as a working local prototype, not an approved production system. No arbitrary
completion percentage or fraud-accuracy score is defensible without an officer pilot.

## Suggested 8-minute demonstration

1. Launch START.cmd. Explain that records stay local and the assessment date is fixed.
2. Overview: show 160,701 connected works, cohort coverage, reported settlements and a
   state rate with its denominator. Explain the incomplete final payment month.
3. Investigate a state/authority. Open a work and trace its priority to reason-code
   points, lifecycle dates, payment rows, prior-year peers and source row references.
4. Show a similar-description candidate and explain why different locations/phases
   still require evidence. Do not describe a named person as fraudulent.
5. Save an explicitly marked demonstration review in an isolated review store; show
   owner, date, status and history. For a real ledger, demonstrate read-only instead.
6. Ask a supported data question; show the exact interpretation and SQL. Show that an
   unsupported request is refused rather than invented.
7. A/B validation: choose 10%. Explain 60% vs 90% synthetic recovery, but 96 vs 144
   reviews, 24 vs 36 false alerts, and a conditional interval that includes zero.
8. Insights & forecast: show concentration caveats, chronological test predictions and
   the three-month test limitation. Finish at status, tests, reproduction and downloads.

## Acceptance checklist

- All 18 original CSVs present and unchanged; one invalid source row quarantined.
- Reconciliation totals agree with dashboard, exports and source audit.
- Evidence drawer opens and closes; filters, pagination and search work.
- Review saves preserve owner/date/status and survive release changes; stale writes fail.
- UI offers tests, A/B rerun, workbook, independent reproduction and release preparation.
- Job errors and logs are visible; no overlapping maintenance or partial release switch.
- Type checks, lint, production build and regression suite pass.
- All 13 feature CSVs reproduce byte-for-byte from original data.
- A/B results include workload and false alerts; ML diagnostics are separate.
- Forecast excludes the snapshot month and does not train on its target month.
- README lets a teammate start, test, use and stop without separate service commands.

The completion checklist records executed checks. Re-run frontend tests/reproduction
after preparing a different release; do not reuse another release's pass status.

## Submission materials and privacy

Share source code, README, architecture, this walkthrough and evaluation methodology.
Keep Dataset/, local/, releases/, generated workbooks/CSVs, review notes and screenshots
containing identifiable records private unless the data owner authorizes publication.
Use an approved local package or sanitized demonstration data for assessors; the public
code repository alone does not include the authorized datasets needed to run this snapshot.
Older slide decks and early plans may contain stale numbers; use current release exports
as the authority and reconcile any presentation before uploading it.

## Remaining external requirements

Independently adjudicated cases, a prospective officer pilot, data-sharing authorization,
live MIS access and production security approval remain external acceptance gates.
Physical asset verification, missing compliance evidence and authenticated role access
cannot be supplied honestly from the current CSVs alone. The current bundle-size warning
is a performance optimization item, not evidence of model correctness or a failed build.
