# SIH 2026 — Problem Statement 26102: Context & Pipeline Breakdown
### AI-Powered Anomaly, Fraud & Inefficiency Detection for MPLADS

---

## 1. Problem Statement Snapshot

| Field | Detail |
|---|---|
| **PS ID** | 26102 |
| **Title** | Development of an AI-powered system to detect anomalies, fraud, and inefficiencies in MPLAD Scheme implementation |
| **Domain** | GovTech / Public Finance Analytics / FinTech-for-Government |
| **Core ask** | An AI/ML platform that ingests MPLADS financial + project-execution data and surfaces anomalies, fraud signals, and inefficiencies through risk-based alerts and dashboards |
| **Primary users** | Members of Parliament (MPs), State Nodal Authorities, District Authorities, Ministry of Statistics & Programme Implementation (MoSPI) |
| **Source** | sih.gov.in/sih2026PS |

---

## 2. Understanding the Domain: What MPLADS Actually Is

You cannot design good anomaly detection without knowing what "normal" looks like. Here is the operational skeleton of the scheme, drawn from publicly available government sources — this is the ground truth your feature engineering and rule engine should encode.

**Structure of the scheme:**
- MPLADS is a Central Sector Scheme (since 1993) letting each MP recommend developmental works in their area — durable community assets, civic amenities.
- Each MP gets an annual entitlement (historically ₹5 crore/year), released in **two installments**, and funds are **non-lapsable** (unspent balance carries forward rather than expiring) — this alone is a rich anomaly signal, since "use-it-or-lose-it" assumptions in a naive model would be wrong.
- **Lok Sabha MPs** recommend works within their own constituency; **Rajya Sabha MPs** anywhere in their state of election; **nominated MPs** anywhere in the country.
- MPs must direct at least **15% of funds to SC-inhabited areas** and **7.5% to ST-inhabited areas** — a hard compliance rule your system should check per MP, per year.
- There's a **₹75 lakh ceiling** on assets built through trusts/societies (as opposed to government implementing agencies) — another explicit rule-check.
- Funds flow **MoSPI → District Authority**, never directly to the MP. The District Collector/Magistrate/Commissioner is the implementing authority who sanctions works, engages an implementing agency, executes on ground, and reports back.
- Guideline SLA: sanctions should ideally be accorded **within 45 days** of receiving the MP's recommendation.

**Actors in the data flow (map these to your schema and to your dashboard personas):**

