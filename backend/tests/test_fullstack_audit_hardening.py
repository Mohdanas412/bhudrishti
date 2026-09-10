"""
Comprehensive automated tests for BhuDrishti full-stack audit and hardening.
Covers:
1. Multi-format CSV ingestion & coordinate inversion auto-detection
2. ULPIN & Khasra rule-based matching boosts & [0, 100%] clamping
3. STRtree indexing & auto_match_candidates pruning
4. Parcel Merge (/harmonized/merge)
5. Parcel Split (/harmonized/split)
6. Bulk Auto-Match (/harmonized/auto-match)
7. Certified Review States (APPROVED, REJECTED, FLAGGED)
8. RoW Corridor Buffer Encroachment Analysis (/geoai/analysis/row-buffer)
9. Analytics Summary, Heatmap & Multi-format Exports (/analytics/...)
"""

import pytest
from app.engines.gis.ingestion import ingest_dataset
from app.engines.matching.engine import MatchResult, auto_match_candidates
from app.engines.matching.scoring import ScoreBreakdown, score_features
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Multi-format Ingestion & Coordinate Inversion Detection
# ---------------------------------------------------------------------------

def test_csv_ingestion_with_coordinate_inversion_detection(tmp_path):
    # Latitude outside [-90, 90] with longitude inside [-90, 90] should be inverted
    csv_content = """parcel_id,latitude,longitude,owner,area_sqm
P-CORR-1,28.6139,77.2090,Ramesh Kumar,1200
P-SWAP-2,77.2095,28.6145,Priya Singh,1350
"""
    csv_path = tmp_path / "test_parcels.csv"
    csv_path.write_text(csv_content, encoding="utf-8")

    res = ingest_dataset(str(csv_path))
    gdf = res.gdf
    assert len(gdf) == 2
    assert "geometry" in gdf.columns

    # Verify coordinates are in valid [lon, lat] order where -180 <= x <= 180 and -90 <= y <= 90
    for geom in gdf.geometry:
        assert -180.0 <= geom.x <= 180.0
        assert -90.0 <= geom.y <= 90.0
        # Specifically for Delhi region, x ~ 77 and y ~ 28
        assert 70.0 <= geom.x <= 85.0
        assert 20.0 <= geom.y <= 35.0


# ---------------------------------------------------------------------------
# 2. Rule Matching Boosts & [0, 100%] Clamping
# ---------------------------------------------------------------------------

def test_ulpin_and_khasra_matching_boost():
    feat_a = {
        "id": "A1",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[77.208, 28.613], [77.209, 28.613], [77.209, 28.614], [77.208, 28.614], [77.208, 28.613]]]
        },
        "ulpin": "28010200000001",
        "khasra_no": "104/2",
    }
    feat_b_exact = {
        "id": "B1",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[77.208, 28.613], [77.209, 28.613], [77.209, 28.614], [77.208, 28.614], [77.208, 28.613]]]
        },
        "ulpin": "28010200000001",
        "khasra_no": "104/2",
    }

    breakdown = score_features(feat_a, feat_b_exact)
    # Score should be strictly clamped in [0, 100]
    assert 0 <= breakdown.score <= 100
    assert breakdown.score >= 95
    assert "ulpin" in breakdown.matched_attributes
    assert "khasra_no" in breakdown.matched_attributes


def test_auto_match_candidates_partitioning():
    fake_breakdown = ScoreBreakdown(score=95, components={}, matched_attributes=(), differing_attributes=())
    matches = [
        MatchResult("A1", "B1", 95, "matched", fake_breakdown),
        MatchResult("A2", "B2", 82, "review", fake_breakdown),
        MatchResult("A3", "B3", 45, "unmatched", fake_breakdown),
    ]

    partitioned = auto_match_candidates(matches, threshold=90)
    assert len(partitioned["auto_approved"]) == 1
    assert partitioned["auto_approved"][0].feature_a == "A1"
    assert len(partitioned["review_queue"]) == 1
    assert partitioned["review_queue"][0].feature_a == "A2"
    assert len(partitioned["unmatched"]) == 1
    assert partitioned["unmatched"][0].feature_a == "A3"


# ---------------------------------------------------------------------------
# 3. Parcel Merge Endpoint (/harmonized/merge)
# ---------------------------------------------------------------------------

