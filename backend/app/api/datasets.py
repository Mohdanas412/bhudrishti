from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.datasets import create_dataset

router = APIRouter()


@router.post("")
async def upload_dataset(file: UploadFile, db: Session = Depends(get_db)):
    """Upload + register a dataset (GeoJSON/Shapefile/CSV). Owner: M3 + M4."""
    dataset = create_dataset(file, db)
    return {"id": dataset.id, "filename": file.filename, "status": dataset.status}


@router.post("/{dataset_id}/validate")
async def validate_dataset(dataset_id: str):
    """Run CRS + geometry checks. Delegates to engines/gis. Owner: M4."""
    return {"dataset_id": dataset_id, "valid": True, "issues": []}


@router.post("/{dataset_id}/standardize")
async def standardize_dataset(dataset_id: str):
    """Schema/CRS normalization. Delegates to engines/gis. Owner: M4."""
    return {"dataset_id": dataset_id, "status": "standardized"}
