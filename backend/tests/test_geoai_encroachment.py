"""
Tests for GeoAI Spatial Encroachment & Drone Change Detection Engine.
"""

import geopandas as gpd
import pytest
from app.engines.gis.encroachment import detect_encroachments
from app.main import app
from fastapi.testclient import TestClient
from shapely.geometry import Polygon


@pytest.fixture
def client():
    return TestClient(app)

def test_encroachment_detection():
    # Cadastral parcel (10x10)
    cadastral_poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    cadastral_gdf = gpd.GeoDataFrame(
        [{"id": "P-1", "geometry": cadastral_poly}],
        geometry="geometry"
    )

    # Drone footprint (encroaching by extending to x=12)
    drone_poly = Polygon([(0, 0), (12, 0), (12, 10), (0, 10), (0, 0)])
    drone_gdf = gpd.GeoDataFrame(
        [{"id": "D-1", "geometry": drone_poly}],
        geometry="geometry"
    )

    # Run detection with standard tolerance
    report = detect_encroachments(cadastral_gdf, drone_gdf, permissible_variance_sqm=5.0)

    assert len(report.metrics) == 1
    metric = report.metrics[0]
    assert metric.encroachment_area_sqm > 0
    assert metric.status in ["permissible", "flagged"]

def test_encroachment_api(client):
    cadastral_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "P-101",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2085, 28.6135], [77.2095, 28.6135], [77.2095, 28.6142], [77.2085, 28.6142], [77.2085, 28.6135]]]
                },
                "properties": {"parcel_id": "P-101"}
            }
        ]
    }

    drone_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "DRONE-01",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2085, 28.6135], [77.2097, 28.6135], [77.2097, 28.6142], [77.2085, 28.6142], [77.2085, 28.6135]]]
                },
                "properties": {"footprint_id": "DRONE-01"}
            }
        ]
    }

    res = client.post(
        "/geoai/analysis/encroachment",
        json={
            "cadastral_geojson": cadastral_geojson,
            "drone_geojson": drone_geojson,
            "permissible_variance_sqm": 5.0
        }
    )

    assert res.status_code == 200
    data = res.json()
    assert "metrics" in data
    assert "total_encroachments" in data
