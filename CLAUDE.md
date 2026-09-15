# CLAUDE.md — repository guide

MPLADS-GUARD: an AI/ML anomaly, fraud-signal and inefficiency detection platform for
the MPLAD Scheme (SIH 2026 PS 26102). This file orients an agent or contributor; the
full plan is in [`FINAL_PROJECT_PLAN.md`](FINAL_PROJECT_PLAN.md).

## Design law (do not violate)
- **No score is a finding of fraud.** Every alert requests evidence and human review.
- Checks with no supporting data (physical progress %, SC/ST tags, trust register,
  GPS, asset photos) are shown as **visibly unavailable, never silently passed**.
- Source CSVs under `Dataset/` are **immutable**; the build fails closed on any hash
  drift. New outputs and review notes stay local (gitignored).
- Keep the deterministic rule engine and the unsupervised models (Isolation Forest,
  DBSCAN) **separate** — the queue score is rules only; the models are descriptive.
- No external LLM or network call in the detection or query path. "Ask the data" is a
  deterministic local SQL parser, not an LLM.

## Canonical layout
- `six_source/` — the engine. `build.py` (pipeline), `serve.py` (loopback API + static
  app), `nlq.py` (NL→SQL), `validate.py` (offline A/B), `patterns.py` (report),
  `isolation.py` (vendored Isolation Forest), `common.py` (contracts/hashes), `tests.py`.
- `mplads-prototype/` — React 19 + Vite UI (`app/six-local.tsx`, built via `vite.six.config.ts`).
- `evaluation_18/` — the older frozen A/B protocol (reference; superseded by `validate.py`).
- `archive/` — the superseded three-source iteration (do not extend).

## Build & run
```powershell
.\run.ps1                     # first run creates the venv, builds data + UI, then serves
```
Manual equivalent:
```powershell
python -m venv .venv; .\.venv\Scripts\python -m pip install -r six_source/requirements.txt
cd six_source; ..\.venv\Scripts\python build.py            # 160,701 works, 21 checks
..\.venv\Scripts\python patterns.py; ..\.venv\Scripts\python validate.py
..\.venv\Scripts\python serve.py --port 8766               # serves mplads-prototype/dist/six
```
Front-end: `cd mplads-prototype && npm run build:six` (or `npm run dev:six` for hot reload,
proxying `/api` to `:8766`). Python 3.12.

## Tests
`python six_source/tests.py` — 14 fast invariant checks. `--rebuild` adds a reproducibility
(hash-equality) check. After any change to `build.py`/`common.py`, run the build and tests.

## Data facts that trip people up
- The four work files are not disjoint; the master is the **union** of recommendation ∪
  sanction, one row per work (160,701 across Lok Sabha + Rajya Sabha sitting/retired).
- The Rajya Sabha portal **reuses `WORK_RECOMMENDATION_DTL_ID` across MPs**, so keys are
  namespaced `cohort:mpkey:id` and MP keys are cohort-namespaced.
- Money is integer **paise** throughout; `paise()` snaps float-serialization noise only.
- `Payment Success` vs `Payment In-Progress` are never summed together.

## Conventions
- Commit only when asked; branch off the default branch first. No raw data, `six_source/local/`,
  `mplads-prototype/dist/six/`, or `.venv/` is ever committed (all gitignored).
- Match the terse, disclosure-heavy field/feature naming already in `build.py`.
