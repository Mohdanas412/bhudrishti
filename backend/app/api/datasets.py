from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.datasets import (
    create_dataset,
    standardize_dataset,
    validate_dataset_geometry,
)

router = APIRouter()


@router.post("")
async def upload_dataset(file: UploadFile, db: Session = Depends(get_db)):
    """Upload + register a dataset (GeoJSON/Shapefile/CSV). Owner: M3 + M4."""
    dataset = create_dataset(file, db)
    return {"id": dataset.id, "filename": file.filename, "status": dataset.status}


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
async def standardize_dataset_route(
    dataset_id: int, db: Session = Depends(get_db)
):
    """CRS-normalize a dataset and compute its coverage boundary.

    Delegates to engines/gis.ingestion (M4). Returns 422 if the engine
    rejects the file (e.g. CRS missing), 404 if the dataset id is unknown.
    """
    result = standardize_dataset(dataset_id, db)

    if result is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if result.get("_error") == "ingest_failed":
        raise HTTPException(status_code=422, detail=result["detail"])

    return result
