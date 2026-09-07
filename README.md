# MPLADS Insight — PS 26102

Complete local research project: reproducible features across the three supplied datasets, an investigation workspace, a plain Excel dataset, architecture/rollout documentation and an honest offline A/B comparison.

## GitHub repository and first-time setup

This repository contains source code, reproducible pipelines, tests and documentation. Raw workbooks, engineered records, Excel outputs, review databases, local hosting metadata and installed dependencies are deliberately **not committed**. The aggregate results below describe the separately verified local delivery; cloning this repository does not include those data files or the prebuilt application.

The existing MIT license applies to the source code. It does not grant rights to any separately supplied MPLADS data.

On Windows, use Python 3.11+ (tested with 3.12) and Node.js 24 LTS:

```powershell
git clone https://github.com/DevAtomicRelease/mplads-prototype.git
cd mplads-prototype
python -m pip install -r pipeline_research/requirements-tested.txt
npm --prefix mplads-prototype ci
```

Obtain the three workbooks through an authorized channel and place them under `Dataset/` at the repository root, retaining these exact names:

- `Works Sanctioned.xlsx`
- `Allocated Limit for Honble MPs.xlsx`
- `Amount consented for Calamity.xlsx`

Then run the complete code/data rebuild without the optional bundled Excel authoring library:

```powershell
powershell -NoProfile -File .\REBUILD_PROJECT.ps1 -SkipWorkbook
.\START_PROJECT.cmd
```

The browser opens at http://127.0.0.1:8765/. No cloud deployment or dataset download is configured. `REBUILD_PROJECT` checks this specific supplied extract's counts and source totals; a different extract requires an explicit data-contract review. The optional final Excel exporter and independent workbook verifier are included as source, but workbook generation additionally requires `@oai/artifact-tool` from the documented local runtime.

The nested `mplads-prototype/` directory is the web app. The repository root also contains its connected data pipeline, A/B experiment and Windows launch controls; retain that structure. The original context file is historical background, with rule corrections documented in `mplads-prototype/SOLUTION_PLAN.md`.

## Open the solution

Double-click **START_PROJECT.cmd**, then open **http://127.0.0.1:8765/**. The app runs only on this computer. Use **STOP_PROJECT.cmd** when finished. Notes remain saved after stopping or restarting.

The delivered static build needs only Python 3.11+ to run; it does not need Node or internet access. The launcher prefers the bundled runtime, then a normal Python installation. Set `MPLADS_PYTHON` if your Python executable is elsewhere. An optional port can be supplied through `START_PROJECT.ps1 -Port 8877`.

## Deliverables

| What to review | Location |
|---|---|
| Final plain Excel workbook | `outputs/01a06d6b-9b94-7a61-b28b-6f9116f20942/MPLADS_Final_Core_Dataset_2026-09-06.xlsx` |
| Architecture, research, limitations and rollout | `mplads-prototype/SOLUTION_PLAN.md` |
| Final verification record | `DELIVERY_VERIFICATION.md` |
| All machine-readable feature tables and field dictionary | `pipeline_research/artifacts/` |
| Raw-data pipeline and regression tests | `pipeline_research/build_features.py`, `test_pipeline.py` |
| Offline A/B report, scores, benchmark and split manifest | `validation_research/` |
| Rebuild equality and original-file hash checks | `validation_research/reproducibility_check.json` |
| Local app source and service | `mplads-prototype/app/`, `lib/`, `scripts/serve_local.py` |
| Local review history | `prototype-local-data/reviews.sqlite3` |

The final core dataset contains 10,000 works with 92 total fields, 543 MPs, 381 authorities, 12 calamity consents, 21,092 candidate pairs and 179 field/table definitions. Source totals reconcile and raw workbooks are unchanged. Earlier Excel files are retained as historical exploratory versions; use the **2026-09-06 core** file with this app.

## A short investigation walkthrough

