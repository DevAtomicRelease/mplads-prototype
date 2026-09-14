# PS 26102 — MPLADS Anomaly, Fraud & Inefficiency Detection

## Final Project Plan: Architecture, Workflow, AI/ML, Tech Stack & Data Pipeline

**Problem Statement:** SIH 2026 — PS 26102. *Development of an AI-powered system to detect anomalies, fraud, and inefficiencies in MPLAD Scheme implementation.*
**Snapshot reference date:** 2026-09-09 (explicit; not a source extraction timestamp).
**Scope of supplied data:** 18th Lok Sabha exports (plus a Rajya Sabha sitting/retired variant). Not all chambers or verified national completeness.

---

## 0. Purpose of this document

The repository already contains several iterations of a working solution. This plan **consolidates them into one final architecture**, states what is authoritative, retires what is superseded, and defines the remaining work needed to turn a rigorous back-end into a demo that wins on both *credibility* and *impact*.

The single most important design principle, inherited from the existing `six_source` work and kept as law:

> **No anomaly score is fraud evidence or a legal finding.** Every alert is a *request for evidence and human review*. Unavailable checks (asset photos, SC/ST tags, trust registration, GPS) are shown as **visibly unavailable**, never silently passed.

This honesty is a scoring differentiator for a government-facing tool, not a limitation to hide.

---

## 1. What the data actually is (ground truth for feature engineering)

Six immutable CSVs per cohort. Hash-locked in `six_source/common.py::EXPECTED`. Row grains and the correct join semantics were established by read-only audit:

| Source | File | Rows (LS) | Grain / handling |
|---|---|---:|---|
| Allocated limit | `01_allocated_limit.csv` | 543 | One row per MP·house·tenure. One explicit zero (not missing). |
| Calamity consent | `02_calamity_consent.csv` | 12 | MP-level consent context. **No work-level funding link.** |
| Works recommended | `03_works_recommended.csv` | 107,562 | Unique `WORK_RECOMMENDATION_DTL_ID`. Its `SANCTION_AMOUNT` is populated even on unsanctioned rows — do **not** treat as sanction. |
| Works sanctioned | `04_works_sanctioned.csv` | 79,881 | Unique work id. 375 absent from recommendation export. Membership here = observed sanction. |
| Works completed | `05_works_completed.csv` | 34,940 | Unique work id; all match a sanction. Membership overrides stage wording. |
| Expenditure | `06_expenditure.csv` | 57,349 | **Report row, not a verified transaction id.** One truncated final row → quarantine. |

**Critical join rules (already implemented, keep exactly):**
- The four work files are **not** disjoint sets nor a synchronized event log. Build the **union** of recommendation ∪ sanction work ids → **107,937 works**, one row per work.
- Completion joins one-to-one onto sanction. Expenditure is **aggregated per work before** joining (many payments → one work), never fanned out.
- MP allocation joins many-to-one on a **checked normalized key** `house|tenure|normalized_name` — no fuzzy entity merge.
- Distinct `VENDOR_ID`s stay distinct even when names match (`same_name_vendor_id_count` records the collision instead of merging).

**What is genuinely absent** (drives the "unavailable, not passed" list): transaction/invoice IDs, revised-sanction ledger, tax/retention breakdown, unit quantities, contractual due dates, receipt dates, SC/ST beneficiary-area tags, trust registration IDs, GPS coordinates, asset photos, physical-progress event history.

---

## 2. Decomposing the ask into detectable signals

Four buckets, each with a distinct modeling approach. This mapping is the backbone of the whole system.

| Bucket | Signal examples | Method | Label need |
|---|---|---|---|
| **A. Financial** | cost far outside peer distribution; payments > sanction; completion > sanction; repeated payment fingerprints; year-end spend spikes; vendor concentration | robust log-MAD z-score, deterministic deltas, HHI, Isolation Forest | none (unsupervised + rules) |
| **B. Execution** | duplicate/near-duplicate works; stalled open works; delayed sanction; completion without payment | weighted-token text similarity + IDA/activity blocking; aging thresholds | none |
| **C. Compliance** | sanction delay >45d; open >1 year; no payment >3 months; (SC/ST %, trust ceiling, jurisdiction — *when tags exist*) | **deterministic rule engine**, not ML | exact by construction |
| **D. Inefficiency** | chronically low utilization; skewed category mix; execution bottlenecks | ratios & aggregates at MP/IDA grain | none |

