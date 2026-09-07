# BhuDrishti — Real Backend Integration & Testing Guide

> **Note**: The test datasets in `data/synthetic_test_data/` are **synthetic** and clearly labelled as such.
> They are designed to exercise the full harmonization pipeline but do **not** represent official government data.

---

## 1. Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10 or higher |
| Node.js | 18 or higher |
| Git | Any recent version |

---

## 2. Start the Backend

```powershell
cd d:\bhudrishti\backend

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start the FastAPI server
.\venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API is available at `http://localhost:8000`.
Interactive API documentation (Swagger UI): `http://localhost:8000/docs`

---

## 3. Start the Frontend

```powershell
cd d:\bhudrishti\frontend
npm run dev
```

Application available at `http://localhost:5173`.

The **Data Mode badge** in the top-right header will show:
- **Backend Connected** (green) — backend is reachable and data is live
- **Demo Mode** (amber) — backend unavailable; synthetic fixtures are active

---

## 4. Environment Variables

Create `frontend/.env.local` to override the default API URL:

```env
VITE_API_URL=http://localhost:8000
```

No backend environment variables are required for local SQLite development.

---

## 5. Synthetic Test Datasets

Located in `data/synthetic_test_data/`:

| File | Dataset Type | Features | Key Characteristic |
|------|-------------|----------|-------------------|
| `cadastral_survey_dwarka.geojson` | `cadastral` | 5 | Source reliability 0.95 |
| `municipal_gis_dwarka.geojson` | `municipal` | 5 | Source reliability 0.82 |
| `building_footprints_dwarka.geojson` | `building` | 3 | Source reliability 0.88 |

**Designed conflicts**: P-102 (Cadastral, 1,240 m²) vs M-458 (Municipal, 1,256 m²) — 16 m² area discrepancy with slight boundary shift.

---

## 6. Complete End-to-End Test Procedure

### Option A: One-Click Sample Seeding (Recommended)

```bash
# Via API
curl -X POST http://localhost:8000/datasets/sample-seed
```

Or in the UI: Navigate to `/datasets` → click **"Load Sample Datasets"** in the top header.

This runs validate + standardize automatically and seeds all three datasets.

---

### Option B: Manual Step-by-Step via curl

#### Step 1: Upload Datasets

```bash
curl -X POST "http://localhost:8000/datasets?dataset_type=cadastral" \
  -F "file=@d:/bhudrishti/data/synthetic_test_data/cadastral_survey_dwarka.geojson"

curl -X POST "http://localhost:8000/datasets?dataset_type=municipal" \
  -F "file=@d:/bhudrishti/data/synthetic_test_data/municipal_gis_dwarka.geojson"

curl -X POST "http://localhost:8000/datasets?dataset_type=building" \
  -F "file=@d:/bhudrishti/data/synthetic_test_data/building_footprints_dwarka.geojson"
```

Expected response (per dataset):
```json
{"id": 1, "filename": "cadastral_survey_dwarka.geojson", "status": "uploaded", "dataset_type": "cadastral"}
```

#### Step 2: List All Datasets

```bash
curl http://localhost:8000/datasets
```

#### Step 3: Validate Geometries

```bash
curl -X POST http://localhost:8000/datasets/1/validate
curl -X POST http://localhost:8000/datasets/2/validate
```

Expected:
```json
{"dataset_id": 1, "valid": true, "issues": []}
```

#### Step 4: Standardize (CRS Reproject + Field Mapping via rapidfuzz)

```bash
curl -X POST http://localhost:8000/datasets/1/standardize
curl -X POST http://localhost:8000/datasets/2/standardize
```

Expected:
```json
{
  "dataset_id": 1, "status": "standardized",
  "crs": "EPSG:4326", "feature_count": 5,
  "features_created": 5, "unmapped_fields": []
}
```

#### Step 5: Run M5 Candidate Matching Engine

```bash
curl -X POST http://localhost:8000/matching/run
```

Expected: Array of 5 pairwise match candidates with geometric IoU, centroid proximity, and confidence scores.

#### Step 6: Retrieve Match Results

```bash
curl http://localhost:8000/matching
```

#### Step 7: Detect Conflicts

```bash
curl -X POST http://localhost:8000/conflicts/detect
```

Expected: At minimum 1 conflict — area discrepancy between P-102 and M-458 (delta: ~16 m²).

#### Step 8: Generate Recommendations

```bash
curl -X POST http://localhost:8000/reconciliation/run
```

Expected: `prefer_source` action recommending Cadastral (higher reliability).

#### Step 9: Submit Human Review Decision

```bash
curl -X POST http://localhost:8000/reviews/1 \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer": "Senior Land Revenue Officer",
    "decision": "accept",
    "comment": "Approved cadastral boundary preference based on ground survey reliability 0.95."
  }'
```

Expected:
```json
{"conflict_id": 1, "decision": "accept", "status": "recorded"}
```

#### Step 10: Retrieve Harmonized Output

```bash
curl http://localhost:8000/harmonized
```

Expected: GeoJSON `FeatureCollection` with all harmonized features and source lineage metadata.

---

## 7. Backend Test Suite

```powershell
cd d:\bhudrishti\backend
.\venv\Scripts\python -m pytest tests -q --tb=short
```

**Expected result**: `40 passed, 4 skipped`

---

## 8. Frontend Production Build

```powershell
cd d:\bhudrishti\frontend
npm run build
```

**Expected result**: Clean Vite build, ~6s, no TypeScript errors.

---

## 9. Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `422 Unprocessable Entity` on upload | File format incorrect or wrong `dataset_type` | Use `.geojson` files from `data/synthetic_test_data/`; ensure `dataset_type` is `cadastral`, `municipal`, or `building` |
| `404 Dataset not found` on validate/standardize | Dataset ID doesn't exist | Run list: `curl http://localhost:8000/datasets` to confirm IDs |
| Matching returns empty | No standardized features in DB | Run standardize step for both datasets first |
| Frontend shows "Demo Mode" | Backend not running or CORS issue | Start backend first; check `VITE_API_URL` in `.env.local` |
| `Connection refused` | Backend not running | Run `uvicorn app.main:app --port 8000 --reload` from `backend/` |

---

## 10. API Prefix Reference

All routes are at the root (`/`) — **no `/api/v1` prefix**.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Backend health check |
| `/datasets` | GET | List all datasets |
| `/datasets` | POST | Upload new dataset |
| `/datasets/{id}` | GET | Get dataset by ID |
| `/datasets/{id}/validate` | POST | Run geometry validation |
| `/datasets/{id}/standardize` | POST | CRS reproject + field mapping |
| `/datasets/{id}/repair` | POST | Topology repair via shapely.make_valid |
| `/datasets/{id}/geojson` | GET | Get features as GeoJSON |
| `/datasets/sample-seed` | POST | Seed Dwarka sample project |
| `/matching` | GET | List match candidates |
| `/matching/run` | POST | Run M5 matching engine |
| `/conflicts` | GET | List detected conflicts |
| `/conflicts/detect` | POST | Run conflict detection |
| `/reconciliation` | GET | List recommendations |
| `/reconciliation/run` | POST | Run recommendation engine |
| `/reviews` | GET | List review decisions |
| `/reviews/{conflict_id}` | POST | Submit human review |
| `/harmonized` | GET | Get harmonized GeoJSON output |
