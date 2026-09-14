# AI/ML approach for MPLADS PS 26102

Research date: 11 September 2026. Data assessed: the frozen 10 September 2026 all-cohort release. This is a researched design recommendation, not a newly trained model or a claim of measured superiority. No weights were downloaded, data uploaded, source records altered or previous A/B results retuned.

## 1. Recommendation

Use a **local hybrid investigation system with separate detection channels**:

1. **Operational checks:** versioned timeline and financial reconciliation rules, with explicit evidence gaps and exceptions.
2. **Cost and similar-work investigation:** historical peer statistics plus guarded lexical matching; test richer text retrieval separately.
3. **Experimental ML discovery:** a small Isolation Forest on eligible, comparable numeric features, initially visible only in a shadow/comparison queue.
4. **Connected-entity evidence:** descriptive vendor/IDA/work relationships, not a graph-based declaration of collusion.
5. **Human adjudication:** gather supporting documents and reliable outcomes before supervised learning or automatic escalation is considered.

The best first *additional tabular ML candidate to test* is Isolation Forest. The best first *text improvement to test* is character TF-IDF. A small local multilingual embedding model is a later challenger. Neither is a validated winner for these data. Deep networks, GNNs and an autonomous LLM are not prerequisites for a useful prototype.

This choice is based on the task's evidence and operating constraints. The primary ADBench study finds that algorithm performance depends on anomaly type; its benchmark does not establish a universal best detector or an MPLADS result. [ADBench, NeurIPS 2022](https://papers.neurips.cc/paper_files/paper/2022/file/cf93972b116ca5268827d575f2cc226b-Paper-Datasets_and_Benchmarks.pdf)

## 2. What the actual data permit

The problem statement covers fund use, approvals, expenditure, work execution and asset creation. The dataset supports some of those objectives directly and others only as evidence requests. It has 18 supplied exports: six dataset types for each of three parliamentary cohorts. Their inclusion does not establish national or longitudinal completeness.

| Observed fact | Model-design consequence |
|---|---|
| 160,701 namespaced works; 124,155 sanctioned, 61,268 reported complete, 62,887 sanctioned/open and 36,546 absent from the sanction export | Compare like lifecycle stages. Do not feed all stages into one undifferentiated anomaly model |
| 113,691 accepted payment-report rows; 71,974 works have observed successful-payment evidence | Coverage and payment status must be explicit. Absent export evidence is not proven non-payment |
| 109,472 works have at least 20 historical peers, approximately 88.17% of sanctioned works | Peer-relative methods need eligibility and fallback reporting, not an invented default score for unsupported rows |
| 1,023 MP-term records, 34,242 exact vendor IDs and 1,045 IDAs | Preserve the work, term, payment and vendor grains; graph relationships are possible without inventing ownership links |
| 278 reused numeric work IDs; 1,205 FLAG=2 recommendations separately namespaced | IDs are string join keys, not numeric model features. Never merge on name or numeric ID alone |
| 1,795 repeated payment-report rows across 528 works; no transaction/invoice IDs | Repetition is an evidence screen, not a bank-transaction duplicate label. Preserve original and sensitivity totals |
| 160,614 descriptions are ASCII-only; 87 contain non-ASCII characters; none contain Devanagari | Start by evaluating lexical spelling variation. This script probe is not language identification: ASCII can contain transliterated Indian languages |
| Only three works have a missing-description flag | Text matching has broad input availability, but description presence does not establish distinctive location/scope |
| No confirmed fraud/adjudication labels, quantities, verified coordinates/photos or reliable knowledge timestamps | Fraud classification, unit-cost overpricing, physical-asset verification and prospective accuracy cannot currently be validated |

Evidence: the frozen `DATA_REPORT.md`, `manifest.json` and a read-only SQLite profile performed for this research. Counts above were recomputed from `Work_Features`; schema checks confirmed the available payment/vendor/network fields. The snapshot remains dated 10 September: researching on 11 September does not silently advance its ages or scores.

### Correct the old context assumptions

The supplied context document was written partly around a synthetic-data hackathon. Do not follow its suggestions to invent missing real-data fields, apply universal SC/ST/geography/trust rules without inputs, assign an arbitrary 0–100 fraud score, or build a photo-based ghost-asset detector from attachment IDs. These capabilities remain disabled or future work.