**Framing:** lead with **unsupervised anomaly detection + an explicit rule engine**. Supervised fraud classification is a **Phase-2 roadmap item** that only becomes possible once investigators label enough reviewed cases via the feedback loop (Section 8). This matches how real GovTech fraud systems bootstrap and is defensible to judges.

---

## 3. Final system architecture

```
                          IMMUTABLE SOURCE CSVs (hash-locked, 6 per cohort)
                                          │
        ┌─────────────────────────────────┼─────────────────────────────────┐
        ▼                                 ▼                                   ▼
  1. INGEST & CONTRACT            2. CONNECT & FEATURE-ENGINEER        (quarantine invalid
   - sha256 == contract            - union → 107,937 works             rows, never edit source)
   - profile nulls/dates           - lifecycle / cost / duplicate
   - quarantine bad rows           - MP / IDA / vendor / month rollups
        │                                 │
        ▼                                 ▼
  3. DETECTION LAYER  ────────────────────┴───────────────────────────┐
   A. Rule engine (deterministic compliance/ops screens)              │
   B. Cost outlier (prior-FY peer log-MAD z)                          │
   C. Duplicate/near-duplicate text screen (blocked, bounded)         │
   D. Vendor concentration (HHI per IDA·FY)                           │
   E. Isolation Forest (descriptive full-snapshot atypicality)       │
        │                                                             │
        ▼                                                             ▼
  4. COMPOSITE RISK SCORING (explainable)               5. OFFLINE A/B EVALUATION
   - priority_score = Σ disclosed rule weights, cap 100   - frozen protocol, seeds
   - reason_codes + Rule_Contributions (per-point trace)  - synthetic injection recovery
   - bands: Routine / Low / Medium / High                 - real-queue overlap (Jaccard)
        │                                                    at equal review budgets
        ▼
  6. LOCAL API (loopback, read-only SQLite, paginated, CSP-locked)
        │
        ▼
  7. ROLE-BASED DASHBOARDS + INVESTIGATION WORKSPACE
   - Ministry (MoSPI) · State Nodal · District Authority · MP views
   - case queue, financial/lifecycle evidence, payment ledger,
     vendor/MP/authority drill-down, duplicate pairs, map, exports
        │
        ▼
  8. HUMAN REVIEW & FEEDBACK LOOP
   - officer records outcome (Needs evidence / Expected variation /
     Data issue / Substantiated issue) → labeled examples
   - feeds Phase-2 supervised scoring
        │
        ▼
  9. AGENTIC NL QUERY ASSISTANT (differentiator)
   - natural-language questions answered over structured data + scores
   - text-to-SQL over the read-only view, cited rows, no free-text hallucination
```

**Authoritative modules (keep, harden):**
- `six_source/build.py` — the data + feature + detection pipeline. **This is the canonical engine.**
- `six_source/serve.py` — the loopback investigation API.
- `six_source/common.py` — versioned contracts, hashes, research sources.
- `evaluation_18/` — the frozen offline A/B protocol and synthetic benchmark.
- `mplads-prototype/` — the React/Vite front-end shell.

**Superseded → archive (do not extend):** `pipeline_research/` (three-source predecessor, kept only for reproducibility comparison), `data_preparation/local/*` older releases, `prototype-local-data/`, one-off `outputs/*` except the latest release. Move these under an `archive/` folder so the final tree reads cleanly.

---

## 4. Data pipeline (detailed, the canonical flow)

Stage numbers match `build.py`'s own `1/8 … 8/8` progress prints.

