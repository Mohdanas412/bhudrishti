import json
import os
import shutil

import geopandas as gpd
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.engines.gis import IngestError, ingest_dataset
from app.models.dataset import Dataset

# Relative to cwd (backend/), per the db path convention
UPLOAD_DIR = "uploads"


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
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if dataset is None:
        return None

    gdf = gpd.read_file(dataset.file_path)

    issues = []
    for idx, geom in enumerate(gdf.geometry):
        if geom is None or geom.is_empty:
            issues.append({"feature_index": idx, "reason": "Empty geometry"})
        elif not geom.is_valid:
            issues.append(
                {
                    "feature_index": idx,
                    "reason": "Invalid geometry (e.g. self-intersection)",
                }
            )

    is_valid = len(issues) == 0

    dataset.crs = str(gdf.crs)
    dataset.feature_count = len(gdf)
    dataset.status = "validated" if is_valid else "invalid"
    db.commit()

    return {"valid": is_valid, "issues": issues}


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
