"""
Smoke tests for the datasets endpoints.

Covers POST /datasets/{id}/validate and POST /datasets/{id}/standardize —
both wire through to engines/gis.

Run from backend/ directory: pytest tests/test_standardize_endpoint.py -v
"""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import SessionLocal
from app.main import app
from app.models.dataset import Dataset

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_GEOJSON = FIXTURES / "sample.geojson"

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_db(tmp_path, monkeypatch):
    """Each test gets a fresh SQLite DB and a clean uploads/ folder."""
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(
        "app.db.session.engine",
        __import__("sqlalchemy").create_engine(
            f"sqlite:///{test_db}", connect_args={"check_same_thread": False}
        ),
    )
    # Rebuild the sessionmaker against the new engine
    from app.db import session as session_mod

    session_mod.SessionLocal.configure(bind=session_mod.engine)
    Base.metadata.drop_all(bind=session_mod.engine)
    Base.metadata.create_all(bind=session_mod.engine)

    # Make sure uploads/ starts clean so we can assert on the file later
    uploads = Path("uploads")
    if uploads.exists():
        shutil.rmtree(uploads)
    uploads.mkdir()

    yield

    if uploads.exists():
        shutil.rmtree(uploads)


def _create_dataset_row(filename: str, file_path: str) -> int:
    """Insert a Dataset row directly so we don't have to round-trip the upload endpoint."""
    db = SessionLocal()
    try:
        ds = Dataset(file_path=file_path, status="uploaded")
        db.add(ds)
        db.commit()
        db.refresh(ds)
        return ds.id
    finally:
        db.close()


def test_standardize_happy_path():
    # Copy the fixture into uploads/ (as the upload endpoint would)
    target = Path("uploads") / "sample.geojson"
    shutil.copy(SAMPLE_GEOJSON, target)

    dataset_id = _create_dataset_row("sample.geojson", str(target))

    r = client.post(f"/datasets/{dataset_id}/standardize")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "standardized"
    assert body["crs"] == "EPSG:4326"
    assert body["feature_count"] == 3
    assert body["dataset_id"] == dataset_id


def test_standardize_404_for_missing_dataset():
    r = client.post("/datasets/99999/standardize")
    assert r.status_code == 404
    assert r.json()["detail"] == "Dataset not found"


def test_standardize_422_for_missing_crs(tmp_path):
    """A dataset that geopandas reads as CRS=None must yield 422, not 500.

    Skipped on geopandas versions that auto-default GeoJSON to EPSG:4326
    per RFC 7946 — those can't reproduce the no-CRS precondition.
    """
    import json

    import geopandas as _gpd

    bad = Path("uploads") / "no_crs.geojson"
    bad.parent.mkdir(exist_ok=True)
    bad.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {"type": "Point", "coordinates": [0, 0]},
                    }
                ],
            }
        )
    )

    # Verify precondition: this file must actually be read as CRS=None
    read_back = _gpd.read_file(str(bad))
    if read_back.crs is not None:
        pytest.skip(
            f"Local geopandas {_gpd.__version__} defaults GeoJSON CRS to "
            f"{read_back.crs}; cannot exercise the missing-CRS path here."
        )

    dataset_id = _create_dataset_row("no_crs.geojson", str(bad))

    r = client.post(f"/datasets/{dataset_id}/standardize")
    assert r.status_code == 422
    assert "CRS missing" in r.json()["detail"]


# ---------------------------------------------------------------------------
# /validate endpoint tests (Stage 2 — M4 validation engine)
# ---------------------------------------------------------------------------


def test_validate_happy_path():
    """A clean dataset must validate as valid=True, with no issues, and
    persist crs/feature_count/status='validated' on the dataset row."""
    target = Path("uploads") / "sample.geojson"
    shutil.copy(SAMPLE_GEOJSON, target)
    dataset_id = _create_dataset_row("sample.geojson", str(target))

    r = client.post(f"/datasets/{dataset_id}/validate")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["valid"] is True
    assert body["issues"] == []

    # Side effect: status on the row is "validated"
    db = SessionLocal()
    try:
        ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        assert ds.status == "validated"
        assert ds.crs == "EPSG:4326"
        assert ds.feature_count == 3
    finally:
        db.close()


def test_validate_detects_empty_geometry():
    """An empty-geom fixture must return valid=False with one EMPTY_GEOMETRY issue."""
    target = Path("uploads") / "empty_geom.geojson"
    shutil.copy(FIXTURES / "empty_geom.geojson", target)
    dataset_id = _create_dataset_row("empty_geom.geojson", str(target))

    r = client.post(f"/datasets/{dataset_id}/validate")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["valid"] is False
    assert len(body["issues"]) == 1
    assert body["issues"][0]["code"] == "empty_geometry"
    assert body["issues"][0]["feature_index"] == 0


def test_validate_404_for_missing_dataset():
    r = client.post("/datasets/99999/validate")
    assert r.status_code == 404
    assert r.json()["detail"] == "Dataset not found"