MoSPI describes receipt-based sanction/rejection timing, generally one-year completion with exceptions, and demission-related follow-up. Therefore recommendation date and reported term end remain proxies, not conclusive non-compliance evidence. Implement applicability, rule effective dates and exception status before stronger compliance wording. [MoSPI eSAKSHI monitoring definitions](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2153066&lang=2&reg=48)

## 3. Why the previous A/B result changes the architecture

The frozen experiment compared transparent A against B's additional peer-cost and near-text signals. **It did not test Isolation Forest, embeddings, GNNs or an LLM.** At equal capacity of 720 synthetic reviews, A recovered 601 constructed positives and B 610. B gained 35 cost/text cases but displaced 26 shared-signal positives. B lost on four of 20 alternative tie seeds. The real 10% lists each contain 16,071 works; 1,682 enter B and the same number leave A, without truth labels for either set.

Consequently, adding another signal to a summed score is not automatically an improvement. Preserve A and its screen-specific views; label B and new methods as separate comparison channels. Any new capacity split, weights or ranking policy must receive its own evaluation. Do not call B's synthetic gain evidence that a new ML model works.

The existing test is a useful reproducible mechanism check, but its duplicate examples provide an already selected pair; they do not test retrieval across the dataset. There is no dedicated exact-duplicate-positive or pending-recommendation benchmark family. New experiments must address those gaps without overwriting the old protocol or claiming an untouched test set after tuning to it.

## 4. Algorithm decisions

| Method | Decision | Fit to this dataset and limitation |
|---|---|---|
| Deterministic reconciliation and timeline rules | Operational core | Exact paise and observable dates are explainable; source coverage and policy exceptions remain necessary |
| Prior-year log-cost median/MAD | Retain as cost evidence | Already reproducible and inspectable. Compares category amounts, not unit prices or justified scope |
| Isolation Forest | First numeric ML challenger | Useful for unusual feature combinations without fraud labels; uncommon legitimate works or reporting patterns can also appear anomalous |
| Character TF-IDF with guarded pair comparison | First text challenger | Low deployment complexity; targets lexical/spelling variation visible in these descriptions |
| Local multilingual-E5-small embeddings | Second text challenger | May recover paraphrase/transliteration/cross-language candidates; must beat lexical retrieval on relevant labelled pairs |
| Local Outlier Factor | Bounded numeric challenger | Local-density comparison may help within meaningful peer groups; sensitive to distance/scale/neighbour choices |
| Kernel One-Class SVM | Defer | No trusted normal-only population; sensitivity and scaling make it a weak first choice here |
| Autoencoder / deep tabular network | Defer | Extra model/tuning choices with no independent real outcome target; reconstruction error is not misuse |
| CatBoost, compared with logistic regression and LightGBM | Later supervised study | Mixed categorical/numeric data are a plausible fit, but adjudicated labels and leakage-safe splits are prerequisites |
| Kaplan–Meier / penalized Cox, then survival forest if useful | Separate delay study | Appropriate for time-to-recorded-completion with valid censoring, not fraud detection |
| Descriptive graph aggregates and bounded neighbourhoods | Evidence viewer now | Can expose connected works and concentration; cannot establish collusion or common ownership |
| GNN fraud classifier / autonomous LLM investigation agent | Defer | Neither labels/relationships for supervised fraud graphs nor authority for autonomous findings are available |

Scikit-learn distinguishes outlier detection on a contaminated sample from novelty detection using a normal reference. Its guide also documents One-Class SVM sensitivity/scaling and LOF's different training-versus-unseen-data APIs. These are method constraints, not accuracy rankings for MPLADS. [Outlier and novelty detection guidance](https://scikit-learn.org/stable/modules/outlier_detection.html)

## 5. Numeric ML design

### Feature eligibility comes before fitting

Use one namespaced work per row. Begin with sanctioned works, partitioned by open/completed status and relevant payment-evidence coverage. Recommendation-only cases remain in their own operational channel. State/activity/FY define peer context; cohort and source coverage are also evaluation strata. Do not use a separate tiny model per MP or vendor.

