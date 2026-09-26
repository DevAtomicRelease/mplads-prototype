# MPLADS-GUARD — PS 26102

A local investigation prototype for MPLADS expenditure, work execution and review.
**A priority score is a request for evidence, never a finding of fraud.**
The current release connects all six export types across three cohorts (18 CSV files).
Raw records, generated outputs and review notes stay on this computer.

## 1. Start and stop

1. Install Python 3.12 and Node.js 22.13 or newer, available on PATH.
2. Keep the authorized source files in the three folders below.
3. Double-click **START.cmd**. Leave its window open.
4. Wait for “MPLADS-GUARD is ready”. The launcher opens **http://127.0.0.1:8766/**.
5. To stop, double-click **STOP.cmd** or press Ctrl+C in the launcher window.

First setup downloads dependencies. A missing/stale data release takes several minutes
to rebuild. Subsequent starts reuse verified outputs and work offline. No Docker,
database installation, API key or separate frontend/backend terminal is needed.

Expected screen: Overview shows **160,701 works**, **6,641 High-band reviews**,
**₹7,998.31 crore sanctioned**, and **₹4,592.56 crore reported settled**, assessed
as of **14 September 2026**. “Members with works” is 962; the allocation-inclusive MP
table contains 1,023 records. These are coverage counts, not verified national completeness.

Required folders:

```text
Dataset/
  Lok Sabha/
  Rajya_Sabha_sitting/
  Rajya_Sabha_retired/
```

Each must contain 01_allocated_limit.csv, 02_calamity_consent.csv,
03_works_recommended.csv, 04_works_sanctioned.csv, 05_works_completed.csv and
06_expenditure.csv. Do not edit raw files to satisfy a check. Changed inputs require
an authorized, reviewed update to the frozen source contract.

Optional PowerShell commands from this folder:

```powershell
.\run.ps1 -Port 8770       # alternate port
.\stop.ps1 -Port 8770      # stop that recorded instance only
.\run.ps1 -NoBrowser       # start without opening a browser
.\run.ps1 -Rebuild         # force a complete verified release
```

## 2. Use the frontend

| Screen | What to do / what it means |
|---|---|
| Overview | Read totals and the India heatmap. Select a state/UT, then click an authority name to open its profile, reasons and year breakdown. The latest payment month is incomplete. |
| Ask the data | Try “Which districts in Bihar have the most delays?” Read the interpretation, SQL and caveat. This is a bounded local question parser, not an LLM. Unsupported requests are refused. |
| Work investigation | Filter state, year, lifecycle, signal, cohort and band. Open a work for dates, payments, reason codes, cost peers and similar descriptions. |
| MP view | Search members and page through results. Inspect progress, spending and missing compliance evidence. |
| Entities | Search full MP, authority and vendor profiles; inspect the underlying records. |
| Similar works | Compare candidate descriptions and amounts. A text match is not proof of duplicate assets. |
| Review register | Find assigned cases, due dates and status; reopen a work. History survives releases. |
| Insights & forecast | Inspect authority-year vendor concentration, connected-data findings and an experimental payment forecast with chronological backtests. |
| A/B validation | Change review capacity; compare recovery, actual workload, false alerts and uncertainty. Download all metrics and seed checks. |
| Data & research | Read source coverage, limitations, research and field definitions. |
| Project status & tools | Check integrity, run tests/reproduction/release jobs, read logs, get help and download reports. |

**Review a case:** open a work → inspect evidence → enter disposition, evidence note,
owner, due date and status → save → check Review register. Entries are append-only
and version-linked. Owner is a label, not an authenticated identity. “Closed” is a
workflow state, not exoneration or a fraud verdict.

Use anonymized/example notes during a demonstration, or an isolated review database.
Do not turn a demonstration into an allegation against a real person.

### Quick check of the refined interface

1. In Overview, select **Uttar Pradesh** on the map or dropdown. Open **JAUNPUR**
   in the authority table: its profile should show 2,248 connected works and 283
   high-priority works. Use **View this entity's connected works** only when you
   want the investigation queue.
2. In Ask the data, enter `JAUNPUR(DISTRICT MAGISTRATE JAUNPUR_IDA), give me details on this.`
   The answer includes the exact authority and a full-profile action. Named-entity
   rankings also link to exact profiles; ambiguous names require a choice.
3. Every table has search and **Jump to page** followed by **Go**. Large lists search
   all matching records, not just the visible page. Small summary tables search only
   their stated scope (for example, national top 20). Clear search to restore rows.
4. In Insights & forecast, read the three-series chart in INR crore, separate test
   errors, concentration search and structured connected-data report.
5. In A/B validation, follow sections 1-6: methods, results/workload, mechanisms,
   sensitivity and ML, evidence/reproduction, then limits. Change capacity to compare
   workload, not just recovery. No outcome here establishes real fraud accuracy.
6. In Data & research, follow sections 1-5. In the dictionary, jump to page 6 to see
   entries 251-292; searching `paise` resets the table to its matching entries.

## 3. Test from the frontend

Open **Project status & tools → Tools**:

1. **Run invariant and end-to-end checks** — 49 regression tests, including financial
   reconciliation, query safety, review persistence and release switching. Tests use
   temporary review databases and do not add test notes to the real ledger.
