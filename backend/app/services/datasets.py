import json
import os
import shutil

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.engines.gis import (
    IngestError,
    ingest_dataset,
    repair_dataset,
    validate_dataset,
)
from app.models.dataset import Dataset

# Relative to cwd (backend/), per the db path convention
UPLOAD_DIR = "uploads"
STANDARDIZED_DIR = os.path.join(UPLOAD_DIR, "standardized")


def create_dataset(file: UploadFile, db: Session) -> Dataset:
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    save_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # source_id left unset (null) — no Source-creation flow yet, confirmed
    new_dataset = Dataset(file_path=save_path, status="uploaded")
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)

    return new_dataset


def validate_dataset_geometry(dataset_id: int, db: Session) -> dict:
    """Run per-feature geometry validation on a dataset.

    Thin wrapper around engines/gis.validate_dataset. The engine owns the
    per-feature loop and the CRS/empty/invalid checks; this function only
    loads the dataset row, persists the engine's verdict onto the row, and
    returns the engine result in M3's existing response shape.

    Side effects (unchanged from M3's original):
      * Sets Dataset.crs (may be None if engine reported CRS_MISSING)
      * Sets Dataset.feature_count
      * Sets Dataset.status = "validated" or "invalid"
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if dataset is None:
        return None

    result = validate_dataset(dataset.file_path)

    dataset.crs = result.crs
    dataset.feature_count = result.feature_count
    dataset.status = "validated" if result.valid else "invalid"
    db.commit()

    return {"valid": result.valid, "issues": result.issues}


def standardize_dataset(dataset_id: int, db: Session) -> dict:
    """CRS-normalize a dataset and compute its coverage boundary.

    Delegates the actual transformation to engines/gis.ingestion so the engine
    stays storage-agnostic (per backend/app/db/README.md). This function is
    the only place that touches the ORM in response to ingestion.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if dataset is None:
        return None

    try:
        result = ingest_dataset(dataset.file_path)
    except IngestError as exc:
        # Engine-level failure (missing CRS, unreadable file). Surface as
        # a structured error so the API layer can translate to 422.
        return {"_error": "ingest_failed", "detail": str(exc)}

    dataset.crs = result.crs
    dataset.feature_count = result.feature_count
    dataset.coverage_boundary_geojson = json.dumps(result.coverage_geojson)
    dataset.status = "standardized"
    db.commit()

    return {
        "dataset_id": dataset_id,
        "status": dataset.status,
        "crs": result.crs,
        "feature_count": result.feature_count,
    }


def repair_dataset_service(dataset_id: int, db: Session) -> dict:
    """Repair invalid geometries in a dataset and persist the cleaned GDF.

    The engine (engines/gis.repair_dataset) is storage-agnostic — it
    returns a RepairResult containing the cleaned GeoDataFrame. This
    service function handles the I/O wiring: writing the cleaned GDF
    to uploads/standardized/{id}.geojson and persisting the verdict
    on the dataset row.

    The cleaned file's path is derivable from `dataset_id`, so we don't
    add a new schema column in this PR — M6 may add `standardized_path`
    later. (See PR #11's open items.)

    Returns None when the dataset id is unknown.
    Returns a dict with `_error` set when the engine rejects the file.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if dataset is None:
        return None

    result = repair_dataset(dataset.file_path)

    # File-level failures (CRS missing, unreadable): no GDF, no I/O.
    # Detect via the absence of a usable CRS in the result.
    if result.crs is None and result.feature_count == 0 and result.dropped_count == 0:
        first = result.issues[0] if result.issues else {}
        return {"_error": first.get("code", "ingest_failed"), "detail": first.get("reason", "")}

    # Persist the cleaned GDF to disk. The path is deterministic so a
    # re-run of /repair overwrites cleanly.
    os.makedirs(STANDARDIZED_DIR, exist_ok=True)
    standardized_path = os.path.join(STANDARDIZED_DIR, f"{dataset_id}.geojson")
    if not result.gdf.empty:
        result.gdf.to_file(standardized_path, driver="GeoJSON")
    else:
        # All features dropped — still write an empty FeatureCollection so
        # downstream readers don't have to special-case a missing file.
        empty = result.gdf.copy()  # empty GeoDataFrame with the same CRS (None)
        empty.to_file(standardized_path, driver="GeoJSON")

    dataset.crs = result.crs
    dataset.feature_count = result.feature_count
    dataset.status = "repaired"
    db.commit()

    return {
        "dataset_id": dataset_id,
        "status": dataset.status,
        "crs": result.crs,
        "feature_count": result.feature_count,
        "dropped_count": result.dropped_count,
        "repaired_count": len(result.repaired_indices),
        "repaired_indices": result.repaired_indices,
        "standardized_path": standardized_path,
        "issues": result.issues,
    }
