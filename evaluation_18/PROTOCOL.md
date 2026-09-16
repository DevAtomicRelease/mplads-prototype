# Frozen offline A/B protocol — PS 26102

Version: all-cohort-ab-v1. Written before generating/scoring this experiment. No live users or official decisions are randomized. This is an offline paired screening-method comparison, not a field trial or fraud-accuracy claim.

## Inputs and arms

Use the verified `data_preparation/local/release_2026-09-10_v2` release, with its 18 locked original CSV hashes and 160,701 namespaced work keys. Never change that release or raw files. The older three-source A/B experiment is not reused as evidence.

A is a strong transparent baseline: sum of eight existing operational/payment screens (pending recommendation >45 days, sanction delay >45 days, open >one calendar year, no observed success after three months, open >reported term end+18 months, successful payments >sanction+INR1, completion amount >sanction+INR1, repeated report content) plus guarded exact-description/equal-sanction duplication.

B uses the same eight screens, replaces guarded exact duplication with guarded near duplication, and adds a historical peer-cost screen. No duplicate double vote. B must be at least A before ranking, but can displace A cases at fixed review capacity. Scores are unweighted counts, not fraud probabilities. Correlated operational flags can accumulate; report family displacement rather than hiding it.

Near-duplicate guard: weighted-token similarity >=0.96, equal known sanctioned amount, at least four non-stopword tokens, no conflicting numeric-token sets or continuation/phase/repair cue. Both real-data arms use the same stored bounded candidate pairs. Thus no claim of exhaustive duplicate recall is possible.

Cost: prior-financial-year state/activity peers with at least 20 records, activity fallback, log(1+INR) median/MAD, scale=max(1.4826*MAD,0.1), flag when robust z>3.5 and amount/median>=2. No tuning to experiment labels. Concentration and Isolation Forest are not added to B in this experiment.

## Two distinct evidence layers

1. **Real-data retrospective queue comparison:** score all works using current snapshot evidence. Report count, overlap/Jaccard, new/displaced cases, cohort mix, covered screens, ties, zero-score fillers and a locally saved review list. Do not estimate precision, false-positive rate, fraud prevalence, forecast accuracy or money saved. This is not a held-out predictive test.
2. **Controlled mechanism benchmark:** generate wholly synthetic coherent cases with synthetic IDs; never label unchanged real rows as clean. Use real historical peer distributions only as contextual anchors. Freeze reference amounts/text frequencies to sanctions through 31 March 2025. All synthetic sanctions occur after that cutoff. Use 100 separate development contexts and 400 test contexts, each with the same 18 predeclared case families. Development contexts are retained for independent debugging, not optimized for superiority. Test labels/oracle facts stay outside detector inputs. No weights/thresholds are fit on either synthetic partition.

The test has nine positive families: late sanction, stalled open work, missing successful payment, payment above sanction, completion above sanction, retired-term backlog, repeated payment, inflated cost (1.5x/2.5x/8x contextual cost), and near-duplicate description (word order, harmless extra word or one typo). Labels mean constructed review-worthy mechanisms, not real fraud.

Nine hard-negative families: routine work; pending request not settled expenditure; approved extension unavailable to detector; legitimate larger scope unavailable to detector; distinct phase; distinct numbered location; repeated export artifact unavailable to detector; INR0.10/INR1 rounding difference; legitimate distinct assets with identical visible description/price. Exonerating extension, scope, bank/invoice and asset facts stay in the oracle only. Some false alarms are intentionally irreducible with supplied fields. Report observable and information-limited controls separately.

Synthetic duplicate tests provide one reference pair and test the pair-scoring mechanism, not retrieval coverage across all works. They are not an end-to-end estimate of the real bounded text search. All mutations alter primitive dates, descriptions and monetary/payment records; never directly set a target screen or score.

Pre-run independent-review clarifications: the supplied synthetic duplicate partner is an abstract pair example, assumed to share IDA/activity, not a retrieved historical asset. Only cost and token-frequency membership is historical; no date or temporal retrieval claim is made for that abstract partner. Same-asset truth remains information-limited even where text similarity is visible. Synthetic payment fingerprints use four varying fields, with all omitted source-report fields held identical within a case. Routine retired-cohort examples use a recently ended term; retired-backlog examples are artificial ended-term scenarios, not source-cohort prevalence estimates. The fixed pre-April-2025 synthetic cost reference is intentionally different from each real row's rolling prior-FY membership. Pending-recommendation and missing-date boundaries are covered by unit fixtures, not by the 18-family benchmark. These clarifications were made before any scored run; no thresholds, weights or severities changed.

## Locked metrics and uncertainty

- Primary: recovery difference B-A at **10% equal review budget**, k=ceil(0.10*N).
- Secondary: 5% and 20% budgets; controlled yield per review, hard-negative selection/FPR and per-family recovery. Precision-like terminology applies only to known controlled labels and 50% constructed positive prevalence.
- Identical label-independent SHA-256 tie-breaks on case/work IDs for both arms. Report 20 fixed tie-seed results, boundary-tie sizes and zero-score fillers.
- Main seed 26102; test/development and tie streams derived explicitly from it. No seed cherry-picking.
- Paired percentile bootstrap: 1,000 resamples of whole test contexts (all 18 siblings together), recomputing both top-k lists for each resample. Report a 95% interval for B-A controlled recovery. This captures variation among generated contexts, not national real-world effectiveness.
- Record threshold workload (score>0) in addition to mandatory top-k review, since zero-score fillers are not alerts.
- Save every case, source/reference membership, score component, label, selected set and split. Rebuild in a separate directory and compare deterministic CSV/JSON hashes. Never rewrite results to imply superiority.

## Acceptance and next step

Data invariants and reproducibility must pass. A positive controlled lift alone does not approve deployment. Record every family loss and information-limited false alarm. The results determine an architecture with a preserved operational queue, a separately visible enhanced/shadow queue, source evidence and human adjudication. Plan the architecture and workflow only after evaluating these results. Live randomized reviewer validation requires reviewers, permissions, suitable labels, a predeclared time window and a power calculation based on observed pilot rates.

Research: [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html), [SciPy bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html), [MoSPI monitoring definitions](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2153066&lang=2&reg=48). The bootstrap is implemented with NumPy, not assumed to use an installed SciPy package.