1. **Portfolio overview:** choose a state and sanction financial year. Summary counts and amounts describe only that selection.
2. **Review queue:** filter by delay, aging, peer cost or duplicate signal. Search by work ID, description, MP or district. Sort and export matching rows.
3. **Work evidence:** open a work. Inspect original fields, dates, peer benchmark and each score contribution. Follow the MP/authority or candidate links.
4. **Duplicate review:** compare both descriptions, dates, amounts, entity evidence and continuation cues. Similarity does not establish duplicate assets.
5. **Record your review:** choose a disposition and add evidence or a next action. Save, refresh and reopen the work. The latest decision persists; earlier saves remain in local history. Review exports are available in the footer.
6. **A/B validation:** switch between 5%, 10%, 20% and 30% review budgets. Inspect the aggregate result, scenario trade-offs and selected real works. Download all held-out scores or the report.
7. **Data & solution plan:** inspect field definitions, rule explanations, source hashes, consents and the rollout plan.

MP/authority profiles show full-extract aggregates. State/year filters choose connected entities; they do not silently recompute profile history. The A/B lab uses a separate frozen held-out population and is independent of the portfolio filters.

## What the validation actually says

A is a fixed delay/aging baseline. B adds historical peer cost and duplicate evidence. Reference records are earlier than the held-out records. At a 20% review budget, the controlled benchmark recovers 37.25% versus 52.75% of scenario-assigned cases: **+15.5 percentage points**, paired 95% interval **+12.0 to +18.25 points**.

This is **not a live randomized trial or fraud accuracy result**. B gains cost/duplicate coverage while losing delay/aging coverage. Real outcomes, false-positive rates and time savings cannot be measured without independently adjudicated labels. The full report describes the frozen design, seeds, uncertainty, unchanged background and prospective trial protocol.

## Rebuild everything locally

Double-click **REBUILD_PROJECT.cmd**. It runs raw ingestion, features, pipeline tests, A/B, independent reruns, equality checks, dashboard/service tests, type checking, the static build and Excel export. It stops on failure. Restart the app after a rebuild. Raw files and review notes are not overwritten.

For code/data rebuilds without regenerating the large workbook, run `REBUILD_PROJECT.ps1 -SkipWorkbook`. Rebuild requirements are Python with NumPy/Pandas plus Node.js 24 LTS and application dependencies. `pipeline_research/requirements.txt` states supported Python library ranges; the validation report records exact tested versions. App versions are pinned in `mplads-prototype/package-lock.json`.

On a new machine, install Python dependencies from that requirements file and run `npm ci` in `mplads-prototype` before rebuilding. Package installation needs internet access but does not upload datasets. Excel regeneration additionally requires the bundled `@oai/artifact-tool` library; its builder uses a local dependency junction. The already-delivered workbook and static app work without that library.

## Data boundaries and operational limits

- The works export is capped at 10,000 rows and contains only **12.75% of its reported sanction value**. It is not complete national coverage or a representative sample.
- Sanctions are not expenditure. Allocation periods, payments, revised estimates, asset dimensions, progress history and fraud labels are absent.
- Recommendation dates proxy IDA receipt. Sanction age proxies duration at the latest sanction date; progress-update dates and MCC exclusions are missing.
- Scores and similar descriptions request investigation. They are not findings of misuse, overpricing, duplicate assets or non-compliance.
- Local review history records a version and source fingerprints. It is application-append-only, not tamper-proof, authenticated or shared across officers. Protect the device and back up the whole project while the service is stopped.
- Source/derived data and notes remain local. Only the audited source code and documentation are published to GitHub; raw and derived records, review notes, hosting metadata and generated artifacts are excluded. No hosting deployment, analytics or external font requests are used. Early scaffold hosting metadata is inactive; it is not an instruction or authorization to deploy.

Before government use: obtain authorized complete sources, approve effective rule versions, add identity/role scopes, secure storage and recovery, run independent adjudication and conduct the prospective trial in the solution plan.

## Troubleshooting and acceptance

If the app cannot load, check `prototype-local-data/server-errors.log`, then use STOP and START. If the port is occupied by another application, select another port; do not stop an unrelated process. If a review fails, the app shows an error rather than claiming it saved. Notes should be exported/backed up as working records, not treated as official audit findings.

Automated checks cover source integrity, joins, totals, score explanations, filters/exports, A/B design, reproducibility, persistence, host/origin guards, compilation and local HTTP. The workbook's summary and representative ranges on every sheet have been rendered and inspected. A browser click-through acceptance check is still a user/pilot task; no automated browser end-to-end test is claimed.
