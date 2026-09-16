# MPLADS Anomaly, Fraud & Inefficiency Detection — SIH 2026 PS 26102

An AI/ML platform that ingests MPLADS financial and project-execution data and surfaces **anomalies, fraud signals, and inefficiencies** as explainable, risk-ranked, human-reviewable cases — for Members of Parliament, State Nodal Authorities, District Authorities, and the Ministry (MoSPI).

> **Design law:** no anomaly score is fraud evidence or a legal finding. Every alert is a *request for evidence and human review*. Checks with no supporting data (asset photos, SC/ST tags, trust registration, GPS) are shown as **visibly unavailable**, never silently passed. No data leaves the device by default.

Full engineering plan: **[`FINAL_PROJECT_PLAN.md`](FINAL_PROJECT_PLAN.md)**. Domain background: [`PS26102_MPLADS_Context.md`](PS26102_MPLADS_Context.md).

---

## Repository layout (canonical)

| Path | Role |
|---|---|
| `Dataset/` | Immutable source CSVs, per cohort: `Lok Sabha/`, `Rajya_Sabha_sitting/`, `Rajya_Sabha_retired/`. Six files each (allocation, calamity consent, recommended, sanctioned, completed, expenditure). **Never edited.** All three build together into 160,701 works. |
| `run.ps1` | One-command launcher: venv → build → front-end → serve. See **Run & test** below. |
| `six_source/` | **Canonical engine.** `build.py` (data + feature + detection pipeline), `serve.py` (loopback investigation API), `nlq.py` (local deterministic natural-language query engine), `validate.py` (offline A/B screening comparison), `patterns.py` (relations/pattern report), `isolation.py` (vendored NumPy Isolation Forest), `tests.py` (invariant tests), `common.py` (versioned contracts & hashes). |
| `mplads-prototype/` | React 19 + Vite + TypeScript front-end (investigation workspace; `app/six-local.tsx`). |
| `evaluation_18/` | The earlier frozen A/B protocol (reference; superseded by `six_source/validate.py`). |
| `FINAL_PROJECT_PLAN.md`, `CLAUDE.md` | Full plan; contributor/agent guide. |
| `archive/` | Superseded three-source iteration, kept for provenance only. See `archive/README.md`. |

---

## Run & test the full project

Python 3.12; Node 22+ only for building the UI. Everything runs locally on `127.0.0.1`.

### One command (Windows, PowerShell)

```powershell
.\run.ps1
```

First run creates the virtual environment, builds the dataset (**build → patterns → A/B validation**) and the front-end if they are missing, then serves the app at **http://127.0.0.1:8766/**. `-Rebuild` forces a fresh dataset build; `-Port <n>` changes the port. (Desktop app: the `mplads-guard` preview in `.claude/launch.json` runs this.)

### Step by step

```powershell
# 1. Python environment
python -m venv .venv
.\.venv\Scripts\python -m pip install -r six_source/requirements.txt   # numpy, pandas, scikit-learn, openpyxl

# 2. Build the connected, audited dataset — all cohorts -> 160,701 works, 21/21 checks
cd six_source
..\.venv\Scripts\python build.py
# ..\.venv\Scripts\python build.py --cohorts lok_sabha          # a single cohort

# 3. Reports (after build)
..\.venv\Scripts\python patterns.py     # -> local/DATA_PATTERNS.md   (relations & patterns)
..\.venv\Scripts\python validate.py     # -> local/ab_metrics.json + AB_Report.md (offline A/B)

# 4. Tests — 14 fast invariant checks
..\.venv\Scripts\python tests.py
# ..\.venv\Scripts\python tests.py --rebuild    # + reproducibility (fresh rebuild -> identical hash)

# 5. Front-end (needs Node; once)
cd ..\mplads-prototype
npm ci                 # install dependencies (fresh clone / first run)
npm run build:six      # emits dist/six/

# 6. Serve the local app + API (loopback only)
cd ..\six_source
..\.venv\Scripts\python serve.py --port 8766
```

