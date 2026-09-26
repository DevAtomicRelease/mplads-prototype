# CLAUDE.md — repository guide

MPLADS-GUARD: an AI/ML anomaly, fraud-signal and inefficiency detection platform for
the MPLAD Scheme (SIH 2026 PS 26102). This file orients an agent or contributor; the
current implementation is in [`ARCHITECTURE.md`](ARCHITECTURE.md). Earlier plans are historical.

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
- `mplads-prototype/` — React 19 + Vite UI (`app/six-local.tsx`, `app/project-tools.tsx`, `vite.config.ts`).
- `evaluation_18/` — the older frozen A/B protocol (reference; superseded by `validate.py`).
- `archive/` — the superseded three-source iteration (do not extend).

## Build & run
```powershell
.\run.ps1                     # first run creates the venv, builds data + UI, then serves
```
Safe maintenance commands (from the repository root):
```powershell
.\.venv\Scripts\python.exe -B six_source/prepare_release.py
.\.venv\Scripts\python.exe -B six_source/maintenance.py tests
.\.venv\Scripts\python.exe -B six_source/maintenance.py reproduce
```
Front-end: `cd mplads-prototype && npm run build` (or `npm run dev` for hot reload,
proxying `/api` to `:8766`). Python 3.12.

## Tests
The maintenance tests action runs 39 invariant/API/release/mechanism checks against
the active release with isolated review storage. Prepare a new release after analytical
code changes. Never overwrite files in an active immutable release.

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
