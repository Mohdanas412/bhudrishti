from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.datasets import (
    create_dataset,
    standardize_dataset_fields,
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
    """Schema/CRS normalization. Delegates to engines/gis. Owner: M4."""
    result = standardize_dataset_fields(dataset_id, db)

    if result is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    return {
        "dataset_id": dataset_id,
        "status": "standardized",
        "features_created": result.get("features_created"),
        "unmapped_fields": result.get("unmapped_fields"),
    }