1. **Source contracts & quarantine** — read each CSV as strings (`utf-8-sig`, `keep_default_na=False`), assert row count **and** sha256 equal the frozen contract; refuse to run on drift. Profile blank/NA counts. Quarantine the one truncated expenditure row with a reason; never mutate source.
2. **One-work master + payment aggregation** — union recommendation/sanction, `combine_first` with sanction governing; parse money to **integer paise** (no float rupees), parse dates to ISO. Aggregate expenditure per work: split `Payment Success` vs `Payment In-Progress` (never summed together), compute `report_fingerprint` (SHA-256 of the row minus `Sno`) to measure repeat-report sensitivity **without asserting duplicate payment**.
3. **Lifecycle + strictly-prior-year cost features** — aging (`sanction_delay_days`, `sanction_age_days`, `days_since_last_success`…), chronology flags, and cost benchmarks that use **only earlier fiscal years** (same-year works never define their own benchmark — leakage guard).
4. **Bounded duplicate-candidate generation** — normalize text, block by `IDA·activity`, anchor on rare tokens, weighted-token (TF-style) similarity ≥0.88 retained / ≥0.96 for high-similarity review; guard against number conflicts, generic short text, and phase/continuation cues. Deterministic, bounded, **no exhaustive-recall claim**.
5. **Explained rules + separate unsupervised model** — the rule registry (Section 5) produces `priority_score` + per-point `Rule_Contributions`; Isolation Forest produces a **separate** descriptive `isolation_percentile` that is deliberately *not* mixed into the queue score.
6. **Entity rollups** — MP, IDA, vendor, vendor-connection edges, IDA·FY concentration (HHI), monthly payments, calamity consents.
7. **Outputs** — every table to CSV **and** an indexed SQLite (`mplads.sqlite3`) with the exact indexes `serve.py` expects. Plus `audit.json`, `review_workbook.json`, `artifact_hashes.json`.
8. **Reconciliation gate** — ~22 hard checks (membership counts, money sums to the paise, score↔contribution equality, no future events, source bytes unchanged). Build **fails closed** if any check fails.

**Reproducibility:** fixed `SEED=26102`, pipeline+common sha recorded in `audit.json`, independent rebuild in a separate directory compared by CSV/JSON hash (already practiced in `pipeline_research/artifacts_reproduced` and `evaluation_18/verify_repro.py`).

---

## 5. AI/ML work (concrete)

### 5.1 Deterministic rule engine (compliance + operations)
Disclosed weights, capped at 100. Current registry (keep, extend when tags arrive):

| Flag | Pts | Meaning | Required caution |
|---|--:|---|---|
| `pending_recommendation_45d_flag` | 12 | pending recommendation >45d | needs receipt/MCC/rejection record |
| `sanction_delay_45d_flag` | 8 | recommendation→sanction >45d proxy | not a confirmed statutory breach |
| `open_over_one_year_flag` | 20 | open past 1-yr anniversary | check due date & extensions |
| `no_payment_three_months_flag` | 12 | no payment row after 3 months | export coverage may be incomplete |
| `paid_over_sanction_flag` | 30 | successful payments > sanction | check revised sanction |
| `completion_over_sanction_flag` | 25 | completion actual > sanction | check approved scope |
| `repeat_payment_report_flag` | 15 | repeated report fingerprints | needs transaction ids to decide |
| `high_cost_peer_flag` | 12 | high prior-FY peer amount | quantities/specs absent |
| `high_similarity_review_flag` | 12 | similar work descriptions | distinct location/phase can be legit |

Bands: `0` Routine · `1–19` Low · `20–39` Medium · `40–100` High. `reason_codes` + `Rule_Contributions` make every point traceable — this is the explainability judges look for.

**Roadmap rules (activate only with scheme-owner sign-off + the missing tags):** SC/ST 15%/7.5% allocation, ₹75 lakh trust ceiling, jurisdiction-of-recommendation. Keep them coded but **visibly inactive** until data supports them.

### 5.2 Cost-outlier model
Prior-FY, per `state·activity` (≥20 peers, activity fallback), `log(1+INR)` median/MAD, robust z = `(x − median)/max(1.4826·MAD, 0.1)`. Flag when `z>3.5` **and** `amount/median ≥ 2`. No tuning to any label.

### 5.3 Duplicate / near-duplicate detection
Weighted-token similarity with IDA·activity blocking (Section 4.4). Emits `Duplicate_Candidates` pairs with guard flags. Production path: sentence-transformer embeddings + FAISS/pgvector + geospatial distance join (roadmap).

### 5.4 Vendor concentration (collusion *screen*, not proof)
HHI of successful-payment share per `IDA·FY`, top-vendor share, edge list `vendor·MP·IDA·IA·FY`. Production path: build the MP–IDA–vendor–payment graph, community detection / GNN embeddings (roadmap, high wow-factor).

