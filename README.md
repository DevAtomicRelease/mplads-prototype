# MPLADS Anomaly, Fraud & Inefficiency Detection — SIH 2026 PS 26102

An AI/ML platform that ingests MPLADS financial and project-execution data and surfaces **anomalies, fraud signals, and inefficiencies** as explainable, risk-ranked, human-reviewable cases — for Members of Parliament, State Nodal Authorities, District Authorities, and the Ministry (MoSPI).

> **Design law:** no anomaly score is fraud evidence or a legal finding. Every alert is a *request for evidence and human review*. Checks with no supporting data (asset photos, SC/ST tags, trust registration, GPS) are shown as **visibly unavailable**, never silently passed. No data leaves the device by default.

Full engineering plan: **[`FINAL_PROJECT_PLAN.md`](FINAL_PROJECT_PLAN.md)**. Domain background: [`PS26102_MPLADS_Context.md`](PS26102_MPLADS_Context.md).

---

## Repository layout (canonical)

| Path | Role |
|---|---|
| `Dataset/` | Immutable source CSVs, per cohort: `Lok Sabha/`, `Rajya_Sabha_sitting/`, `Rajya_Sabha_retired/`. Six files each (allocation, calamity consent, recommended, sanctioned, completed, expenditure). **Never edited.** All three build together into 160,701 works. |
| `six_source/` | **Canonical engine.** `build.py` (data + feature + detection pipeline), `serve.py` (loopback investigation API), `nlq.py` (local deterministic natural-language query engine), `patterns.py` (relations/pattern report), `isolation.py` (vendored NumPy Isolation Forest), `common.py` (versioned contracts & hashes). |
| `evaluation_18/` | Frozen offline A/B protocol + synthetic-injection benchmark (how the system is validated without fraud labels). |
| `mplads-prototype/` | React 19 + Vite + TypeScript front-end (investigation workspace; `app/six-local.tsx`). |
| `FINAL_PROJECT_PLAN.md` | Architecture, workflow, AI/ML, tech stack, data pipeline, execution order. |
| `archive/` | Superseded three-source iteration, kept for provenance only. See `archive/README.md`. |

---

## Quick start (Windows, PowerShell)

Python 3.12 recommended.

```powershell
# 1. Environment
python -m venv .venv
.\.venv\Scripts\python -m pip install numpy pandas openpyxl

# 2. Build the connected, audited dataset
cd six_source
..\.venv\Scripts\python build.py --output-dir local                    # all three cohorts (160,701 works)
# ..\.venv\Scripts\python build.py --cohorts lok_sabha --output-dir local   # a single cohort

# 3. Relations & patterns report (optional, after build)
..\.venv\Scripts\python patterns.py

# 4. Serve the local investigation API (loopback only)
..\.venv\Scripts\python serve.py --port 8766
```

`build.py` refuses to run unless every source file's row count **and** SHA-256 match the frozen contract in `common.py`, and it fails closed unless all 21 reconciliation checks pass. Outputs (CSV + indexed `mplads.sqlite3` + `audit.json`) land in `six_source/local/` (git-ignored; local by design).

### Front-end

The six-source UI has its own Vite config (`vite.six.config.ts`): entry `six.html` → `app/six-local.tsx`, output `dist/six/`, dev proxy `/api` → `127.0.0.1:8766` (matching `serve.py`).

```powershell
cd mplads-prototype
npm ci                # first time only (node_modules already present here)

# Development: hot-reload UI + live backend
npm run dev:six       # Vite dev server at http://127.0.0.1:3001, proxies /api to :8766
#   (run `python ../six_source/serve.py` in another shell)

# Production static build the backend serves itself
npm run build:six     # emits dist/six/ ; then `python ../six_source/serve.py` serves it at /
```

`serve.py` serves `dist/six/` at the web root (`/` → `six.html`) and handles `/api/*` from the read-only SQLite. Verified end-to-end: build → serve → `/api/health`, `/api/works`, static assets.

> The legacy three-source UI (`index.html` → `app/local.tsx`, `dist/local`) and its `serve_local.py` are retained under the old entry but are superseded by the six-source path above.

---

## Data pipeline (what `build.py` does)

1. **Contracts & quarantine** — hash-lock every source; quarantine invalid rows (one truncated expenditure row) without touching source files.
2. **One-work master** — union recommendation ∪ sanction → **107,937 works**, one row each; sanction export governs sanctioned fields. Money kept in **integer paise**.
3. **Lifecycle + cost features** — aging, chronology flags, and cost benchmarks computed from **prior fiscal years only** (leakage guard).
4. **Bounded duplicate candidates** — normalized-text, IDA·activity-blocked, weighted-token similarity with number/generic/phase guards.
5. **Explained rules + separate model** — deterministic rule engine → `priority_score` (capped 100) + per-point `Rule_Contributions`; a **separate** Isolation Forest `isolation_percentile`.
6. **Entity rollups** — MP, IDA, vendor, vendor-connection edges, IDA·FY concentration (HHI), monthly payments.
7. **Outputs** — CSV + indexed SQLite + `audit.json` + `review_workbook.json`.
8. **Reconciliation gate** — 21 checks (membership counts, paise-exact money sums, score↔contribution equality, no future events, source bytes unchanged).

