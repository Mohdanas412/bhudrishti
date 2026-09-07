"""
Unit tests for engines/gis/validation.repair_dataset().

Storage-agnostic: no DB, no FastAPI. Just the engine.
Run from backend/ directory: pytest tests/test_gis_repair.py -v
"""

import os
from pathlib import Path

from app.engines.gis import IssueCode, RepairResult, repair_dataset
from shapely.validation import make_valid

FIXTURES = Path(__file__).parent / "fixtures"


def test_repair_clean_dataset():
    """A clean input returns a GDF equal in shape to the input, no drops, no issues."""
    result = repair_dataset(str(FIXTURES / "sample.geojson"))

    assert isinstance(result, RepairResult)
    assert result.crs == "EPSG:4326"
    assert result.feature_count == 3
    assert result.dropped_count == 0
    assert result.repaired_indices == []
    assert result.issues == []
    # All features in the cleaned GDF are still valid
    assert all(result.gdf.geometry.is_valid)
    assert all(not g.is_empty for g in result.gdf.geometry)


def test_repair_fixes_self_intersection():
    """A bowtie polygon gets repaired in place via shapely.make_valid.

    The repaired geometry is valid (Shapely splits the bowtie into two
    triangles, which is a MultiPolygon of valid parts).
    """
    result = repair_dataset(str(FIXTURES / "self_intersect.geojson"))

    assert result.crs == "EPSG:4326"
    assert result.feature_count == 1
    assert result.dropped_count == 0
    assert result.repaired_indices == [0]
    assert result.issues == []
    # The repaired geometry is now valid
    assert result.gdf.geometry.iloc[0].is_valid
    # Sanity: make_valid of a bowtie yields a MultiPolygon (two triangles)
    assert result.gdf.geometry.iloc[0].geom_type == "MultiPolygon"


def test_repair_drops_empty_geometry():
    """A feature with empty coordinates gets dropped with an UNREPAIRABLE_GEOMETRY issue."""
    result = repair_dataset(str(FIXTURES / "empty_geom.geojson"))

    # The empty_geom fixture has 1 empty + 1 valid feature, so 1 survives.
    assert result.feature_count == 1
    assert result.dropped_count == 1
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue["code"] == IssueCode.UNREPAIRABLE_GEOMETRY
    assert issue["feature_index"] == 0
    assert "Empty geometry" in issue["reason"]


def test_repair_keeps_valid_drops_invalid():
    """Two features: one bowtie, one valid. Repair fixes the bowtie, keeps both."""
    result = repair_dataset(str(FIXTURES / "self_intersect_multi.geojson"))

    # Both features survive (bowtie is fixed in place).
    assert result.feature_count == 2
    assert result.dropped_count == 0
    assert result.repaired_indices == [0]  # the bowtie was at index 0
    assert result.issues == []
    # Both geoms in the result are now valid
    assert all(result.gdf.geometry.is_valid)


def test_repair_unreadable_file():
    """A nonexistent path returns a RepairResult with FILE_UNREADABLE and empty gdf."""
    result = repair_dataset("/tmp/does-not-exist-bhudrishti-xyz.geojson")

    assert result.feature_count == 0
    assert result.dropped_count == 0
    assert result.gdf.empty
    assert len(result.issues) == 1
    assert result.issues[0]["code"] == IssueCode.FILE_UNREADABLE
    assert result.issues[0]["feature_index"] is None


def test_repair_does_not_mutate_source():
    """Hard rule (playbook Section 10): the original upload must be untouched."""
    import hashlib

    path = str(FIXTURES / "self_intersect.geojson")
    with open(path, "rb") as f:
        before = hashlib.sha256(f.read()).hexdigest()
    mtime_before = os.path.getmtime(path)

    repair_dataset(path)

    with open(path, "rb") as f:
        after = hashlib.sha256(f.read()).hexdigest()
    mtime_after = os.path.getmtime(path)

    assert before == after, "repair_dataset mutated the source file bytes"
    assert mtime_before == mtime_after, "repair_dataset modified source file mtime"


def test_repair_make_valid_used_for_fix():
    """Sanity check: the repaired geometry is the same as what shapely.make_valid
    produces on the same input. Confirms we're using make_valid and not e.g. buffer(0)."""
    from shapely.geometry import Polygon

    bowtie = Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])
    expected = make_valid(bowtie)
    assert expected.is_valid
    # Whatever shape make_valid produces, the engine must match
    result = repair_dataset(str(FIXTURES / "self_intersect.geojson"))
    actual = result.gdf.geometry.iloc[0]
    assert actual.equals(expected)
