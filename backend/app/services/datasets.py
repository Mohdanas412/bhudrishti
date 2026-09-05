import os
import shutil

import geopandas as gpd
from fastapi import UploadFile
from sqlalchemy.orm import Session

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
