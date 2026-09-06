"""
Unit tests for engines/gis/validation.py.

Storage-agnostic: no DB, no FastAPI. Just the engine.
Run from backend/ directory: pytest tests/test_gis_validation.py -v
"""

import os
from pathlib import Path

import geopandas as gpd
import pytest

from app.engines.gis import IssueCode, ValidationResult, validate_dataset

FIXTURES = Path(__file__).parent / "fixtures"


def test_validate_clean_dataset():
    """The clean sample fixture must validate with no issues."""
    result = validate_dataset(str(FIXTURES / "sample.geojson"))

    assert isinstance(result, ValidationResult)
    assert result.valid is True
    assert result.issues == []
    assert result.crs == "EPSG:4326"
    assert result.feature_count == 3


def test_validate_detects_empty_geometry():
    """A feature with empty coordinates must be reported as EMPTY_GEOMETRY."""
    result = validate_dataset(str(FIXTURES / "empty_geom.geojson"))

    assert result.valid is False
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue["code"] == IssueCode.EMPTY_GEOMETRY
    assert issue["feature_index"] == 0
    assert "Empty geometry" in issue["reason"]


def test_validate_detects_self_intersection():
    """A bowtie polygon (self-intersecting) must be reported as INVALID_GEOMETRY."""
    result = validate_dataset(str(FIXTURES / "self_intersect.geojson"))

    assert result.valid is False
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue["code"] == IssueCode.INVALID_GEOMETRY
    assert issue["feature_index"] == 0
    assert "self-intersection" in issue["reason"].lower()


def test_validate_reports_missing_crs():
    """A file geopandas reads as CRS=None must be reported as CRS_MISSING.

    Skipped on geopandas versions that auto-default GeoJSON to EPSG:4326
    per RFC 7946 — those can't reproduce the no-CRS precondition.
    """
    import json
    import tempfile

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

    # Verify the precondition: the file must read as CRS=None
    read_back = gpd.read_file(path)
    if read_back.crs is not None:
        os.unlink(path)
        pytest.skip(
            f"Local geopandas {gpd.__version__} defaults GeoJSON CRS to "
            f"{read_back.crs}; cannot exercise the missing-CRS path on this machine."
        )

    try:
        result = validate_dataset(path)
    finally:
        os.unlink(path)

    assert result.valid is False
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue["code"] == IssueCode.CRS_MISSING
    assert issue["feature_index"] is None  # whole-file, not per-feature
    assert result.crs is None
    assert "CRS missing" in issue["reason"]


def test_validate_unreadable_file():
    """A nonexistent path must be reported as FILE_UNREADABLE, not raise."""
    result = validate_dataset("/tmp/does-not-exist-bhudrishti-xyz.geojson")

    assert result.valid is False
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue["code"] == IssueCode.FILE_UNREADABLE
    assert issue["feature_index"] is None


def test_validate_does_not_mutate_source():
    """Hard rule (playbook Section 10): the original upload must be untouched."""
    import hashlib

    path = str(FIXTURES / "sample.geojson")
    with open(path, "rb") as f:
        before = hashlib.sha256(f.read()).hexdigest()
    mtime_before = os.path.getmtime(path)

    validate_dataset(path)

    with open(path, "rb") as f:
        after = hashlib.sha256(f.read()).hexdigest()
    mtime_after = os.path.getmtime(path)

    assert before == after, "validate_dataset mutated the source file bytes"
    assert mtime_before == mtime_after, "validate_dataset modified source file mtime"


def test_validate_multiple_issues_one_pass():
    """A file with two distinct problems must surface both issues, with the
    correct codes and feature_index values, and report valid=False."""
    import json
    import tempfile

    payload = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": [
            {
                "type": "Feature",
                "properties": {"feature_id": "OK"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [77.0, 28.0], [77.01, 28.0], [77.01, 28.01], [77.0, 28.01], [77.0, 28.0]
                    ]],
                },
            },
            {
                "type": "Feature",
                "properties": {"feature_id": "BAD1"},
                "geometry": {"type": "Polygon", "coordinates": [[]]},
            },
            {
                "type": "Feature",
                "properties": {"feature_id": "BAD2"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0.0, 0.0], [2.0, 2.0], [2.0, 0.0], [0.0, 2.0], [0.0, 0.0]
                    ]],
                },
            },
        ],
    }
    fd, path = tempfile.mkstemp(suffix=".geojson")
    os.close(fd)
    with open(path, "w") as f:
        json.dump(payload, f)

    try:
        result = validate_dataset(path)
    finally:
        os.unlink(path)

    assert result.valid is False
    assert len(result.issues) == 2
    by_index = {i["feature_index"]: i["code"] for i in result.issues}
    assert by_index[1] == IssueCode.EMPTY_GEOMETRY
    assert by_index[2] == IssueCode.INVALID_GEOMETRY
