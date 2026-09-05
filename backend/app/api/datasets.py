from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.datasets import create_dataset, validate_dataset_geometry

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
async def standardize_dataset(dataset_id: str):
    """Schema/CRS normalization. Delegates to engines/gis. Owner: M4."""
    return {"dataset_id": dataset_id, "status": "standardized"}
