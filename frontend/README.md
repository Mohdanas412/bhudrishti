# Frontend (M1 dashboard/UI, M2 map/GIS)

- `src/pages/` — Dashboard, Data Sources, Conflict Investigation, Human Review (M1)
- `src/map/` — MapLibre GL layers, conflict highlighting, before/after (M2)
- `src/components/` — shared UI
- `src/mock/*.json` — frozen contracts (match, conflict, recommendation). Build against these until the real API is ready; the shapes will not change without a team-wide heads up.

Swap `src/mock/*.json` reads for `fetch(VITE_API_BASE_URL + ...)` once M3's endpoints are live — same shape, so this should be a near drop-in change.
