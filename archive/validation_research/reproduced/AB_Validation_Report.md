# MPLADS offline A/B ranking validation

This is a reproducible offline comparison of review ranking methods. It is not a randomized live user experiment and does not estimate real fraud accuracy.

## Data and temporal split

Source: Three raw MPLADS workbooks via core-2026-09-06-v1. Workbook SHA-256: `Works Sanctioned.xlsx: df7566583d45030fd70ee93f3c718cb93ac29add7fdc6323f3b3c4675212cd50 | Allocated Limit for Honble MPs.xlsx: 3a2b695b2a419c600c679e51a672e168904b8f0177e501e47a4caf50b5b4a83d | Amount consented for Calamity.xlsx: 2aab01d90d1d5c8b26b206f3a54d671a0ee9a2ab28aafdbca4f365ad91b5f733`. Extracted snapshot JSON SHA-256: `b874687cfc0211ab0f5323f0e26ab5ff38f82437fd24cada9ba3d9e5ae5c9bbe`.
The frozen cutoff is 2025-02-20: 7,013 earlier works form the reference; 2,987 later works form the test set. All records on a cutoff date remain together.
Peer medians and log-MAD scales are fitted only on earlier amounts. Test descriptions are matched only to earlier training works in the same IDA and work type. Original full-dataset cost, duplicate, entity aggregates, and priority scores are not used. No test outcome is used for fitting or tuning.

The date split validates retrospective screening on a frozen snapshot; it does not demonstrate forecasting from information available at the sanction date. Status/age are measured at the 2026-09-01 snapshot.

## Frozen methods

A = delay contribution + early-stage aging contribution. B = A + robust high-cost contribution + corroborated description similarity contribution. These research scores are distinct from the earlier workbook priority scores.
Delay: 30 × clip((calendar delay − 45)/320, 0, 1). Aging: 20 × clip((snapshot age − 180)/550, 0, 1), only for early-stage works. Cost: 25 × clip((log-cost robust z − 2.5)/3.5, 0, 1), only when amount exceeds 2× historical peer median. Duplicate: 25 × clip((token Jaccard − 0.80)/0.20, 0, 1), within the same IDA/type and amount within 5%, with at least five description tokens.
Peer fallback: state + type when at least 20 reference works exist, then type with at least 20, then global. Robust scale = max(1.4826 × log-amount MAD, 0.25). Weights and benchmark severity were fixed in the script before running the experiment; they were not searched or optimized on the held-out results.

## Real-data queue comparison

The counts below measure queue composition. A cost or duplicate flag is an unconfirmed signal, so these are coverage measures, not correctness measures.

| Review budget | Cases each | Queue overlap | A cost / duplicate cases | B cost / duplicate cases |
|---|---:|---:|---:|---:|
| 5% | 150 | 17.3% | 23 / 0 | 132 / 14 |
| 10% | 299 | 54.2% | 131 / 0 | 229 / 15 |
| 20% | 598 | 77.6% | 197 / 1 | 315 / 17 |
| 30% | 897 | 88.2% | 237 / 2 | 327 / 18 |

## Controlled held-out injection benchmark

The benchmark samples 1,200 held-out source rows aged at least 365 days (fixed seed). Four disjoint groups of 100 receive delay, early-stage aging, high cost, or historical duplicate evidence; 800 rows retain their source values. If fewer eligible rows exist, the script scales this fixed design proportionally. Unchanged cases may already contain legitimate anomalies.
Delay sets recommendation 365 days before the existing sanction date. Aging changes status to early stage while retaining actual sanction/snapshot dates. High cost sets amount to the larger of 8× historical median or exp(median log amount + 6 historical robust scales) − 1. Duplicate replaces description, IDA, type, state, and amount with an earlier training record. Injection changes are confined to an in-memory copy and an explicitly labeled validation output; no source data are augmented.
Some temporal injections can reinforce a signal already present. Therefore the benchmark measures recovery of cases selected for an injected scenario, not a causal estimate that every detected signal was newly created.

| Review budget | A recovery | B recovery | Difference B−A | Paired bootstrap 95% interval |
|---|---:|---:|---:|---:|
| 5% | 11.2% | 13.0% | +1.8 pp | [-0.5, +4.0] pp |
| 10% | 16.0% | 26.5% | +10.5 pp | [+7.5, +13.0] pp |
| 20% | 37.2% | 52.8% | +15.5 pp | [+12.0, +18.2] pp |
| 30% | 47.8% | 68.8% | +21.0 pp | [+16.8, +25.5] pp |

Intervals condition on this fixed reference model, designed severity, selected source pool, and artificial scenario mixture. They do not cover unknown fraud prevalence, label error, distribution drift, or re-training uncertainty.

| Scenario | Injected | Signal triggered | Already signaled before | Component increased | A recovery at 20% | B recovery at 20% |
|---|---:|---:|---:|---:|---:|---:|
| delay | 100 | 100.0% | 100 | 100 | 100.0% | 38.0% |
| aging | 100 | 100.0% | 25 | 75 | 27.0% | 5.0% |
| high_cost | 100 | 100.0% | 16 | 97 | 12.0% | 84.0% |
| duplicate | 100 | 100.0% | 2 | 99 | 10.0% | 84.0% |

The combined ranking improves total recovery for this designed mixture at 10–30% budgets. Its benefit at 5% is uncertain because the interval includes zero. At 20%, B prioritizes injected cost/duplicate evidence while detecting fewer of the injected delay/aging cases than A. This is a measurable allocation tradeoff, not general superiority. Keep distinct operational delay and aging queues or agree a review quota before considering the combined queue for deployment; validate any changed policy on a new untouched test set.

## Limits and next validation step

- The 10,000-row work extract covers 12.75% of its reported value and may be selected rather than representative. Training/test results apply to this extract.
- Sanction delay is recommendation-to-sanction calendar time; actual IDA receipt date and excluded periods are absent. Aging is a snapshot proxy. Cost comparisons lack dimensions and specifications. Similarity lacks verified coordinates and asset scope.
- Background records are not verified negatives. Neither false-positive rate, fraud precision/recall, nor saved reviewer time can be estimated here. The duplicate benchmark contains intentionally strong matches and can overstate generalization to paraphrases or genuine scope differences.
- The narrow A baseline is useful for isolating added signals, but is not claimed to be the strongest possible alternative. An unsupervised score has no supervised fraud calibration.
- A prospective pilot should randomize comparable cases/officers to A or B at the same review budget, use blinded independent adjudication, and measure substantiated issues per review, time to decision, agreement, and missed-case sampling. The current comparison does not replace this live experiment.

## Reproduction and files

Run `python run_ab_validation.py` with the bundled NumPy and pandas runtime. Optional `--input` and `--out` arguments override paths. Fixed seeds, hashes, train/test manifest, scores, synthetic row records, and machine-readable metrics accompany this report.
The script asserts record uniqueness, temporal separation, no train/test overlap, all historical references belonging to training, correct output counts, and source hash stability. Successful assertions are recorded under `checks` in metrics.json.