### 5.5 Isolation Forest (unsupervised atypicality)
Seeded 100-tree NumPy implementation, subsample 256; features = log sanction amount, sanction delay, completion days, days-since-last-success, cost z, paid/sanction ratio, vendor count, with median imputation + missing indicators. Output is a **descriptive full-snapshot percentile**, explicitly separate from the queue score and **not** a fraud probability or forecast.

### 5.6 Trend & early-warning analytics (label-free, buildable now)
The PS explicitly asks for *predictive insights* and *early-warning mechanisms*. These do **not** require fraud labels and are built from the existing time fields:
- **Stagnation / aging velocity** — works whose `days_since_last_success` or `sanction_age_days` cross escalating buckets; an IDA's open-work backlog growing month over month.
- **Utilization pace vs fiscal calendar** — projected year-end utilization from run-rate; flag MPs/IDAs tracking to leave large balances unspent, and (separately) late-quarter spend spikes.
- **Spend drift** — month-over-month settled-payment change per state/IDA vs its own trailing median (simple seasonal/decomposition); surfaces abnormal acceleration for the Ministry view.
- **Leading indicators** — pending-recommendation and no-payment-after-3-months counts trend as an *early* signal before a work becomes a one-year breach.
These are descriptive/extrapolative early warnings, clearly labelled as projections, **not** calibrated fraud forecasts. Supervised prediction remains §5.8.

### 5.7 Evaluation (how we prove it works without fraud labels)
Two layers, per `evaluation_18/PROTOCOL.md`:
1. **Real-data retrospective queue comparison** — baseline A vs enhanced B at equal review budgets (5/10/20%); report count, Jaccard overlap, displaced cases, cohort mix, ties. **No** precision/FPR/money-saved claims on real rows.
2. **Controlled mechanism benchmark** — wholly synthetic coherent cases (9 positive + 9 hard-negative families), reference frozen to sanctions ≤ 31 Mar 2025, all synthetic events after. Report recovery difference B−A at 10% budget with a paired bootstrap 95% interval. Labels mean "constructed review-worthy mechanism", not real fraud.

Headline metrics for the pitch: **injected-anomaly recovery rate**, **100% deterministic rule coverage**, **explainability** (one-glance "why flagged"), and an explicit **human-in-the-loop / false-positive-cost** narrative.

### 5.8 Phase-2 (roadmap, stated in pitch, not built for MVP)
Supervised risk scoring trained on investigator feedback labels; CV ghost-asset verification on geotagged completion photos; GNN collusion detection at scale; live MIS/eSAKSHI integration.

---

## 6. Role-based dashboards & workspace

Ship **depth over breadth**: build the District Authority + Ministry views well, then State Nodal and MP.

| Persona | Primary need | Key views |
|---|---|---|
| **Ministry (MoSPI)** | national trends, systemic patterns | state/district risk heatmap, top-N high-risk IDAs, scheme-wide utilization & compliance, monthly spend trend |
| **State Nodal** | cross-district oversight | district-vs-district comparison, state risk table, pendency |
| **District Authority** | act on cases | case queue by band, per-work evidence (financial + lifecycle + payment ledger), vendor history, duplicate pairs, record review outcome |
| **MP** | own works status | traffic-light status of recommended works, flagged items, utilization vs allocation |

Cross-cutting: server-side filter/paginate (data is large), map view (Leaflet) once geodata exists, one-click evidence export (CSV/Excel workbook), local review history, validation/A-B results page. The existing `six-local.tsx` + `workspace.tsx` already implement the workspace shell and evidence sheet — extend, don't rewrite.

---

## 7. Agentic NL query assistant (the differentiator)

An official asks in plain language — *"Which districts in Bihar have the most works open beyond one year this FY?"* — and gets an answer generated over the structured data + risk scores, **with the underlying rows cited**.

- **Safe design:** constrained **text-to-SQL over the read-only SQLite view** (allow-listed columns/tables, `LIMIT`-capped, no writes), results rendered as a table + short natural-language summary. The model never invents numbers; every figure traces to a returned row.
- **Local-first:** to preserve the "no data leaves the device" guarantee, keep it optional/toggleable; if a hosted LLM is used for the demo, state it explicitly and never send raw PII — send schema + aggregated rows only.
- Plays directly to the team's RAG/agentic (LangGraph) strength and stands out to judges. Scope it as **one working demo query path**, not a full assistant, for the MVP.

