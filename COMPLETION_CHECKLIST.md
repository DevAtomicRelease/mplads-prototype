# Local prototype completion

Scope: SIH PS 26102, local MPLADS investigation prototype. Preserve raw data and existing review records. No publication, push, or claim of proven fraud accuracy.

## Implementation sequence

- [x] Complete atomic release activation, per-request version consistency, integrity verification, and serialized maintenance jobs.
- [x] Add regression tests for interrupted activation, changed artifacts, release switching, review persistence, and unsupported queries.
- [x] Implement frontend operations, investigation/review workflow, concentration, experimental forecast, and chart/data limitations.
- [x] Align benchmark scoring/ties with production; report synthetic development limitations, workload, false alerts and separate in-sample ML diagnostics.
- [x] Align startup, architecture, testing, and submission documentation with the implementation.
- [x] Run isolated tests, type checking, lint, production build, independent data reproduction, and browser checks.

## Executed verification (25 September 2026)

- Active analytical release: `20260924T191600-860c6c62`; source assessment date `2026-09-14`.
- 18 source files verified; 21 reconciliation checks pass; 160,701 unique work records.
- Independent complete feature build: all 13 exported feature CSVs byte-identical.
- Regression suite at that check: 39 checks. Test notes use disposable databases only.
- Frontend type checking, lint and production build pass; Python dependency consistency passes.
- Production npm audit reported zero vulnerabilities at check time; this is not a security certification.
- Windows launcher reuse/start and identity-checked shutdown tested on port 8770;
  no listener remained after shutdown. Canonical service is port 8766.
- Browser: overview totals/charts; evidence drawer and close control; isolated owner/status/
  due-date save and cross-release history; case register; supported local query; A/B capacity
  changes; forecast chart and concentration table; frontend test action, disabled controls,
  completion/log display; mobile navigation and forecast at 390px.
- Fixes discovered by browser QA: date input lost its value on focus change; mobile menu
  stayed open after navigation; unrelated query fell back to work-count rankings.
- Spreadsheet read-only inspection: 8 sheets imported, no matched formula-error cells;
  overview, priority and A/B previews examined. Long IDs/names and overview labels are
  clipped at default Excel widths. Values remain intact; use the frontend/full CSVs or
  expand columns. This export-format polish remains, and native Excel testing was not run.

## Frontend refinement verification (25-26 September 2026)

- [x] All 49 backend regression checks pass, including exact/ambiguous authority
  queries, ranked-entity drill-down keys, profile aggregation at unique-work grain,
  server-wide search, literal wildcards, stable pages and all 36 geometry labels.
- [x] Four frontend report-parser tests pass: multi-word labels, financial years,
  signed values, series headings and lossless fallback for malformed blocks.
- [x] Type checking, lint and production frontend build pass.
- [x] Browser: India map and legend render; Uttar Pradesh selection filters authority
  context; all 36 labels match. Map provenance and vintage caveat remain visible.
- [x] Browser: Overview Jaunpur opens its profile, not the queue. The exact reported
  Jaunpur question returns 2,248 works / 283 high-priority and opens the same profile.
- [x] Browser: ranked authority answer opens the matching Dumka profile (861 connected
  works, 729 open beyond one year), retaining the exact entity key.
- [x] Browser: dictionary page 6 shows 251-292 of 292; `paise` search returns 35
  entries and resets page. Concentration page 52 shows 2551-2551 of 2,551; an unknown
  authority search shows no matches, and clearing/replacing search restores results.
- [x] Browser: forecast legend, INR crore axis and 12-fold view render; report has
  five structured tables rather than raw fixed-width blocks. A/B capacity changes
  update recovery, actual workload and uncertainty; methods/evidence/limits are separate.
- [x] README walkthrough and implemented architecture describe profiles, search,
  report rendering, map provenance and truthful benchmark interpretation.
- [x] Final browser smoke check at 390px: mobile navigation closes after selection,
  A/B sections and page-jump controls fit without document-wide horizontal overflow;
  wide tables scroll within their own container. Dark-mode explanatory text contrast
  was fixed and rechecked. New pages now start at their heading. No captured browser
  error logs in the tested session. This is not a comprehensive accessibility audit.

Active release remains `20260924T191600-860c6c62`. Startup preflight reverified raw and
release integrity. The complete 13-CSV rebuild evidence above is from the earlier
25 September check, not a second reproduction claimed for this presentation pass.
No real review notes, raw source rows or sealed release artifacts were changed.

## Non-blocking polish / remaining acceptance work

- Improve workbook wrapping/widths and include workload/false-alert columns in its A/B
  summary; the complete truthful metrics already appear in the frontend/JSON/README.
- Optimize the approximately 842 kB JavaScript bundle (258 kB gzip; build warns above 500 kB).
- Replace or formally approve the illustrative map before an official government
  deployment. Its 36-label coverage does not certify boundary correctness or vintage.
- Reconcile old presentation decks with the current implementation before submitting them.
- A full accessibility audit, all browser/device combinations, load testing and native Excel
  behavior are not certified by the smoke checks above.

## External acceptance requirements

An authorized officer pilot, independently adjudicated real cases, live MIS integration, and production security approval require external access or decisions. They are not prerequisites for an honestly scoped local prototype and must not be represented as completed.