| Actor | Role | What they'd want from the AI system |
|---|---|---|
| Member of Parliament | Recommends works | "Are my recommended works progressing? Any of my works flagged?" |
| State Nodal Department | Oversees state-level implementation | Cross-district comparison, state-level risk heatmap |
| District Authority (Collector's office) | Sanctions, executes, reports | Case-level red flags, contractor history, inspection scheduling |
| Implementing Agency / Contractor | Executes the physical work | (Not a primary dashboard user, but a first-class *entity* in your fraud graph) |
| MoSPI (Ministry) | Policy, funds release, monitoring | National-level trends, state rankings, systemic fraud patterns |
| Auditors / CAG (implicit) | Post-facto audit | Drill-down evidence trail, exportable audit reports |

---

## 3. Decomposing "Anomalies, Fraud, and Inefficiencies" into Detectable Signals

The problem statement is intentionally broad. The real engineering work is translating vague terms into concrete, computable signals. Break it into four buckets:

### A. Financial / Expenditure Anomalies
- Cost estimates far outside the historical distribution for a given work category + region (e.g., a community hall costing 3x the median for similar halls in similar districts).
- Sudden spikes in expenditure velocity right before financial year-end (classic "use it or lose it" fraud pattern even though funds are technically non-lapsable — pressure to *show* utilization still exists).
- Payments released disproportionately to a small number of vendors/contractors across many different MPs or districts (possible collusion or shell-vendor pattern).
- Mismatch between sanctioned amount, released amount, and expenditure reported — gaps that never get reconciled.
- Round-number or suspiciously repeated invoice amounts.

### B. Work-Execution / Project Anomalies
- **Duplicate works**: near-identical work descriptions/locations sanctioned more than once (possibly under different MPs or years) — this is an NLP + geospatial similarity problem.
- **Ghost assets**: work marked "completed" with no verifiable geotagged photo, or a photo that doesn't match the claimed asset type/location (computer vision + metadata cross-check).
- **Delayed projects**: works sanctioned long ago with no progress updates, or progress updates that have stalled — needs a "project aging" and stagnation detector.
- **Cost overruns without justification**: revised estimates that balloon mid-execution without a linked change-order/reason code.

### C. Compliance / Governance Deviations
- SC/ST allocation percentage falling below the 15%/7.5% mandate, per MP per year.
- Sanctions taking far longer than the 45-day guideline.
- Trust/society-executed works exceeding the ₹75 lakh ceiling.
- Works recommended outside an MP's permitted geographic jurisdiction.

### D. Utilization Inefficiencies (not fraud, but bad outcomes)
- Districts/MPs with chronically low fund utilization rates.
- High sanction-to-completion time even where cost is normal (execution bottlenecks, not corruption).
- Skewed work-category distribution (e.g., a district recommending only one type of asset — could indicate lack of local needs assessment, or a preferred-contractor arrangement).

This A/B/C/D split matters because **each bucket needs a different modeling approach** — see Section 6.

---

## 4. Data Landscape

What the model needs to ingest (map to whatever the SIH dataset/mock-data provides, since a real production MPLADS database won't be handed to a hackathon team):

| Data category | Example fields | Likely anomaly use |
|---|---|---|
| Sanction records | Work ID, MP ID, district, category, sanctioned amount, sanction date, recommendation date | SLA compliance, duplicate detection |
| Cost estimates | Estimated cost, revised cost, category benchmarks | Cost-overrun / outlier detection |
| Expenditure / payments | Installment amounts, dates, vendor ID, payment mode | Financial anomaly detection, vendor graph |
| Work progress | Status (sanctioned/in-progress/completed), % physical progress, last updated date | Delay / stagnation detection |
| Asset creation proof | Geotagged photos, completion certificates, inspection reports | Ghost-asset detection (CV) |
| Vendor / contractor master | Vendor ID, registration details, past work history | Collusion / shell-vendor graph analysis |
| SC/ST tagging | Beneficiary category flag per work | Compliance-rule checking |
| Historical fraud/audit flags (if available) | Past confirmed fraud cases | Supervised model training / evaluation |

If a real dataset isn't provided, the realistic hackathon path is to **synthesize a plausible dataset** that mirrors these fields (with injected anomalies you control), since MPLADS public data (mplads.gov.in, data.gov.in) is aggregate/state-wise rather than granular enough for row-level ML out of the box — worth checking during the hackathon, but plan for synthetic augmentation regardless.

---

## 5. End-to-End Technical Pipeline

```
┌─────────────┐   ┌──────────────┐   ┌───────────────┐   ┌──────────────────┐
│  Data        │   │ Cleaning /   │   │ Feature        │   │ Anomaly / Fraud   │
│  Ingestion   │──▶│ Standardize  │──▶│ Engineering    │──▶│ Detection Models  │
└─────────────┘   └──────────────┘   └───────────────┘   └────────┬──────────┘
                                                                    │
┌─────────────┐   ┌──────────────┐   ┌───────────────┐             ▼
│ Dashboards / │◀──│ Alerting &   │◀──│ Composite Risk │◀───────────┘
│ Decision     │   │ Rules Engine │   │ Scoring        │
│ Support      │   └──────────────┘   └───────────────┘
└──────┬───────┘
       │
       ▼
┌─────────────┐
│ Human review │──▶ feedback loop back into model training
│ & labeling   │
└─────────────┘
```

### 5.1 Data Ingestion Layer
- Batch ingestion of structured records (CSV/DB dumps of sanctions, expenditure, progress) + unstructured artifacts (completion photos, inspection PDFs).
- Schema normalization across states/districts, since real government data is notoriously inconsistent in formatting.

### 5.2 Cleaning & Standardization
- Entity resolution: same contractor/vendor spelled differently across records, same work location geocoded inconsistently.
- Currency/unit normalization, date parsing, missing-value handling.
- De-duplication of MP/district/work identifiers.

### 5.3 Feature Engineering
Build features at multiple **granularities** — this is the crux of a good system:
- **Per-work**: cost vs. category benchmark (z-score), sanction-to-completion duration, revision count, SC/ST flag correctness.
- **Per-MP**: utilization rate, category diversity, SC/ST compliance %, average sanction delay.
- **Per-district**: works-per-inspector ratio, completion rate, average cost-per-category vs. state median.
- **Per-vendor**: number of distinct MPs/districts worked with, average contract value, win-rate concentration (Herfindahl-type index for collusion signals).

### 5.4 Anomaly / Fraud Detection Models (map to the A/B/C/D buckets)

| Bucket | Technique | Notes |
|---|---|---|
| Financial anomalies | Isolation Forest / Autoencoder / robust z-score on cost & payment features | Unsupervised — no fraud labels needed to start |
| Duplicate works | Sentence embeddings (work description) + geospatial distance clustering | NLP similarity + geo join |
| Ghost assets | CV model (object/scene classification) on geotagged completion photos vs. claimed category; EXIF/geotag cross-validation | Needs an image dataset — can mock for demo |
| Vendor collusion | Graph construction (MP–district–vendor–payment edges) + community detection / GNN embeddings | High "wow factor" for judges, moderate complexity |
| Delay / stagnation | Survival analysis or simple threshold-based aging buckets on progress timestamps | Simple to build, high practical value |
| Compliance deviations | Deterministic rule engine (not ML) — SLA days, SC/ST %, cost ceilings | Don't over-engineer this with ML; rules are exact |
| Trend/systemic patterns | Time-series decomposition per state/district (seasonal spend spikes, drift) | Good for the Ministry-level dashboard |

**Important framing for a hackathon**: pure supervised fraud classifiers are unrealistic without labeled historical fraud cases (government data won't have "is_fraud" columns). Lead with **unsupervised anomaly detection + explicit rule engine**, and describe supervised learning as the "Phase 2, once auditors label enough flagged cases" roadmap — this is honest and matches how real GovTech fraud systems bootstrap (rules + anomaly detection first, supervised models later from investigator feedback).

### 5.5 Composite Risk Scoring
- Combine multiple signals per work/MP/district into a single 0–100 risk score (weighted sum or a simple logistic model once you have any labeled feedback).
- Keep it **explainable**: show *which* sub-signals contributed to the score (e.g., "Cost overrun: 40%, Delay: 30%, Vendor concentration: 30%") — explainability is a strong differentiator for a government-facing tool and something judges will explicitly look for.

### 5.6 Alerting & Rules Engine
- Deterministic checks (SLA breach, SC/ST %, ceiling breach) fire immediately, independent of the ML pipeline.
- ML-driven risk scores above a threshold generate a "review case" routed to the relevant District Authority / State Nodal Authority.

### 5.7 Dashboards & Decision Support (role-based)
- **MP view**: status of their own recommended works, simple traffic-light flags.
- **District Authority view**: case queue of flagged works needing action, contractor history lookup.
- **State Nodal view**: district-vs-district comparison, state risk heatmap.
- **Ministry (MoSPI) view**: national trends, top-N highest-risk districts/states, scheme-wide utilization and compliance stats.

### 5.8 Feedback Loop
- Every flagged case an authority marks "confirmed issue" / "false positive" becomes a labeled training example — this is how the system improves from purely unsupervised to semi-supervised over time. Design this loop explicitly in your architecture diagram; it shows judges you understand this is a *living* system, not a one-shot model.

---

## 6. Suggested Tech Stack

Given your existing toolkit (Python, LangGraph agentic pipelines, RAG, computer vision experience):

- **Data/ML**: Python, pandas, scikit-learn (Isolation Forest, clustering), PyTorch/TensorFlow only if you build the CV or GNN component seriously.
- **NLP similarity**: sentence-transformers embeddings + a vector store (FAISS/pgvector) for duplicate-work detection.
- **Graph**: NetworkX for a hackathon-scale vendor/collusion graph; mention Neo4j/GNN as the production-scale path.
- **Geospatial**: geopy/Turf-equivalent for distance-based duplicate detection; a map view (Leaflet/Mapbox) in the dashboard.
- **Backend**: FastAPI serving model outputs + rule engine.
- **Frontend**: React dashboard (role-based views), charts via Recharts/Plotly.
- **Agentic layer (your differentiator)**: a LangGraph agent that lets an official ask natural-language questions ("Which districts in Bihar have the worst SC/ST compliance this year?") and get an answer generated over the structured data + risk scores — this plays directly to your existing RAG/agentic strengths and would stand out.
- **Storage**: PostgreSQL (+PostGIS for geo) for structured records; object storage for photos/PDFs.

---

## 7. Realistic MVP Scope vs. Full Vision

| Layer | Hackathon MVP (36–48 hrs) | Full Vision (mentioned in pitch, not built) |
|---|---|---|
| Data | Synthetic dataset mirroring MPLADS schema, with injected anomalies you control | Live integration with MPLADS MIS / state databases |
| Detection | Rule engine (SLA, SC/ST%, ceiling) + 2–3 unsupervised models (cost outliers, duplicate works, delay detection) | Full GNN-based collusion detection, CV-based ghost-asset verification at scale |
| Scoring | Simple weighted composite risk score, explainable breakdown | Learned scoring model retrained from investigator feedback |
| Dashboard | 2 role views (District Authority + Ministry) built well, rather than 4 views built shallowly | All 4 stakeholder dashboards, mobile app for MPs |
| Agentic layer | One working natural-language query demo over the data | Full conversational assistant with drill-down and report generation |

Judges reward a **narrow slice that actually works end-to-end** (ingest → detect → score → alert → dashboard) far more than a wide slice of disconnected mockups.

---

## 8. Evaluation / Success Framing for the Pitch

Since there's no ground-truth fraud label to compute precision/recall against, frame evaluation as:
- **Injected-anomaly recovery rate**: what % of anomalies you deliberately planted in synthetic data does the system catch?
- **Rule-compliance coverage**: does it correctly flag every synthetic SLA/SC-ST/ceiling violation? (This should be ~100%, since it's deterministic.)
- **Explainability**: can a non-technical district officer understand *why* a case was flagged, in one glance?
- **False-positive cost narrative**: acknowledge that in a government context, false positives on named contractors/MPs carry reputational risk — mention a human-in-the-loop review step as a design safeguard, not an afterthought.

---

## 9. Open Questions to Settle with Your Team Before Building

1. Will you use SIH-provided data (if any is released for this PS) or build your own synthetic dataset? Decide early — this determines your Day-1 plan.
2. How deep do you go on the computer-vision "ghost asset" detector — is it a real trained model or a convincing demo on a few staged images?
3. Do you build the full 4-persona dashboard or concentrate polish on 1–2 views?
4. Is the LangGraph natural-language query agent a core deliverable or a stretch goal for the demo's final two minutes?
5. Who owns the rule engine (compliance checks) vs. the ML anomaly layer — keep these decoupled in code so one team member can own each.

---

## 10. Background Sources Used for MPLADS Domain Facts
Publicly available scheme information was drawn from Ministry of Statistics & Programme Implementation guideline summaries, PIB releases, and general reference sources (incl. Wikipedia's MPLADS entry) on fund entitlement, SC/ST allocation rules, the 45-day sanction guideline, and the ₹75 lakh trust ceiling. Verify current figures against the latest MPLADS Guidelines 2023 revision before finalizing your rule engine, since entitlement amounts and thresholds are periodically revised.
