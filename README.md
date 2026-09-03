# BhuDrishti — SIH26013

Automated Integration and Intelligent Harmonization of Multi-source Geospatial Data for Urban Land Record Management.

Single source of truth for scope/architecture: `docs/Idea_Playbook_From_Zero_to_Hero.pdf` (add it to `docs/` after cloning).

## Quick start (everyone)

```bash
git clone <repo-url>
cd bhudrishti
cp .env.example .env
docker compose up --build
```

- Backend: http://localhost:8000/docs (FastAPI auto-generated OpenAPI)
- Frontend: http://localhost:5173
- DB: postgres on localhost:5432 (PostGIS enabled)

If Docker/PostGIS fails to start on your machine within the first 2 days, use the SQLite+GeoPandas fallback documented in `backend/app/db/README.md` — don't block on it, flag it in standup.

## Role-based entry points

Read **CONTRIBUTING.md** first (branching + PR rules), then jump to your folder:

| Member | Folder | First file to open |
|---|---|---|
| M1 — Frontend product | `frontend/src/pages`, `frontend/src/components` | `frontend/src/mock/*.json` (frozen contracts) |
| M2 — GIS frontend | `frontend/src/map` | `docs/contracts/*.json` |
| M3 — Backend | `backend/app/api`, `backend/app/services` | `backend/app/main.py` |
| M4 — GIS processing | `backend/app/engines/gis` | `backend/app/engines/gis/README.md` |
| M5 — Intelligence | `backend/app/engines/matching`, `.../reconciliation` | `docs/contracts/*.json` |
| M6 — Database + QA | `database/`, `backend/tests` | `database/schema.sql` |

Nobody waits on anybody: contracts in `docs/contracts/` are frozen on Day 1. M3 returns mock/hard-coded responses until M4/M5 land real logic.
## Team Contribution 
Rishi - Project Setup and Development