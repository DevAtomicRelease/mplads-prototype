# MPLADS-GUARD — SIH 2026 PS 26102

A **local** AI/ML platform that reads MPLADS financial and project-execution data and surfaces **anomalies, fraud signals and inefficiencies** as explainable, risk-ranked, human-reviewable cases — for Members of Parliament, State Nodal Authorities, District Authorities and the Ministry (MoSPI).

> **Design law:** no score here is a finding of fraud. Every alert is a *request for evidence and human review*. Checks with no supporting data (physical progress %, SC/ST tags, trust register, GPS, asset photos) are shown as **visibly unavailable, never silently passed**. No data leaves the device.

---

## Quick Start

**Prerequisites**
- **Python 3.12** on PATH (tick "Add Python to PATH" in the installer).
- **Node.js 22+** on PATH — needed only the first time, to build the web interface.
- The **dataset**: six CSVs per cohort under `Dataset/` (already present in this folder):
  `Dataset/Lok Sabha/`, `Dataset/Rajya_Sabha_sitting/`, `Dataset/Rajya_Sabha_retired/`, each with
  `01_allocated_limit.csv … 06_expenditure.csv`.
- First run needs **internet** (to download Python/Node packages). After that it runs **offline**.

**Launch (one action)**
- Double-click **`START.cmd`**, or in PowerShell from this folder run:

```powershell
.\run.ps1
```

The launcher checks prerequisites, builds the dataset and interface **only if missing or stale**, starts the local service, and opens your browser **when it is actually ready**.

**Open:** http://127.0.0.1:8766/

**Expected successful screen:** a dark‑sidebar app titled **MPLADS‑GUARD**, opening on **Overview** with headline cards — *Connected works 1,60,701*, *High‑priority reviews*, *Sanctioned ₹7,998.31 cr* — a top‑states chart, an India risk map and a state table. The top bar reads *"Local processing · review signals, not findings of fraud."*

**Stop:** press **Ctrl+C** in the launcher window, or double‑click **`STOP.cmd`**.
**Restart:** run `.\run.ps1` (or `START.cmd`) again — it reuses the existing build and starts in seconds.

Options: `.\run.ps1 -Port 8770` (different local port) · `.\run.ps1 -Rebuild` (force a fresh dataset build) · `.\run.ps1 -NoBrowser`.

---

## Using the app — frontend walkthrough

1. **Overview** — national KPIs, per‑cohort cards, top‑states chart, monthly settled‑payments trend, an **India state‑risk map** (hover for detail; click a state to see its district authorities) and a state heatmap. "Investigate" opens the filtered work queue.
2. **Ask the data** — type a plain‑English question (e.g. *"Which districts in Bihar have the most delays?"*). It is answered **entirely locally** — no external service — and shows an interpretation, a table, the **exact SQL** used, and a caveat. It refuses fraud/corruption‑framed questions and says so when it can’t map a metric.
3. **Work investigation** — the case queue. Filter by state, financial year, lifecycle or an investigation **signal** (open beyond one year, cost outlier, year‑end rush, duplicate, DBSCAN outlier, …), sort, and open any work.
4. **MP view** — look up a member: allocation and utilisation, a work‑progress funnel, a traffic‑light workload summary, an honest "unavailable, not passed" compliance panel, and their flagged works.
5. **Entities** — full‑extract profiles for MPs, district authorities and vendors.
6. **Similar works** — near‑duplicate description candidates with guard flags.
7. **A/B validation** — the offline screening comparison (see below).
8. **Data & research** — source coverage, evidence limits, research and the feature dictionary.
9. **Project status & tools** — dataset inventory & source verification, financial/lifecycle summary, reproducibility & test status, **downloads**, **methodology** (rule registry, limits, research), **Help**, and **Tools**.

### Investigate a work, inspect evidence, save a review, download reports
- Open **Work investigation**, filter/search, and click a work to open its **evidence drawer**: lifecycle dates, a financial reconciliation, the **reason codes** that put it in the queue (each with a required caution), a historical cost comparison, the payment ledger and similar‑work candidates.
- **Save a review:** in the drawer choose a disposition (*Needs evidence · Expected variation · Data issue · Substantiated issue*), write an evidence note, and save. Reviews are stored **locally**, tied to the dataset version, **preserved across rebuilds**, and never uploaded.
- **Download reports:** on **Project status & tools → Downloads**, get the Excel review workbook, the feature CSVs, the audit/hash manifest, the A/B report and CSVs, and the reproducibility manifest.

### Run frontend checks and understand the results
On **Project status & tools → Tools**, each button starts a background job on this machine (this is *computation*, distinct from viewing existing results). One job of each kind runs at a time; a running button is disabled and duplicate requests are refused.
- **Run invariant and end‑to‑end checks** — the test suite (green = all invariants and API endpoints hold for this build).
- **Re‑run offline A/B validation** — regenerates the A/B result.
- **Generate the Excel review workbook**.
- **Independent rebuild and reproducibility check** — rebuilds into a separate directory and compares hashes; writes the reproducibility manifest.
- **Build, validate and activate a new release** — see *Releases* below.

Each job shows queued/running/completed/failed, a progress bar, timestamps and its last log line.

---

## Validation (A/B) — how the screening is tested