Open **http://127.0.0.1:8766/**. `build.py` fails closed unless every source file's row count **and** SHA-256 match the frozen contract in `common.py` and all 21 reconciliation checks pass. Outputs (CSV + indexed `mplads.sqlite3` + `audit.json`) land in `six_source/local/` (git-ignored; local by design).

### Front-end development

```powershell
cd mplads-prototype
npm run dev:six        # Vite hot-reload at http://127.0.0.1:3001, proxies /api to :8766
```

Run `python ../six_source/serve.py` in another shell. The six-source UI has its own config `vite.six.config.ts` (entry `six.html` → `app/six-local.tsx`, output `dist/six/`); `serve.py` serves `dist/six/` at the web root and handles `/api/*` from the read-only SQLite. The legacy three-source UI (`index.html` → `dist/local`) is retained but superseded.

---

## Data pipeline (what `build.py` does)

1. **Contracts & quarantine** — hash-lock every source (per cohort); quarantine invalid rows (one truncated expenditure row) without touching source files.
2. **One-work master** — union recommendation ∪ sanction across all cohorts → **160,701 works**, one row each; sanction export governs sanctioned fields. Keys are namespaced `cohort:mpkey:id` (the Rajya Sabha portal reuses work ids across MPs). Money kept in **integer paise**.
3. **Lifecycle + cost features** — aging, chronology flags, year-end (March) disbursement share, and cost benchmarks computed from **prior fiscal years only** (leakage guard).
4. **Bounded duplicate candidates** — normalized-text, IDA·activity-blocked, weighted-token similarity with number/generic/phase guards.
5. **Explained rules + separate unsupervised models** — a 10-rule deterministic engine → `priority_score` (capped 100) + per-point `Rule_Contributions` and 5 bands (Routine/Low/Medium/High/Critical); plus two **separate** descriptive views kept out of the queue — an Isolation Forest `isolation_percentile` and a DBSCAN `dbscan_outlier_flag`.
6. **Entity rollups** — MP, IDA, vendor, vendor-connection edges, IDA·FY concentration (HHI), monthly payments.
7. **Outputs** — CSV + indexed SQLite + `audit.json` + `review_workbook.json`.
8. **Reconciliation gate** — 21 checks (membership counts, paise-exact money sums recomputed from source, score↔contribution equality, no future events, source bytes unchanged); build fails closed on any failure.

Reproducible: fixed `SEED=26102`; pipeline/common SHA recorded in `audit.json`; independent rebuild comparable by output hash.

**Tests:** `python six_source/tests.py` runs 14 fast invariant checks (build reconciliation, namespaced-key uniqueness, score↔contribution equality, band thresholds, unsupervised-signal consistency, NL-query injection-safety/determinism, A/B properties). `python six_source/tests.py --rebuild` adds an end-to-end reproducibility check (fresh rebuild → identical `Work_Features.csv` hash).

### Detection layers → problem-statement asks

- **Financial** — cost outliers (prior-FY robust log-MAD z), payment/completion-vs-sanction deltas, repeated-payment-report sensitivity, vendor concentration (HHI).
- **Execution** — duplicate/near-duplicate works, stalled-open aging, sanction delay, completion-without-payment.
- **Compliance & operations** — deterministic rules: sanction delay >45d, open >1yr, no payment >3mo, year-end (March) disbursement concentration. (SC/ST %, ₹75L trust ceiling, jurisdiction, payment-vs-physical-progress: **unavailable** — the exports carry no beneficiary tags, trust register, coordinates or physical-progress %, so these are shown unavailable, not passed.)
- **Inefficiency** — utilization ratios and category mix at MP/IDA grain.
- **Unsupervised** — Isolation Forest atypicality and DBSCAN feature-space outliers, both deliberately separate from the rule queue and complementary to each other.

Supervised fraud classification is **Phase-2**, unlocked once investigators label reviewed cases through the feedback loop.

