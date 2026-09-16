# PS 26102: preparation of all supplied datasets

Scope: the 18 CSV files supplied in three parliamentary cohorts on 10 September 2026. This supersedes the earlier six-file input assumption, not the original files. No publication or change to the existing prototype is part of this preparation run.

- [x] Re-read the problem statement and verify official monitoring definitions.
- [x] Profile every source, including schemas, money, dates, missingness, term identity, duplicate records and overlap across cohorts.
- [x] Freeze the input manifest. Preserve every original record and its provenance. Quarantine malformed records with a reason rather than guessing values.
- [x] Build a work master, a term-aware MP dimension and separate payment and consent facts. Validate join cardinalities and financial totals before deriving features.
- [x] Engineer documented features for expenditure reconciliation, sanction and completion delays, term-end follow-up, comparable costs, repeated descriptions, payment patterns and vendor concentration. Keep data-quality observations separate from investigation signals.
- [x] Produce full local CSV and SQLite tables, a complete feature dictionary and a plain Excel review summary. The workbook is a review extract, not a replacement for the complete tables.
- [x] Test boundary conditions, independently reconcile the outputs, rebuild and compare deterministic artifact hashes, then verify the raw files are unchanged.
- [x] Document findings, unsupported checks, reproducible commands and the next requirements for model/prototype integration. Do not claim fraud accuracy or A/B success without labels and an actual evaluation.

Design constraints: no invented values, no unverified transaction deduplication, no geographic assertions from a generic Rajya Sabha constituency, and no mixing parliamentary terms using the misleading shared `Sitting MP` label. Treat rule thresholds as monitoring proxies when receipt dates, sanction-letter exceptions or actual demission dates are absent.

Completed release: `local/release_2026-09-10_v2/`. Verification: 17 unit tests, 116 pipeline checks, 185 independent/rebuild checks and 43 saved-workbook checks passed. All 19 prepared CSVs reproduced byte-for-byte. All six workbook sheets visually reviewed. The complete dataset contains 160,701 work entities with 119 fields and 113,691 payment records. See the local `DELIVERY.md` for handoff and outstanding project integration work.