Reproducible: fixed `SEED=26102`; pipeline/common SHA recorded in `audit.json`; independent rebuild comparable by output hash.

### Detection layers → problem-statement asks

- **Financial** — cost outliers (prior-FY robust log-MAD z), payment/completion-vs-sanction deltas, repeated-payment-report sensitivity, vendor concentration (HHI).
- **Execution** — duplicate/near-duplicate works, stalled-open aging, sanction delay, completion-without-payment.
- **Compliance** — deterministic rules: sanction delay >45d, open >1yr, no payment >3mo. (SC/ST %, ₹75L trust ceiling, jurisdiction: coded but **inactive** until the required tags exist.)
- **Inefficiency** — utilization ratios and category mix at MP/IDA grain.
- **Unsupervised** — Isolation Forest atypicality, deliberately separate from the rule queue.

Supervised fraud classification is **Phase-2**, unlocked once investigators label reviewed cases through the feedback loop.

---

## What the data shows

Generated by `six_source/patterns.py` (full report in `six_source/local/DATA_PATTERNS.md`). All-cohort build = **160,701 works** across Lok Sabha + Rajya Sabha (sitting/retired); the Rajya Sabha portal reuses `WORK_RECOMMENDATION_DTL_ID` across MPs, so keys are namespaced `cohort:mpkey:id`. Settled-vs-sanction differs sharply by cohort: **LS 41.6%, RS-sitting 70.9%, RS-retired 78.4%**.

Lok Sabha cohort snapshot:

- **Funnel:** 107,562 recommended → 79,881 sanctioned (74.3%) → 34,940 completed (43.7% of sanctioned). **44,941 works open.**
- **Money:** Rs 5,767 cr recommended, Rs 4,208 cr sanctioned, **Rs 1,751 cr settled (41.6% of sanction)**; allocation snapshot Rs 8,334 cr.
- **Queue:** 80.2% of works carry ≥1 screen; bands High 4,642 / Medium 28,503 / Low 53,393 / Routine 21,399.
- **Dominant signals:** sanction-delay >45d proxy 52.2%, no-payment-after-3mo 29.8%, pending-recommendation >45d 16.3%, open >1yr 10.0%.
- **Integrity result:** `paid_over_sanction` and `completion_over_sanction` are **0** — a legitimate clean result on the supplied fields, not a masked failure.
- **Cost:** 63,629 works get a prior-FY peer benchmark; 4,509 high-cost-peer flags; extreme ratios up to ~286×.
- **Duplicates:** 23,798 candidate pairs, 8,881 high-similarity-review, touching 11,610 works.
- **Vendors:** 20,763 distinct IDs; 1,715 same-name-different-ID collisions (kept distinct, never merged); 474 IDA·FY groups with HHI>0.5, 233 single-vendor.
- **Model vs rules:** Isolation-Forest top 1% overlaps rule High-band by only ~2% — the two layers are complementary by design.

Numbers are descriptive of the supplied 18th Lok Sabha exports, not verified national totals.

---

## Ask the data (local NL→SQL)

`six_source/nlq.py` answers plain-English questions (*"Which districts in Bihar have the most delays?"*, *"States with the lowest settled-to-sanction ratio"*) **entirely locally** — a deterministic intent parser maps the question to an allow-listed, parameterised aggregate over `Work_Features`, and returns an interpretation, a source-tied summary, a formatted table, and the **exact generated SQL**. No external LLM, no data egress, no hallucination — every number is reproducible from the shown query. Served at `/api/ask`; the "Ask the data" tab exposes it with example prompts.

## Validation (`evaluation_18/`)

Two evidence layers, no fraud-accuracy claim:
1. **Real-data retrospective queue comparison** — baseline vs enhanced at equal review budgets; report count, Jaccard overlap, displaced cases.
2. **Controlled mechanism benchmark** — wholly synthetic coherent cases (9 positive + 9 hard-negative families), reference frozen to sanctions ≤ 31 Mar 2025; recovery difference at 10% budget with a paired bootstrap 95% interval.

See `evaluation_18/PROTOCOL.md` and `evaluation_18/README.md`.

---

## Security & privacy

Loopback-only (`127.0.0.1`), exact-Host check, read-only SQLite URI, strict CSP, same-origin review writes, no query strings in logs, source bytes verified unchanged every build. No external LLM or cloud call by default. Generated outputs and review notes stay local.

## License

MIT for source code (`LICENSE`). Inclusion of supplied MPLADS records establishes no separate data-redistribution license or government endorsement.