---

## 8. Human review & feedback loop

Every flagged case an officer dispositions — `Needs evidence` / `Expected variation` / `Data issue` / `Substantiated issue` (already in `serve.py`) — becomes a **labeled training example**. This is what turns a purely unsupervised system semi-supervised over time and is the on-ramp to Phase-2 supervised scoring. Reviews are stored locally, versioned to the exact dataset build (write rejected if the dataset changed under the reviewer).

---

## 9. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Data / ML | Python, pandas, NumPy | Isolation Forest is a local seeded NumPy impl (no sklearn dependency at runtime); sklearn only for offline experiments |
| Text similarity | weighted-token now → sentence-transformers + FAISS/pgvector (roadmap) | duplicate detection |
| Graph | pandas edge list + HHI now → NetworkX / Neo4j / GNN (roadmap) | vendor concentration |
| Geospatial | Leaflet map + geopy distance (roadmap, needs coords) | duplicate geo-join, heatmaps |
| Storage | SQLite (indexed, read-only at serve time) → PostgreSQL + PostGIS (production) | object storage for photos/PDFs in production |
| API | stdlib `http.server` loopback now → FastAPI (production) | CSP-locked, host-checked, paginated, no query strings in logs |
| Frontend | React 19 + Vite + TypeScript, shadcn/@base-ui, Recharts, lucide | `mplads-prototype/` |
| Agentic layer | LangGraph text-to-SQL agent over the read-only view | differentiator |
| Reproducibility | fixed seed, sha256 contracts, independent-rebuild hash compare | build fails closed on drift |

**Security posture (already strong, keep):** loopback-only (`127.0.0.1`), exact-Host check, read-only DB URI, strict CSP, same-origin POST for reviews, no data sent to any external service by default, source bytes verified unchanged every build.

---

## 10. MVP scope vs full vision

| Layer | Hackathon MVP | Full vision (pitch, not built) |
|---|---|---|
| Data | supplied 6-CSV cohorts, hash-locked, quarantined | live eSAKSHI / state MIS integration |
| Detection | rules + cost + duplicate + HHI + Isolation Forest | GNN collusion, CV ghost-asset at scale |
| Scoring | disclosed weighted composite, explainable | learned scoring from investigator feedback |
| Dashboards | District + Ministry deep; State + MP present | 4 polished personas + MP mobile app |
| Agent | one working NL→SQL demo path | full conversational drill-down + report gen |
| Eval | offline A/B + synthetic recovery | prospective randomized officer trial (rollout gate) |

Judges reward a **narrow slice that works end-to-end** (ingest → detect → score → alert → dashboard → review) over a wide slice of disconnected mockups. The repo already has that slice; the remaining work is consolidation + the two differentiators (role dashboards, NL agent) + demo polish.

---

## 11. Execution plan (remaining work, ordered)

1. **Consolidate the tree** — mark `six_source/` canonical; move superseded iterations to `archive/`; update `README` to point at the one true build+serve path.
2. **Verify end-to-end on a clean machine** — `build.py` → reconciliation gate green → `serve.py` → workspace loads. Confirm the ~22 checks pass on the current dataset (row/hash contracts may need refreshing for the Rajya Sabha cohorts).
3. **Multi-cohort** — DONE. `six_source` now builds Lok Sabha + Rajya Sabha sitting/retired together into 160,701 namespaced works. Keys are `cohort:mpkey:id` (RS reuses raw work ids across MPs); `mp_key` is cohort-namespaced; contracts are per-cohort hash-locked; reconciliation is recomputed from source (21 checks pass). `--cohorts` selects a subset.
4. **Role dashboards** — DONE (first cut). New `/api/overview` endpoint + an Overview tab: national + per-cohort KPIs, top-states bar, monthly-settled line, a state risk heatmap (shaded by High-band share) with per-state metrics, and highest-risk district authorities; clicking a state drills to its authorities (State Nodal view) and "Investigate" opens the filtered queue (District view). Next polish: map choropleth, MP self-view.
5. **Map view** — wire Leaflet; degrade gracefully while coordinates are unavailable (state/district choropleth from names).
6. **NL→SQL agent** — DONE. Built as a *local, deterministic* intent parser (`six_source/nlq.py`) rather than an external LLM: it maps a plain-English question to an allow-listed, parameterised aggregate over `Work_Features` (plus vendor/month tables), and returns an interpretation, a source-tied summary, a formatted table, the exact generated SQL, and a caveat. No external service, no data egress, zero hallucination — every number reproducible from the shown SQL. Exposed at `/api/ask`; "Ask the data" tab in the UI with example prompts and drill-through. (A hosted-LLM path remains an optional future enhancement, gated on the same allow-listed SQL.)
7. **Evaluation surfacing** — render `evaluation_18` A/B + synthetic-recovery results in the validation page as pitch evidence.
8. **Demo script** — one flagged case walked end-to-end: signal → reason codes → evidence → officer disposition → how it feeds Phase-2.

