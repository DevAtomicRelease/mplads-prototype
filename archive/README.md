# Archive — superseded iterations

These directories and scripts are **retained for provenance and reproducibility only**. They are the earlier three-source pipeline and its runtime, superseded by the canonical `six_source/` engine. Nothing in the active project imports from here.

| Item | Was | Replaced by |
|---|---|---|
| `pipeline_research/` | Original three-source feature pipeline (`build_features.py`), its tests, artifacts, and Excel workbook | `six_source/build.py` (the `isolation_scores` model is now vendored in `six_source/isolation.py`) |
| `validation_research/` | First A/B validation of the three-source queue | `evaluation_18/` (frozen offline A/B protocol) |
| `data_preparation/` | Namespaced multi-cohort release experiment (reached 160,701 keys) | To be folded into `six_source` as the multi-cohort build (see `FINAL_PROJECT_PLAN.md` §11.3) |
| `prototype-local-data/` | Old loopback service runtime logs/reviews | `six_source/serve.py` writes its own local review DB |
| `outputs/` | One-off Excel/CSV exports from earlier runs | `six_source/local/` build outputs |
| `scripts/verify_team_bundle.py` | Old delivery-bundle verifier | build-time reconciliation checks in `six_source/build.py` |
| `START/STOP/REBUILD_PROJECT.*`, `PROJECT_RUNTIME.ps1` | Runtime for the old "MPLADS Insight" stack (`dist/local`) | Documented six_source flow in the root `README.md` |
| `DELIVERY_VERIFICATION.md`, `TEAM_DATA_MANIFEST.json` | Old delivery docs | `FINAL_PROJECT_PLAN.md` + this consolidation |

Do not extend anything here. To reproduce the old three-source results, run the scripts in place; they still reference each other by their original relative paths inside `archive/`.