| Candidate feature family | Available fields / proposed transformation | Safeguard |
|---|---|---|
| Cost context | `cost_peer_log_z`, with `cost_peer_ratio` and `peer_count` shown as evidence | Do not automatically add absolute cost, ratio and z as three independent votes for the same phenomenon |
| Approval timing | `sanction_delay_days`, peer-relative duration where reference support permits | Recommendation-to-sanction is not receipt-to-decision |
| Open-work age | `sanction_age_days`, log transform or stage/activity-relative age | Only compare works at the same assessment date and compatible stage |
| Successful expenditure | `paid_to_sanction_ratio` with `has_successful_payment_evidence` | Require nonzero sanction and appropriate evidence; unknown is not zero |
| Pending requests | Proposed `pending_payment_paise / sanction_amount_paise` | Keep separate from spent money; missing/invalid denominators give unavailable |
| Payment recency | `days_since_last_success` | Use only in the successful-payment-evidence partition; do not impute an invented last payment |
| Payment/vendor activity | Log counts such as `successful_payment_count`, `vendor_count` | Work age and export coverage affect opportunity to accumulate counts |
| Completed-work amounts | `completion_sanction_delta_paise` and supporting sanctioned amount | Completed partition only; reconciliation screen remains independently visible |

Exclude raw work/MP/vendor IDs, names, serial numbers, attachment IDs, row order, the existing A/B scores, `screening_signal_count`, and rule flags as first-pass numeric inputs. IDs support joins and drill-down; rule flags are not training labels. Do not copy MP-term allocation or calamity consent onto each work and sum it as expenditure. Keep graph and text scores outside the initial numeric model to avoid a difficult-to-audit conglomerate.

Missingness is not a uniform preprocessing problem. Use explicit eligibility partitions for structurally unavailable values. For residual missing values in eligible features, fit an imputer only on the reference partition and record missingness as reliability metadata; test whether a proposed missingness predictor merely learns source incompleteness. Use separate quality alerts for acquisition failures. Unsupported peers should produce an eligibility reason, not a plausible zero-risk score.

### First Isolation Forest experiment

Proposed starting configuration: 200 trees, `max_samples='auto'`, all selected features, no bootstrap, fixed declared seed and `contamination='auto'`. This is a modest starting experiment, not a tuned optimum. Rank by `-score_samples` so higher values mean more unusual, retain the raw value, and do not interpret a percentile as a probability. Scikit-learn uses the contamination setting to establish a threshold; choosing 5% is not evidence that 5% of MPLADS works are fraudulent. [Isolation Forest API](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)

Fit peers, preprocessing and the model inside the declared reference partition. For an initial retrospective feasibility experiment, keep linked works in the same group, fit on a declared reference subset and score a disjoint assessment subset using only reference-fitted transforms. Such a split measures stability and enables later adjudication; it does not turn current snapshot fields into historical knowledge or supply ground truth. Apply the same eligibility population and review budgets to all compared methods, reporting excluded cases separately.

The prepared peer-z and ratio columns describe the existing release's reference policy. Recompute their reference statistics for each new experiment split; do not reuse a full-release transform while claiming that only the experiment's training partition fitted it. Preserve the prepared columns separately as evidence for the original method.

Inspect stability across predeclared seeds and reasonable tree/subsample settings on a development partition. Document every tried configuration. A score-only model cannot be selected by a fraud-accuracy statistic before real labels exist. Dense systemic irregularities can look normal; retain deterministic checks and relational evidence even if ML assigns low unusualness.

Show an evidence panel with measured features, peer reference/count, applicable rules and missing facts. Those are observed reasons to inspect, not mathematically proven feature attributions for Isolation Forest. If later adding SHAP or perturbation explanations, validate their model support and faithfulness separately and never present attribution as a causal explanation.

## 6. Duplicate-work detection: retrieval and verification are different tasks

### Retrieval

Preserve source text, and version normalization separately. Keep numbers, place fragments and phase/extension/repair terms available for structured checking.

