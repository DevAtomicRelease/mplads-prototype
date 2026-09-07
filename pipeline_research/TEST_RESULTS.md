# Regression test results

Run date: 6 September 2026. Command: `python -B test_pipeline.py`.

Nine tests ran and passed, with no skipped tests:

- Honorific and punctuation normalization without deleting substrings inside names.
- India financial-year boundary on 31 March and 1 April.
- Strictly earlier history, same-day exclusion, and inclusive 90-day lookback start.
- Unknown historical amounts propagate as null instead of becoming zero.
- Leave-current-row-out peers and degenerate MAD/IQR fallback.
- Duplicate corroboration and continuation safeguard.
- Seeded Isolation Forest determinism, constant-input result, and recovery of one deliberately extreme numeric fixture.
- Missing-value and ISO-date JSON serialization.
- Saved source audit, source-row conservation, missing allocation and extract-coverage checks.

These are implementation regression tests. The artificial extreme-point fixture is a known-answer numeric check, not measured fraud accuracy. The separate A/B evaluation reports controlled recovery and temporal queue comparisons.
