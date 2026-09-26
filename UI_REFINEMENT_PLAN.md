# Frontend refinement acceptance plan

Requested scope: repair Insights, restore a sourced India overview map, provide entity
details, recognize named-entity queries, standardize table search/page navigation,
reorganize A/B and research evidence, and align architecture/completion documentation.

Preserve original CSVs and review history. Do not publish data or claim fraud accuracy.

- [x] Shared table search and direct page navigation, with full-dataset server filtering.
- [x] Authority/member/vendor profile API and contextual detail views.
- [x] Named-entity question resolution with explicit ambiguity handling and regression tests.
- [x] India map with local geometry, provenance, coverage and accessible state selection.
- [x] Structured Insights, A/B and research sections with legible charts and evidence tables.
- [x] Updated architecture, acceptance checklist and verified frontend/backend tests.

Verification: 49 backend regressions, four report-parser regressions, type checking,
lint and production build. Browser acceptance evidence and remaining certification
limits are recorded in COMPLETION_CHECKLIST.md. Raw analytical release and review
history were not overwritten. The map is sourced, not certified official geometry;
the query parser remains bounded and A/B remains synthetic development evidence.