---

## What the data shows

Generated by `six_source/patterns.py` (full report in `six_source/local/DATA_PATTERNS.md`). All-cohort build = **160,701 works** across Lok Sabha + Rajya Sabha (sitting/retired). Settled-vs-sanction differs sharply by cohort: **LS 41.6%, RS-sitting 70.9%, RS-retired 78.4%**.

- **Funnel:** 159,794 recommended → 124,155 sanctioned → 61,268 completed.
- **Queue:** 129,248 works (80.4%) carry ≥1 screen; bands Routine 31,453 / Low 84,348 / Medium 38,277 / High 6,623 / Critical 0.
- **Dominant signals:** sanction-delay >45d proxy 86,264 (53.7%), no-payment-after-3mo 37,067, pending-recommendation >45d 24,936, open >1yr 18,947, year-end (March) rush 5,899.
- **Anomaly signals:** high-cost-peer 4,792, near-duplicate-review 6,521 (35,452 candidate pairs), DBSCAN pattern outliers 5,748.
- **Integrity result:** `paid_over_sanction` = 1 and `completion_over_sanction` = 0 — a legitimate near-clean result on the supplied fields, not a masked failure.
- **Critical band = 0:** the top observed score is 64; the 81–100 tier is empty and would populate for a genuinely extreme work.

Numbers are descriptive of the supplied exports, not verified national totals.

---

## Ask the data (local NL→SQL)

`six_source/nlq.py` answers plain-English questions (*"Which districts in Bihar have the most delays?"*, *"States with the lowest settled-to-sanction ratio"*) **entirely locally** — a deterministic intent parser maps the question to an allow-listed, parameterised aggregate over `Work_Features`, and returns an interpretation, a source-tied summary, a formatted table, and the **exact generated SQL**. No external LLM, no data egress, no hallucination — every number is reproducible from the shown query. Served at `/api/ask`; the "Ask the data" tab exposes it with example prompts.

## Validation (`six_source/validate.py`, "A/B validation" tab)

`validate.py` runs an offline A/B screening comparison and writes `local/ab_metrics.json` (served at `/api/validation`) plus `AB_Report.md` and CSVs. Two evidence layers, no fraud-accuracy claim:
1. **Controlled mechanism benchmark on the real pipeline** — synthetic *source-shaped rows* (a prior-year peer background, labelled positive mechanisms, **legitimate-exception negatives** and difficult negatives) are run through the **actual build feature functions and rule engine**, then the **actual queue** is evaluated at equal review budgets: recovery, useful findings per review, and false-alert burden (genuinely flagged negatives, not zero-score fillers), with a paired bootstrap 95% interval. Baseline **A** = the operational/payment screens; enhanced **B** adds cost-outlier, near-duplicate and year-end screens.
2. **Real retrospective queue comparison** — A vs B ranking of the actual built works; report queue **overlap** (Jaccard) at equal budgets. No accuracy claim.

Representative result (seed 26102): **0 of 1,284** legitimate-exception/hard negatives are flagged (materiality + guards working), 100/120 positives flag (the near-duplicate misses are bounded-detector limits), and at a 10% budget **B recovers ~83% vs A ~60% (+23 pp, 95% CI ~16–31 pp) with zero false alerts** — B recovers the cost/duplicate positives A scores zero. Evaluation families, seed, cutoff and peer anchors are frozen before scoring; production thresholds are used unchanged (no tuning on the test set). The earlier `evaluation_18/PROTOCOL.md` informed this design.

---

## Security & privacy

Loopback-only (`127.0.0.1`), exact-Host check, read-only SQLite URI, strict CSP, same-origin review writes, no query strings in logs, source bytes verified unchanged every build. No external LLM or cloud call by default. Generated outputs and review notes stay local.

## License

MIT for source code (`LICENSE`). Inclusion of supplied MPLADS records establishes no separate data-redistribution license or government endorsement.