def test_harmonized_parcel_merge():
    payload = {
        "parcel_ids": ["P-101", "M-456"],
        "target_parcel_id": "HARM-P-101-MERGE",
        "combined_owner": "Harmonized Joint Owner"
    }
    r = client.post("/harmonized/merge", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "merged"
    assert "merged_feature" in body
    feat = body["merged_feature"]
    assert feat["type"] == "Feature"
    assert "ulpin" in feat["properties"]
    assert feat["properties"]["area"] > 0


# ---------------------------------------------------------------------------
# 4. Parcel Split Endpoint (/harmonized/split)
# ---------------------------------------------------------------------------

def test_harmonized_parcel_split():
    payload = {
        "parcel_id": "P-102",
        "split_parts": 2,
        "direction": "horizontal"
    }
    r = client.post("/harmonized/split", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "split"
    assert len(body["sub_parcels"]) == 2
    p1 = body["sub_parcels"][0]
    p2 = body["sub_parcels"][1]
    assert "id" in p1
    assert "id" in p2
    assert p1["properties"]["area"] > 0
    assert p2["properties"]["area"] > 0


# ---------------------------------------------------------------------------
# 5. Bulk Auto-Match Endpoint (/harmonized/auto-match)
# ---------------------------------------------------------------------------

def test_harmonized_bulk_auto_match():
    r = client.post("/harmonized/auto-match?threshold=90")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["threshold"] == 90
    assert "auto_approved_count" in body


# ---------------------------------------------------------------------------
# 6. Review Canonical Statuses (APPROVED, REJECTED, FLAGGED)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("decision,expected_status", [
    ("APPROVED", "APPROVED"),
    ("accept", "APPROVED"),
    ("REJECTED", "REJECTED"),
    ("reject", "REJECTED"),
    ("FLAGGED", "FLAGGED"),
    ("edit", "FLAGGED"),
])
def test_review_decisions_canonical_states(decision, expected_status):
    r = client.post("/reviews/999", json={
        "reviewer": "Inspector Roy",
        "decision": decision,
        "comment": f"Audit test with {decision}"
    })
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "recorded"
    assert body["decision"] == expected_status


# ---------------------------------------------------------------------------
# 7. RoW Buffer Encroachment Analysis (/geoai/analysis/row-buffer)
# ---------------------------------------------------------------------------

def test_row_buffer_encroachment_analysis():
    payload = {
        "corridor_geojson": {
            "type": "LineString",
            "coordinates": [[77.2080, 28.6130], [77.2100, 28.6150]]
        },
        "parcels_geojson": [
            {
                "type": "Feature",
                "id": "ENC-P1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2085, 28.6135], [77.2095, 28.6135], [77.2095, 28.6145], [77.2085, 28.6145], [77.2085, 28.6135]]]
                },
                "properties": {"owner": "Encroacher 1"}
            },
            {
                "type": "Feature",
                "id": "FAR-P2",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.3000, 28.7000], [77.3010, 28.7000], [77.3010, 28.7010], [77.3000, 28.7010], [77.3000, 28.7000]]]
                },
                "properties": {"owner": "Clear Owner"}
            }
        ],
        "buffer_meters": 30.0
    }
    r = client.post("/geoai/analysis/row-buffer", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert "breaches" in body
    assert len(body["breaches"]) >= 1
    b = body["breaches"][0]
    assert "breach_area_sqm" in b
    assert b["breach_area_sqm"] > 0
    assert body["breach_features"]["type"] == "FeatureCollection"


# ---------------------------------------------------------------------------
# 8. Analytics Summary, Heatmap & Multi-format Exports
# ---------------------------------------------------------------------------

def test_analytics_summary():
    r = client.get("/analytics/summary")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "breakdowns" in data
    assert "quality_indices" in data
    assert "total_datasets" in data["summary"]
    assert "total_matches" in data["summary"]


def test_discrepancy_heatmap():
    r = client.get("/analytics/discrepancy-heatmap")
    assert r.status_code == 200
    fc = r.json()
    assert fc["type"] == "FeatureCollection"
    assert "features" in fc


def test_analytics_exports():
    # 1. GeoJSON export
    r_geo = client.get("/analytics/export/geojson")
    assert r_geo.status_code == 200
    assert "json" in r_geo.headers["content-type"]
    geo_body = r_geo.json()
    assert geo_body["type"] == "FeatureCollection"

    # 2. CSV export
    r_csv = client.get("/analytics/export/csv")
    assert r_csv.status_code == 200
    assert "text/csv" in r_csv.headers["content-type"]
    assert "Parcel ID" in r_csv.text