Two evidence layers, no fraud‑accuracy claim (there are no adjudicated labels):
1. **Controlled mechanism benchmark on the real pipeline** — synthetic *source‑shaped rows* (a prior‑year peer background, labelled positive mechanisms, **legitimate‑exception negatives** and difficult negatives) run through the **actual build feature functions and rule engine**; the **actual queue** is then measured at equal review budgets (recovery, findings‑per‑review, false‑alert burden — all over one reviewed set), with a paired bootstrap 95% interval. Baseline **A** = operational/payment screens; enhanced **B** adds cost‑outlier, near‑duplicate and year‑end screens.
2. **Real retrospective queue comparison** — A vs B ranking of the actual built works, reported as an **unweighted top‑k set overlap**. No accuracy claim.

Representative result (seed 26102): **0 of 1,284** legitimate‑exception/hard negatives are flagged; at a 10% budget **B recovers ~83% vs A ~60% (+23 pp, 95% CI ~16–31)** with zero false alerts. The evaluation is **not tuned to make B win** — it may lose at any budget.

---

## Releases, reviews and reproducibility

- **Raw sources are immutable**; the build fails closed if any source hash differs from its frozen contract, and refuses to serve a **stale** build.
- **Prepare a new release** builds into an isolated `six_source/releases/<timestamp>/`, validates it completely, and only **activates** it (copies into `local/`) if every step passes — the previous working release is **retained on failure**.
- **Reviews are independent**: `reviews.sqlite3` is never overwritten by a rebuild and stays tied to its dataset version.
- **Reproducibility**: `reproduce.py` rebuilds into a separate directory and confirms every build artifact is byte‑identical (13/13), writing `reproducibility.json`. Fixed seed 26102.

---

## Troubleshooting

| Symptom | Cause & fix |
|---|---|
| Page says **"The local backend is not responding"** | The service isn’t running. Start it with `run.ps1` / `START.cmd`, then reload. (The page cannot start it for you.) |
| Browser opens an **old/different UI** | You opened a stale dev server. The app is served by the launcher at **http://127.0.0.1:8766/**. `index.html` is the current app; `legacy.html` is the archived one and is never the default. |
| **"Port 8766 is already in use"** | Another program holds the port. Re‑run with `-Port <number>` (e.g. `.\run.ps1 -Port 8770`). If it’s our own instance, the launcher just reopens it. |
| **"Python was not found"** / import errors | Install Python 3.12 (Add to PATH). The launcher creates the venv and installs dependencies on first run (needs internet). |
| **"Node.js/npm was not found"** | Install Node 22+ (only needed to build the interface the first time). |
| **"source CSVs are missing"** | Put the six CSVs for each cohort under `Dataset/<cohort>/` and re‑run. |
| **Stale outputs** (changed a source or the pipeline) | The launcher detects it and rebuilds automatically; or run `.\run.ps1 -Rebuild`. Serving a stale build is refused. |

---

## Developer notes (optional manual commands)

Everything the launcher does can be run by hand from `six_source/` using the venv Python:

```powershell
python -m venv .venv; .\.venv\Scripts\python -m pip install -r six_source/requirements.txt
cd six_source
..\.venv\Scripts\python build.py            # 160,701 works, 21 reconciliation checks
..\.venv\Scripts\python patterns.py         # DATA_PATTERNS.md
..\.venv\Scripts\python validate.py         # ab_metrics.json + AB_Report.md
..\.venv\Scripts\python workbook.py          # MPLADS_Review.xlsx
..\.venv\Scripts\python tests.py             # invariant + end-to-end tests (add --rebuild for hash equality)
..\.venv\Scripts\python reproduce.py         # independent rebuild + reproducibility.json
..\.venv\Scripts\python prepare_release.py   # build+validate+activate a versioned release
..\.venv\Scripts\python serve.py --port 8766 # serves mplads-prototype/dist at /
```

Front‑end: `cd mplads-prototype && npm ci && npm run build` (dev: `npm run dev`, proxying `/api` to `:8766`; the archived app is `npm run dev:legacy`). Repository layout and design law: see [`CLAUDE.md`](CLAUDE.md); full plan: [`FINAL_PROJECT_PLAN.md`](FINAL_PROJECT_PLAN.md).

---

## Capabilities

**Implemented (local, working):** multi‑cohort build (160,701 works) with hash‑locked contracts and 21 reconciliation checks; explainable rule engine (10 screens, 5 bands) with per‑point reason codes; cost‑outlier, duplicate/near‑duplicate, vendor‑concentration screens; Isolation Forest and DBSCAN unsupervised outliers (separate from the queue); four persona dashboards + India risk map; local deterministic NL→SQL; offline A/B validation on the real pipeline; Excel/CSV/report exports; local review workflow; project status & tools with allow‑listed background jobs; versioned releases; reproducibility + tests.

**Experimental:** the natural‑language query engine (deterministic, allow‑listed SQL — intentionally not an LLM); DBSCAN feature‑space clustering; the A/B enhancement (cost + duplicate + year‑end screens).

**Planned (not built):** supervised risk scoring trained on investigator feedback; computer‑vision ghost‑asset checks; GNN vendor‑collusion detection; live MIS/eSAKSHI integration; and an **authorized officer pilot** with independently adjudicated cases (the review loop already captures the labels such a pilot needs). No production‑readiness or real‑world fraud‑accuracy claim is made.

## Security & privacy

Loopback‑only (`127.0.0.1`), exact‑Host check, read‑only SQLite, strict CSP, same‑origin review/job writes (the dev proxy preserves same‑origin without any CORS relaxation), no query strings in logs, source bytes verified every build, allow‑listed background jobs only. No external LLM or cloud call. Nothing is pushed or uploaded.

## License

MIT for source code (`LICENSE`). Inclusion of supplied MPLADS records establishes no separate data‑redistribution license or government endorsement.
