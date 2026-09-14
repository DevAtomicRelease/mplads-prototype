# Results workbook review

All five sheets were rendered and visually inspected on 10 September 2026: Summary, Controlled budgets, Case families, Real queues, Methods and sources. Arial was present in Windows Fonts and rendered successfully. The workbook uses plain grey headers, readable tables, typed counts/rates and no decorative charts. Titles, headers, source links and important numeric values were visible without clipping in the reviewed ranges.

The calculation checks verified live recovery after changing a selected-positive count, restored original recovery, the B-A recovery difference, family selected totals and the real queue Jaccard overlap. The formula-error scan found zero matches. Every sheet's rendered range and the five calculation checks are recorded in `workbook/previews/verification.json`; those support images are not additional deliverables.

The workbook is an aggregate review aid, not an interactive scoring engine. Counts are frozen experiment results; its simple displayed rate formulas update from those counts. It does not imply that changing a workbook input reruns the 1,000-draw bootstrap or the detection benchmark. Full cases, oracle, score components, selections and reproducibility evidence remain in the local evaluation package.

The Methods and sources sheet was subsequently extended by one scope-limit row and re-rendered. Its final A1:B20 preview has now been inspected and is readable. It explicitly identifies the absence of dedicated exact-duplicate-positive and pending-recommendation benchmark families. The other four reviewed sheets were unchanged, and all five calculation checks and the error scan passed again.

Final workbook: `outputs/ps26102-ab-20260910/MPLADS_AB_Results.xlsx`, 12,312 bytes. SHA-256: `8fee7d3544357b320c373731b5caa820580edd16b4f9c6fe1ebc0fff18f0379c`.
