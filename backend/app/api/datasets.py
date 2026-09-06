from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.datasets import (
    create_dataset,
    repair_dataset_service,
    standardize_dataset_fields,
    standardize_dataset_ingest,
    validate_dataset_geometry,
)

router = APIRouter()


class DatasetType(str, Enum):
    """Closed set of dataset types, per Addendum v1 Critical Fix 1 canonical schema."""

    CADASTRAL = "cadastral"
    MUNICIPAL = "municipal"
    BUILDING = "building"


@router.post("")
async def upload_dataset(
    file: UploadFile, dataset_type: DatasetType, db: Session = Depends(get_db)
):
    """Upload + register a dataset (GeoJSON/Shapefile/CSV). Owner: M3 + M4."""
    dataset = create_dataset(file, dataset_type.value, db)
    return {
        "id": dataset.id,
        "filename": file.filename,
        "status": dataset.status,
        "dataset_type": dataset.dataset_type,
    }


@router.post("/{dataset_id}/validate")
async def validate_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Run CRS + geometry checks. Delegates to engines/gis. Owner: M4."""
    result = validate_dataset_geometry(dataset_id, db)

    if result is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return {
        "dataset_id": dataset_id,
        "valid": result["valid"],
        "issues": result["issues"],
    }


@router.post("/{dataset_id}/standardize")
async def standardize_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """CRS-normalize, compute coverage boundary (M4), then map fields to
    canonical attributes and create Feature rows (M3). Owner: M3 + M4."""
    ingest_result = standardize_dataset_ingest(dataset_id, db)

    if ingest_result is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if "error" in ingest_result:
        raise HTTPException(status_code=422, detail=ingest_result["error"])

    fields_result = standardize_dataset_fields(dataset_id, db)

    if fields_result is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if "error" in fields_result:
        raise HTTPException(status_code=422, detail=fields_result["error"])

    return {
        "dataset_id": dataset_id,
        "status": "standardized",
        "crs": ingest_result["crs"],
        "feature_count": ingest_result["feature_count"],
        "features_created": fields_result.get("features_created"),
        "unmapped_fields": fields_result.get("unmapped_fields"),
    }


@router.post("/{dataset_id}/repair")
async def repair_dataset_route(dataset_id: int, db: Session = Depends(get_db)):
    """Repair invalid geometries in a dataset and persist the cleaned GDF.

    Delegates to engines/gis.repair_dataset (M4). Self-intersections are
    fixed in place via shapely.make_valid; empty or unrepairable geoms
    are dropped. The cleaned GeoDataFrame is written to
    uploads/standardized/{id}.geojson. Dataset.status is set to
    'repaired'. Returns 422 for engine-level failures, 404 for missing id.
    """
    result = repair_dataset_service(dataset_id, db)

    if result is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if result.get("_error") in ("ingest_failed", "crs_missing", "file_unreadable"):
        raise HTTPException(status_code=422, detail=result["detail"])

    return result