2. **Independent rebuild and reproducibility check** — rebuilds in a separate folder;
   success means all 13 feature CSVs match byte-for-byte. This is not a claim that
   every binary workbook/SQLite file has identical bytes.
3. **Re-run offline A/B validation** — creates and activates a separate analytical
   release; it never overwrites a release being read.
4. **Generate the Excel review workbook** — staged refresh; the workbook is a review
   summary (top 1,000 works and top 500 vendors), not the full data export.
5. **Build, validate and activate a new release** — full source verification,
   engineering, validation, forecasts, workbook and regression checks.

Only one maintenance action runs at a time across processes. Jobs show completion or
failure and expandable logs. Keep the service running during a job. Refresh the page
after release activation. Old test/reproduction evidence is not shown as current
for a different release; rerun the checks when needed.

Full data exports, reason contributions, concentration, forecasts, source/audit hashes,
the A/B report and the Excel review workbook are in **Downloads**. Use CSVs for the
complete analytical dataset; SQLite is the indexed local serving store.

## 4. What the A/B result establishes

This is an **offline development benchmark**, not a randomized officer trial or
independent fraud-accuracy validation. Synthetic source-shaped mechanisms and
legitimate exceptions pass through the real feature functions and rule engine.
The benchmark and duplicate retrieval were revised after inspection.

Seed 26102: 1,440 evaluation works, including 120 injected positive cases.

| Review capacity | A recovery | B recovery | Actually reviewed A / B | False alerts A / B |
|---|---:|---:|---:|---:|
| 5% (72 maximum) | 40% | 40% | 72 / 72 | 24 / 24 |
| 10% (144 maximum) | 60% | 90% | 96 / 144 | 24 / 36 |
| 20% (288 maximum) | 60% | 100% | 96 / 156 | 24 / 36 |

A uses operational/payment rules. B adds historical-cost, similar-description and
year-end-payment rules. Both use production weights and work-ID tie ordering.
Zero-score fillers are not reviewed, so equal capacity is **not equal actual workload**.

At 10%, both methods yield 75% injected findings per review; B reviews more cases.
The paired context-bootstrap recovery difference is **−1.7 to +40.0 percentage
points** (95%, conditional on fitted synthetic scores), so this interval includes
zero. It is not an interval for real fraud detection. Seeds 26103/26104 are sensitivity
checks, not external validation. Real-data queue overlap measures disagreement,
not correctness. Isolation Forest and DBSCAN diagnostics are separate, in-sample
and not calibrated probabilities.

The forecast chooses between last-month and trailing-three-month means on earlier
validation months, then evaluates three later months. Test MAE is ₹56.65 crore for
the baseline versus ₹43.34 crore for the selected mean. Three test months are too
few for a production claim. September is excluded from training; the projection
is for the **full month**, not remaining expenditure.

## 5. If something goes wrong

| Symptom | Action |
|---|---|
| “Local data service unavailable” | Start START.cmd and use its printed URL. Opening frontend files or a preview server alone does not start the data service. |
| Old screen / blank results | Use the launcher URL, not an old development tab; refresh after a build. |
| Port already used | Use an alternate port. The launcher never kills an unrelated process. |
| Missing Python / Node | Install the prerequisites above, reopen the terminal, then launch again. |
| Source hash mismatch | Keep the raw export unchanged. Restore the authorized exact input or review/update the data contract; do not bypass verification. |
| Job failed | Expand its log in Tools. The previous release and review history are retained. |
| Old review after a rebuild | Intentional: it remains attached to the version reviewed. Reassess against current evidence before adding a new entry. |
| Stop refuses process identity | It refuses to kill a process that cannot be verified as this project. Check the original launcher; do not kill arbitrary Python processes. |

## 6. Architecture, readiness and development

See [ARCHITECTURE.md](ARCHITECTURE.md) for the implemented pipeline and rollout gates,
and [SUBMISSION_GUIDE.md](SUBMISSION_GUIDE.md) for the demonstration and acceptance checklist.
Older plans remain historical references, not implementation claims.

Developer checks (optional; normal users use the frontend):

```powershell
.\.venv\Scripts\python.exe -B six_source/maintenance.py tests
.\.venv\Scripts\python.exe -B six_source/maintenance.py reproduce
.\.venv\Scripts\python.exe -B six_source/prepare_release.py
.\.venv\Scripts\python.exe -m pip check
```

In mplads-prototype: run npm ci, npm test (four report-parser regressions),
npm exec -- tsc --noEmit, npm run lint and
npm run build. For hot reload, npm run dev proxies /api to the running service
on port 8766. The launcher serves dist/index.html; legacy.html is archived.
Do not run individual build scripts against an active release.

**Local research prototype, not production certified.** No officer authentication,
live MIS integration, adjudicated real-world accuracy, physical asset verification
or government endorsement is claimed. Missing evidence is unavailable, not passed.
The bundled map matches all 36 state/UT labels but is not certified current official
boundary geometry. Its provenance and inconsistent publisher vintage metadata are
disclosed beside the map; tables remain the authoritative source-labelled view.

Source code is MIT licensed. Dataset inclusion does not establish redistribution
rights. The runtime uses loopback, same-origin write checks, allow-listed jobs,
read-only analytical SQLite and an independent review ledger. Never expose this
unauthenticated prototype to the internet. No raw records or reports were published
as part of this completion work.
