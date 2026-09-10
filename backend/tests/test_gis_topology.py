"""
Tests for GIS Topology Engine & Vertex Snapping.

Tests:
  - Intra-layer and multi-layer vertex snapping with tolerance thresholds.
  - Overlap detection and automated resolution / boundary clipping.
  - Gap / vacant sliver hole detection and absorption.
  - Topology Health Report generation (metrics, counts, health scores).
  - API endpoint verification (/datasets/{id}/topology/correct, /datasets/{id}/topology/health, /harmonized/topology/correct).
"""

import geopandas as gpd
import pytest
from app.engines.gis.topology import (
    TopologyHealthReport,
    correct_topology,
    detect_overlaps,
    resolve_overlaps,
    snap_geometry_to_reference,
    snap_layers,
)
from app.main import app
from fastapi.testclient import TestClient
from shapely.geometry import Polygon


@pytest.fixture
def client():
    return TestClient(app)


def test_snap_geometry_to_reference():
    # Target polygon with vertex slightly offset (e.g. 77.209501 vs 77.209500)
    target = Polygon([(77.2085, 28.6135), (77.209501, 28.6135), (77.209501, 28.6142), (77.2085, 28.6142), (77.2085, 28.6135)])
    reference = Polygon([(77.2095, 28.6135), (77.2108, 28.6135), (77.2108, 28.6144), (77.2095, 28.6144), (77.2095, 28.6135)])

    snapped, count = snap_geometry_to_reference(target, reference, tolerance=0.0001)
    assert count >= 1
    # Check that coordinate aligned closely with 77.2095
    coords = list(snapped.exterior.coords)
    assert any(abs(x - 77.2095) < 1e-6 for x, y in coords)


def test_detect_and_resolve_overlaps():
    # Two polygons in sample geographic coordinates that slightly overlap along their shared boundary
    p1 = Polygon([(77.2085, 28.6135), (77.2095, 28.6135), (77.2095, 28.6142), (77.2085, 28.6142), (77.2085, 28.6135)])
    # Overlaps p1 by 0.0001 deg along x
    p2 = Polygon([(77.2094, 28.6135), (77.2108, 28.6135), (77.2108, 28.6142), (77.2094, 28.6142), (77.2094, 28.6135)])

    gdf = gpd.GeoDataFrame([
        {"feature_id": "P-1", "geometry": p1},
        {"feature_id": "P-2", "geometry": p2},
    ], crs="EPSG:4326")

    overlaps = detect_overlaps(gdf, min_overlap_sqm=0.01)
    assert len(overlaps) == 1
    assert overlaps[0]["feature_a"] == "P-1"
    assert overlaps[0]["feature_b"] == "P-2"

    resolved_gdf, fixes, resolved_count = resolve_overlaps(gdf, max_overlap_area_sqm=5000.0)
    assert resolved_count == 1
    assert len(fixes) == 1
    # Now they should not overlap with area > 0
    new_overlaps = detect_overlaps(resolved_gdf, min_overlap_sqm=0.01)
    assert len(new_overlaps) == 0


def test_detect_and_resolve_gaps():
    # Four parcels arranged in a 2x2 grid surrounding a tiny 0.0001 square gap
    # Ring around a central micro-hole
    p1 = Polygon([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)])
    p2 = Polygon([(1.0001, 0.0), (2.0, 0.0), (2.0, 1.0), (1.0001, 1.0), (1.0001, 0.0)])
    p3 = Polygon([(0.0, 1.0), (1.0, 1.0), (1.0, 2.0), (0.0, 2.0), (0.0, 1.0)])
    p4 = Polygon([(1.0001, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0001, 2.0), (1.0001, 1.0)])

    gdf = gpd.GeoDataFrame([
        {"feature_id": "P-1", "geometry": p1},
        {"feature_id": "P-2", "geometry": p2},
        {"feature_id": "P-3", "geometry": p3},
        {"feature_id": "P-4", "geometry": p4},
    ], crs="EPSG:4326")

    # Correct topology with snap + gap filling
    corrected_gdf, report = correct_topology(
        gdf, tolerance=0.0002, max_gap_area_sqm=500.0, auto_fill_gaps=True, auto_merge_overlaps=True
    )
    assert isinstance(report, TopologyHealthReport)
    assert report.summary.total_features == 4
    assert report.summary.final_health_score >= report.summary.initial_health_score


def test_multi_layer_snap():
    # Target dataset (Cadastral) and Reference dataset (Survey Drone)
    target = gpd.GeoDataFrame([
        {"feature_id": "CAD-1", "geometry": Polygon([(77.2085, 28.6135), (77.20951, 28.6135), (77.20951, 28.6142), (77.2085, 28.6142), (77.2085, 28.6135)])},
    ], crs="EPSG:4326")

    ref = gpd.GeoDataFrame([
        {"feature_id": "DRONE-1", "geometry": Polygon([(77.20950, 28.6135), (77.2108, 28.6135), (77.2108, 28.6144), (77.20950, 28.6144), (77.20950, 28.6135)])},
    ], crs="EPSG:4326")

    snapped_gdf, fixes = snap_layers(target, reference_gdf=ref, tolerance=0.00005)
    assert len(fixes) >= 1
    assert fixes[0].fix_type == "snap"


def test_topology_api_endpoints(client):
    # 1. Seed sample project to have test datasets
    res_seed = client.post("/datasets/sample-seed")
    assert res_seed.status_code == 200
    seed_data = res_seed.json()
    dataset_ids = seed_data.get("dataset_ids", [])
    assert len(dataset_ids) >= 1

    ds_id = dataset_ids[0]

    # 2. Test GET topology health
    res_health = client.get(f"/datasets/{ds_id}/topology/health")
    assert res_health.status_code == 200
    health_body = res_health.json()
    assert "health_report" in health_body
    assert "summary" in health_body["health_report"]
    assert "final_health_score" in health_body["health_report"]["summary"]

    # 3. Test POST topology correct
    res_correct = client.post(f"/datasets/{ds_id}/topology/correct?tolerance=0.0001&auto_merge_overlaps=true&auto_fill_gaps=true")
    assert res_correct.status_code == 200
    correct_body = res_correct.json()
    assert correct_body["status"] == "topology_corrected"
    assert "health_report" in correct_body
    assert "fixes" in correct_body["health_report"]

    # 4. Test POST harmonized topology correct
    res_harm_top = client.post("/harmonized/topology/correct?tolerance=0.0001")
    assert res_harm_top.status_code == 200
    harm_body = res_harm_top.json()
    assert "type" in harm_body and harm_body["type"] == "FeatureCollection"
    assert "metadata" in harm_body
    assert "topology_health" in harm_body["metadata"]
