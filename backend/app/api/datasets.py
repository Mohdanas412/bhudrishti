from fastapi import APIRouter, UploadFile

router = APIRouter()


@router.post("")
async def upload_dataset(file: UploadFile):
    """Upload + register a dataset (GeoJSON/Shapefile/CSV). Owner: M3 + M4."""
    return {"id": "mock-dataset-1", "filename": file.filename, "status": "registered"}


@router.post("/{dataset_id}/validate")
async def validate_dataset(dataset_id: str):
    """Run CRS + geometry checks. Delegates to engines/gis. Owner: M4."""
    return {"dataset_id": dataset_id, "valid": True, "issues": []}


@router.post("/{dataset_id}/standardize")
async def standardize_dataset(dataset_id: str):
    """Schema/CRS normalization. Delegates to engines/gis. Owner: M4."""
    return {"dataset_id": dataset_id, "status": "standardized"}
