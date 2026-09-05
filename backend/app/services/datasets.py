import os
import shutil

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.dataset import Dataset

# Relative to cwd (backend/), per your db path convention
UPLOAD_DIR = "uploads"


def create_dataset(file: UploadFile, db: Session) -> Dataset:
    # Make sure the folder exists (won't error if it already does)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    save_path = os.path.join(UPLOAD_DIR, file.filename)

    # Copy the uploaded file's contents to disk
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # source_id left unset (null) — no Source-creation flow yet, confirmed
    new_dataset = Dataset(file_path=save_path, status="uploaded")
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)  # so new_dataset.id is populated from the DB

    return new_dataset
