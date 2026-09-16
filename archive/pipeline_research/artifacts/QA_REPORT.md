# MPLADS raw-to-features quality report

Pipeline: core-2026-09-06-v1
Snapshot proxy: 2026-09-01

## Source reconciliation

| Source | Records | Visible amount (INR) | Reported total (INR) | Difference |
|---|---:|---:|---:|---:|
| works | 10,000 | 5276800278.00 | 41388495369.08 | 36111695091.08 |
| allocations | 543 | 83336673298.01 | 83336673298.01 | 0.00 |
| consents | 12 | 40567400 | 40567400 | 0 |

## Validation

- raw_sources_sha256_unchanged: True
- works_rows_preserved: True
- allocation_rows_preserved: True
- consent_rows_preserved: True
- unique_nonmissing_work_ids: True
- unique_allocation_mp_keys: True
- work_mp_join_complete: True
- consent_mp_join_complete: True
- allocation_exact_total_reconciles: True
- consent_exact_total_reconciles: True
- amount_conserved_after_joins: True
- mp_aggregate_amount_conserved: True
- ida_aggregate_amount_conserved: True
- strict_mp_prior_dates: True
- strict_ida_prior_dates: True
- scores_in_0_100: True
- score_contributions_reconcile: True
- no_self_duplicate_pairs: True
- no_repeated_duplicate_pairs: True

## Source quality and signals

```json
{
  "data_quality": {
    "allocation_amount_missing": 1,
    "work_required_input_missing_rows": 0,
    "work_source_replacement_character_rows": 0,
    "negative_date_order_rows": 0,
    "unknown_status_rows": 0,
    "mp_profiles_without_visible_works": 269
  },
  "screening_counts": {
    "potential_delay_over45": 7453,
    "early_stage_over180": 1979,
    "high_peer_amount": 698,
    "duplicate_candidate_works": 1375,
    "priority_bands": {
      "Routine": 7508,
      "Low": 1680,
      "Medium": 811,
      "High": 1
    }
  },
  "duplicate_method": {
    "pairs_examined": 61390,
    "candidate_pairs": 21092,
    "suppressed_common_postings": 0,
    "minimum_similarity": 0.84,
    "blocking": "Same state plus exact normalized text or one of each record's three rarest informative tokens; token postings over 250 suppressed. Exact blocks retained in full.",
    "similarity": "0.65 IDF-weighted token Jaccard + 0.35 character-trigram Dice. Exact normalized descriptions = 1.",
    "recall_status": "Candidate recall not measured on real audit labels; cross-state and cross-language matches are not searched."
  }
}
```

## Limitations

- The works extract has exactly 10,000 records and only 12.75% of its reported sanctioned value. Counts/totals reflect this extract, not complete scheme coverage.
- Sanctioned amounts and consent amounts are not expenditure, payments, released funds, or measured utilization.
- Cost signals compare whole sanctioned amounts. Work quantities, estimates/revisions, unit rates and specifications are absent; cost overruns cannot be measured.
- There are no audit outcomes or fraud labels. Screening priority has no validated fraud probability.
- No MP-ID crosswalk exists for the allocation/consent tables. Deterministic normalized names are used and duplicate master keys stop the build.
- Missing values remain null. MPs with no visible works have observed work count zero and null amount/rate profiles.
- The 45-day proxy lacks IDA receipt dates and Model Code of Conduct exclusions. 180-day aging is an analytic choice, not a statutory completion deadline.
- Latest sanction date is a snapshot proxy. Progress-update, actual-start and completion timestamps are absent.
- Peer, duplicate, batch, entity and isolation-forest features use the supplied snapshot; rebuild inside temporal training folds for predictive use.
- Calamity annual aggregation assumes consent financial year. Legal annual-basis interpretation and declaration/eligibility documents require verification.
- Trust annual screening uses sanctions rather than the complete recommendation ledger. Particular-trust term ceilings cannot be assessed without entity IDs and term history.
- SC/ST beneficiary targeting, vendor collusion, duplicate invoices, geospatial/ghost assets, and project cost overruns cannot be validated from these inputs.
- Constituency reservation labels do not identify the beneficiary community of a work. State mismatches are contextual, not proof of geographic non-compliance.

## Sources

- [MPLADS Guidelines 2023](https://www.mplads.gov.in/MPLADS/UploadedFiles/MPLADSGuidelinesApril2023.pdf)
- [Parliamentary reply on salient features](https://www.sansad.in/getFile/loksabhaquestions/annex/183/AS338_TsKdbP.pdf?source=pqals)
- [Isolation Forest, Liu et al. 2008](https://cs.nju.edu.cn/zhouzh/zhouzh.files/publication/icdm08b.pdf)

Source SHA256 values are recorded in audit.json. All source checksums are compared before and after processing.