- Keep the current weighted-token candidate set as the frozen reference.
- Test a sparse character TF-IDF representation, starting with `char_wb` 3–5 character n-grams and L2 normalization. Fit its vocabulary/IDF on the declared reference only. This is a proposed lexical challenger, not a proven accuracy increase. [TF-IDF documentation](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
- Use more than one retrieval pass: same IDA/activity; broader state/activity with distinctive place fragments; an audited sample outside those blocks. Record candidate caps and cap hits. Limit per-query candidates and stream comparisons rather than materializing all pairs.
- Keep exact equal-amount matching as strong corroborating evidence, but do not require amount equality for every *retrieval* pass: the same asset might appear with a changed estimate. Changed-amount matches remain a new experimental channel, not an alteration to frozen B.
- For ordinary investigator keyword search, SQLite FTS5/BM25 is sufficient to test before adding another search service. Its ranking is search relevance, not duplicate probability; lower SQLite BM25 values rank better. Place the derived index outside the immutable fact database. [SQLite FTS5](https://sqlite.org/fts5.html)

### Semantic challenger

Test `intfloat/multilingual-e5-small` only after the lexical/pair-label work. Its official card documents MIT licensing, 384-dimensional embeddings, a 512-token limit and the `query: ` prefix for symmetric similarity. Its multilingual coverage claim does not establish equal accuracy across Indian languages; actual script/language strata and truncation need measurement. Pin a reviewed revision, license and artifact hashes rather than following a moving `main`. [E5 model card](https://huggingface.co/intfloat/multilingual-e5-small/blob/main/README.md)

No model was downloaded in this research. The local vector matrix alone would use 160,701 × 384 × 4 = 246,836,736 bytes, about 235.4 MiB, at float32. Model weights, sparse features, index and runtime memory are extra. Exhaustive unordered comparison would require 12,912,325,350 pairs. These are arithmetic estimates, not measured throughput. Benchmark batches on the target device before choosing any approximate index or promising latency.

### Verification and evaluation

For each retrieved pair, expose text differences, amount/date differences, location/phase/number conflicts, peer context and raw-source references. Number conflicts can refer to phases, sites, years or estimates; do not silently equate all conflicts or remove every number. Conservative current guards remain until evaluated replacements exist.

Pair labels should distinguish same physical asset/scope, separate asset, legitimate phase/extension, duplicate report, and insufficient evidence. Include exact-positive matches, different-amount positives, transliterated text, common-template negatives and cases missed by the existing retrieval blocks. A model cannot infer physical identity reliably where the distinguishing evidence is absent.

Measure candidate recall on an independently assembled known-pair set separately from precision/yield of the final review list. Labels drawn only from a retriever's candidates cannot demonstrate that retriever's recall. Hold entire asset families/pair groups out together. Do not reuse the old supplied-pair synthetic test as an end-to-end retrieval benchmark.

## 7. Vendor networks: evidence before graph learning

Build typed links between work, exact vendor ID, IDA, implementing-agency name and MP term. Preserve the payment report's provenance and status on edges. Derived features can use successful-payment shares, existing IDA-year HHI/top-vendor share, unique counterparties and bounded shared-vendor neighbourhoods. Display original-report and fingerprint-sensitivity totals together; neither establishes invoice duplication.

Start with SQL aggregates and on-demand neighbourhoods; add a graph library only for an algorithm the UI needs. Avoid dense all-entity projections, ownership inference from spelling similarity, or centrality being relabelled as a collusion score. A contractor serving several authorities may be entirely legitimate.

CARE-GNN, for example, uses label-aware neighbour selection in its research setting. That does not match a dataset without fraud labels or ownership relations. This is a reason to defer that particular supervised approach, not a claim that all graph learning requires labels. [CARE-GNN primary paper](https://arxiv.org/abs/2008.08692)

For future graph experiments, build edges as of the prediction cutoff and keep evaluation labels out of message-passing inputs. A current full-snapshot graph is an investigation aid, not a time-valid predictive feature store.

## 8. Later learning: two distinct objectives

**Evidence-backed issue prioritization:** once investigators supply sufficient, diverse adjudicated outcomes, compare regularized logistic regression, CatBoost and LightGBM. The target is the explicitly defined substantiated issue type or actionability outcome, not a fabricated universal `is_fraud`. CatBoost's categorical handling makes it a plausible candidate, but its ordered boosting does not fix future-information or entity leakage. [CatBoost primary paper](https://papers.neurips.cc/paper_files/paper/2018/file/14491b756b3a51daac41c24863285549-Paper.pdf)

**Delay forecasting:** fraud labels are not required for time-to-completion modelling, but reliable follow-up is. Treat completion as the event and open works as right-censored only where observation through a known date is defensible. An absent completion row is not sufficient proof of follow-up. Capture cancellations, withdrawals, reporting delays and approved extensions; cancellation may be a competing event. Start with descriptive Kaplan–Meier and penalized Cox baselines before a survival forest. [Survival-analysis introduction](https://scikit-survival.readthedocs.io/en/stable/user_guide/00-introduction.html)

For either objective, reconstruct recommendation/sanction-time feature availability. Current completion amounts, last-payment dates, accrued totals and final review decisions cannot be earlier-time predictors. Separate later-time testing from held-out-authority generalization; ordinary group folds do not enforce chronology by themselves. Fit transforms inside each split. [Grouped and temporal validation guidance](https://scikit-learn.org/stable/modules/cross_validation.html)

If probabilities are eventually displayed, fit calibration on separate labelled data and assess reliability by cohort and time. A Brier score alone mixes calibration and discrimination, so also inspect calibration curves. [Probability calibration guidance](https://scikit-learn.org/stable/modules/calibration.html)

## 9. Architecture and workflow

The existing React + local Python API + read-only SQLite design remains suitable. This research adds a **batch model/scoring layer and explicit evidence channels**, not a replacement frontend or a cloud service.

```text
Preserved 18-source release
          |
          v
Identity, units, coverage and feature-availability checks
          |
          v
Parallel channels, each with its own eligibility and evidence:
  Operational rules | Peer cost/text | Experimental IF | Relationships
          |             |                  |                  |
          +-------------+------------------+------------------+
                                   |
                                   v
                 Local work dossier and separate review queues
                 + missing/conflicting-data warnings
                                   |
                                   v
                       Human evidence and disposition
                                   |
                                   v
                     Separate adjudication/evidence store
                                   |
                                   v
                     Approved labels -> new versioned study
```

### Stores and contracts

| Proposed store | Contents and guard |
|---|---|
| Frozen facts | Existing read-only prepared SQLite, raw provenance and dictionary; never train by mutating source tables |
| Versioned model artifacts | Feature contract, peer/reference membership, preprocessing, estimator/vectorizer or encoder revision, package versions and hashes |
| Derived scores/search cache | `work_id` or pair IDs, data release, as-of date, method version, eligibility, raw score, channel, rank/reference and evidence pointers |
| Review/evidence database | Case state, reviewer, disposition type, rationale, evidence IDs, timestamps, inclusion probability and model version viewed |
| Evaluation artifacts | Frozen experiment manifest, splits, known labels, selected sets, metrics and uncertainty; separate synthetic/real populations |

Training and indexing run as explicit local batch jobs. API requests read precomputed outputs and bounded evidence, not trigger retraining. A failed new job keeps the previous approved version active. Startup rejects mismatched fact/model versions; a model error cannot hide the baseline queue. Null/unsupported outputs carry reasons, and exact paise/identity contracts from the existing plan remain unchanged.

### Investigator sequence

1. Select the authorized scope and verify the release date.
2. Open the operational queue or a labelled comparison channel; see coverage and eligibility denominators.
3. Inspect a work dossier with lifecycle, settled-versus-pending amounts, source rows and conflicts.
4. For cost, request scope/quantity evidence; for pairs, verify physical identity/phase/location; for payments, obtain bank/invoice references; for delay, check receipt and extensions.
5. Record expected variation, data issue, substantiated issue or insufficient evidence. High-impact findings require independent review under the proposed governance workflow.
6. Track follow-up separately from scoring; preserve prior decisions and the evidence snapshot on reopening.

Display individual method outputs and reviewer confidence in evidence separately. Do not invent a combined 0–100 probability, average incomparable anomaly/embedding scores, or multiply overlapping screen counts into a unique-case total. If capacity must be divided among channels, agree and freeze that policy before evaluating its benefit. No arbitrary quota split is justified by this research.

## 10. Where an LLM belongs, if added

An LLM is optional and should not be the detector or decision maker. Begin with deterministic evidence summaries. Later, a local read-only assistant could explain an allowlisted aggregate query or retrieve approved guideline passages with citations. It must distinguish scheme text from row-specific evidence and refuse unsupported statements about fraud, beneficiary compliance or physical assets.

Do not give it arbitrary SQL, raw file paths, internet access, automatic case closure or authority to contact officials. Retrieved descriptions and attachments are untrusted input. Enforce access scope in the application, validate tool arguments and numeric answers, and require human approval for material actions. Prompt injection needs application controls, not just a stronger prompt. [OWASP prompt-injection prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)

Package any approved model ahead of use, load pinned local files and enforce offline mode. Hugging Face documents `HF_HUB_OFFLINE=1` and `local_files_only=True`; these settings should be supplemented by an outbound-network test. Downloading weights is a distinct setup step and must not upload project data. [Transformers offline operation](https://huggingface.co/docs/transformers/installation#offline-mode)

## 11. Evaluation needed to decide what is actually best

The next study should isolate contributions rather than compare a weak baseline with a bundle of unrelated improvements:

| Study | Fixed comparison | Evidence required |
|---|---|---|
| Text retrieval | Frozen weighted-token reference vs character TF-IDF; then union with E5 | Independently assembled pair truth, same retrieval/review budget, misses outside current blocks, language/scope strata |
| Numeric discovery | Frozen operational reference vs eligible IF and a bounded LOF challenger | Same eligibility population; adjudicated ML-only, rule-only, disagreements and randomly sampled unflagged works |
| Queue allocation | Existing A/B rankings vs a separately declared multi-channel policy | Equal total capacity/time, losses by existing issue family, reviewer workload and unresolved evidence |
| Later supervised model | Logistic baseline vs CatBoost/LightGBM | Representative adjudicated labels, temporal/group holdouts and independent calibration/test partitions |
| Delay model | Simple duration/survival baseline vs more complex survival model | Verified follow-up/censoring and supported time horizons; censoring-aware calibration/error measures |

Sample labels from all channels and from outside the selected queues, retaining selection probabilities. Training only on the most alarming reviewed cases creates selection bias. Unreviewed and insufficient-evidence cases are not negative labels. Obtain independent review for disagreements and important findings; freeze the rubric and maintain an untouched final evaluation set. Any later active-learning sample is for training, not a replacement for representative evaluation.

Primary operational outcome: substantiated, actionable issues per fixed review budget, with time and evidence-completion burden. Also report baseline-case displacement, issue-family and cohort coverage, unresolved proportion, reviewer disagreement and adverse reversals. Counts of alerts or a higher mean anomaly score are not evidence of value. Choose a meaningful minimum benefit and harm margins with the user/authority before outcome inspection; do not invent a universal training-label count or acceptance percentage.

Average precision and precision–recall analysis are useful for a later labelled ranking study, but an observed reviewed-only sample does not estimate population recall. Any outside-queue probability sample needs its own weighted analysis. [Average precision definition](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html)

For a live reviewer A/B study, use the linked-case/cluster-aware design in the existing architecture plan, maintain equal resources, calculate power from a separate feasibility pilot, and obtain required participation/data-use approvals. This research has neither run nor authorized that trial.

## 12. Implementation order and completion gates

1. **Read-only integration:** connect the complete fact release and existing A/B outputs; test all cohort/key/paise/provenance cases. This remains the immediate prototype milestone.
2. **Evidence workflow:** deliver dossiers, rule/cost/pair comparisons and separate local case management. A model is not useful if a reviewer cannot inspect or resolve its output.
3. **Lexical retrieval experiment:** implement character TF-IDF as a new method version, collect missing retrieval labels and measure candidates/cap hits/latency.
4. **Numeric ML experiment:** implement the eligible feature pipeline and shadow Isolation Forest; retain reference hashes, seed sensitivity, missingness audit and separate result tables.
5. **Model promotion study:** adjudicate the declared samples and compare equal-capacity outcomes. Promote only demonstrated benefit; otherwise keep the feature/model experimental.
6. **Conditional extensions:** evaluate E5 if lexical misses justify it; train supervised/survival models only when their distinct data prerequisites are met. LLM, GNN and computer vision remain optional later work.

For offline runtime, reuse the local application stack. A CPU-first deployment is a design target, not a measured latency promise. Inspect available RAM/dependencies during implementation and benchmark a bounded text batch before full indexing. No new model service, vector database or GPU is necessary merely to begin the tested data/evidence interface.

Completion of this research means that the approach, alternatives, feature contracts, workflow and validation gates are documented. The proposed new ML/text models are **not implemented or evaluated yet**. The current operational/scoring artifacts and raw data remain unchanged.

## 13. Reproducing the readiness counts

Run against the frozen `mplads_prepared.sqlite3` with a read-only connection. The first query gives the lifecycle/coverage counts; the second gives the lifecycle labels. The text probe counts `str.isascii()` and whether any character falls within Unicode U+0900–U+097F, treating null descriptions as empty strings. It must not be presented as language classification.

```sql
SELECT cohort, COUNT(*) AS works,
       SUM(in_sanctioned) AS sanctioned,
       SUM(in_completed) AS completed,
       SUM(has_successful_payment_evidence) AS success_evidence,
       SUM(missing_description_flag) AS missing_descriptions,
       SUM(peer_count >= 20) AS supported_peers
FROM Work_Features GROUP BY cohort;

SELECT lifecycle, COUNT(*) FROM Work_Features GROUP BY lifecycle;
```

Observed rows for the first query: Lok Sabha `(107937, 79881, 34940, 35721, 2, 78570)`; Rajya Sabha retired `(27166, 24524, 16282, 21271, 0, 14702)`; Rajya Sabha sitting `(25598, 19750, 10046, 14982, 1, 16200)`. These are counts, not new labels or changed source values.