---

## 12. Open questions to settle with the team

1. Single Lok Sabha cohort for the demo, or the full multi-cohort namespaced build?
2. Is the NL→SQL agent a core deliverable or the final-two-minutes stretch?
3. Local-only LLM for the agent (privacy-preserving) vs a hosted model for demo quality — and how to caveat it.
4. Which two dashboards get polish (recommend District + Ministry).
5. Do we invest in even a staged CV ghost-asset demo, or keep it strictly roadmap?

---

## 13. Robustness — acceptance criteria & risk register

### 13.1 Definition of done (per layer)
- **Data pipeline:** all source hashes match contract; all 21 reconciliation checks pass; independent rebuild reproduces identical output hashes; every invalid row quarantined with a reason.
- **Detection:** every queue point traces to a named rule in `Rule_Contributions`; Isolation Forest kept separate from the queue; no rule fires on a field the data does not contain (unavailable ≠ failed).
- **Evaluation:** offline A/B reruns deterministically to the same CSV/JSON hashes; synthetic recovery reported with a bootstrap interval; no precision/FPR claimed on real rows.
- **Dashboards:** each persona view answers its Section-6 question from real built tables; every flagged case shows a one-glance "why"; server-side pagination on the 100k-row table.
- **Agent:** every number in an answer traces to a returned row; queries are read-only, allow-listed, and `LIMIT`-capped; no free-text figures.
- **Review loop:** each disposition is stored locally, versioned to the exact dataset build, and rejected if the build changed underneath.

### 13.2 Coverage check against the problem statement
Anomalies ✓ (cost, duplicate, isolation) · fraud *signals* ✓ (payment/completion-vs-sanction, vendor concentration, repeat reports — as screens, never verdicts) · inefficiencies ✓ (utilization, aging, category mix) · trends ✓ (§5.6) · risk-based alerts ✓ (bands + reason codes) · predictive/early-warning ✓ (§5.6 now, §5.8 later) · 4-persona decision support ✓ (§6) · automated compliance monitoring ✓ (rule engine) · transparency/accountability ✓ (explainability + human-in-loop).

### 13.3 Risk register
| Risk | Mitigation |
|---|---|
| **False positive on a named MP/vendor** carries reputational harm | Nothing is labelled fraud; every alert is a review request; human-in-the-loop disposition is a first-class step, not an afterthought |
| **Source schema/hash drift** (new export) | Build fails closed on hash mismatch; profile and approve a new contract version before running |
| **Correlated flags inflate a score** | Weights disclosed; `Rule_Contributions` shows family displacement rather than hiding it |
| **Missing-data mistaken for compliance** | Unavailable checks rendered visibly unavailable; absence never scored as a pass |
| **Frontend `dist/six` build gap / port mismatch** | Resolved: `npm run build:six` emits `dist/six`, dev proxy aligned to `serve.py` :8766; end-to-end verified (build→serve→API+assets) |
| **Scope creep** (CV ghost-asset, GNN) | Explicitly Phase-2; MVP is the end-to-end slice |
| **Agent LLM leaking data / hallucinating** | Local-first, schema+aggregates only, read-only allow-listed SQL, cited rows |
| **Tight local disk / heavy roadmap libs** | MVP base pins only numpy/pandas/openpyxl; heavy libs (torch, sentence-transformers) deferred to when their layer is built |

---

*Design law restated: every alert requests evidence and human review; no liability is attributed to any MP, vendor, or authority from an anomaly flag; unavailable checks are shown as unavailable, not passed.*
