"""
Unit tests for engines/gis/ingestion.py.

Storage-agnostic: no DB, no FastAPI. Just the engine.
Run from backend/ directory: pytest tests/test_gis_ingestion.py -v
"""

import os
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from app.engines.gis import IngestError, IngestResult, ingest_dataset
from app.engines.gis.ingestion import TARGET_CRS

FIXTURES = Path(__file__).parent / "fixtures"


def _write_tmp_gdf(gdf, suffix):
    """Helper: write a GeoDataFrame to a tmp path and return it."""
    import tempfile

    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    gdf.to_file(path, driver="GeoJSON")
    return path


def test_ingest_geojson_wgs84_passthrough():
    """Input already in EPSG:4326 — CRS stays, coverage is computed."""
    path = str(FIXTURES / "sample.geojson")

    result = ingest_dataset(path)

    assert isinstance(result, IngestResult)
    assert result.crs == TARGET_CRS
    assert result.feature_count == 3
    assert result.gdf.crs.to_string() == TARGET_CRS
    assert result.coverage_geojson["type"] in ("Polygon", "MultiPolygon")
    assert "coordinates" in result.coverage_geojson


def test_ingest_geojson_utm_reprojects():
    """Input in UTM 43N (EPSG:32643) — output must be reprojected to 4326."""
    poly = Polygon(
        [
            (700000, 3160000),
            (700100, 3160000),
            (700100, 3160100),
            (700000, 3160100),
            (700000, 3160000),
        ]
    )
    gdf = gpd.GeoDataFrame({"feature_id": ["UTM1"]}, geometry=[poly], crs="EPSG:32643")

    path = _write_tmp_gdf(gdf, ".geojson")
    try:
        result = ingest_dataset(path)
    finally:
        os.unlink(path)

    assert result.crs == TARGET_CRS
    assert result.feature_count == 1
    # Lon should be in [-180, 180], lat in [-90, 90] after reprojection
    bounds = result.gdf.total_bounds
    assert -180 <= bounds[0] <= 180 and -180 <= bounds[2] <= 180
    assert -90 <= bounds[1] <= 90 and -90 <= bounds[3] <= 90


def test_ingest_missing_crs_raises():
    """A file geopandas reads as CRS=None must raise IngestError.

    Modern GeoJSON (RFC 7946) defaults to WGS84, so the GeoJSON-no-crs case
    is no longer a reliable trigger. We construct a GeoDataFrame without
    setting crs and write it out, which gives gdf.crs = None on read.
    """
    import json
    import tempfile

    # Build a minimal valid GeoJSON file by hand with no CRS hint.
    # We bypass geopandas for the write to guarantee gdf.crs is None on read.
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"feature_id": "X1"},
                "geometry": {"type": "Point", "coordinates": [77.0, 28.0]},
            }
        ],
    }
    fd, path = tempfile.mkstemp(suffix=".geojson")
    os.close(fd)
    with open(path, "w") as f:
        json.dump(payload, f)

    # Confirm our test premise: the file is read as CRS=None
    import geopandas as _gpd

    read_back = _gpd.read_file(path)
    if read_back.crs is not None:
        pytest.skip(
            f"Local geopandas {_gpd.__version__} defaults GeoJSON CRS to "
            f"{read_back.crs}; cannot exercise the missing-CRS path on this machine."
        )

    try:
        with pytest.raises(IngestError) as excinfo:
            ingest_dataset(path)
        assert "CRS missing" in str(excinfo.value)
    finally:
        os.unlink(path)


def test_ingest_computes_coverage_polygon():
    """Three disjoint polygons produce a (Multi)Polygon coverage GeoJSON."""
    polys = [
        Polygon([(77.0, 28.0), (77.01, 28.0), (77.01, 28.01), (77.0, 28.01)]),
        Polygon([(77.1, 28.1), (77.11, 28.1), (77.11, 28.11), (77.1, 28.11)]),
        Polygon([(77.2, 28.2), (77.21, 28.2), (77.21, 28.21), (77.2, 28.21)]),
    ]
    gdf = gpd.GeoDataFrame(
        {"feature_id": ["A", "B", "C"]}, geometry=polys, crs="EPSG:4326"
    )
    path = _write_tmp_gdf(gdf, ".geojson")
    try:
        result = ingest_dataset(path)
    finally:
        os.unlink(path)

    assert result.coverage_geojson["type"] in ("Polygon", "MultiPolygon")
    # GeoJSON-serializable (no shapely objects leaking out)
    import json

    json.dumps(result.coverage_geojson)  # would raise TypeError if not serializable


def test_ingest_does_not_mutate_source_file():
    """Hard rule (playbook Section 10): the original upload must be untouched."""
    import hashlib

    path = str(FIXTURES / "sample.geojson")
    with open(path, "rb") as f:
        before = hashlib.sha256(f.read()).hexdigest()
    mtime_before = os.path.getmtime(path)

    result = ingest_dataset(path)

    with open(path, "rb") as f:
        after = hashlib.sha256(f.read()).hexdigest()
    mtime_after = os.path.getmtime(path)

    assert before == after, "ingest_dataset mutated the source file bytes"
    assert mtime_before == mtime_after, "ingest_dataset modified source file mtime"
    # Sanity: the result still references the engine output, not the file
    assert len(result.gdf) == 3


def test_ingest_nonexistent_file_raises():
    with pytest.raises(IngestError) as excinfo:
        ingest_dataset("/tmp/does-not-exist-bhudrishti-xyz.geojson")
    assert "Failed to read" in str(excinfo.value)
