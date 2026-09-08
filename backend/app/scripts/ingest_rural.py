import os

from app.db.session import SessionLocal
from app.models.dataset import Dataset
from app.models.source import Source
from app.services.datasets import (
    validate_dataset_geometry,
    standardize_dataset_ingest,
    standardize_dataset_fields,
)

def ingest_file(file_path: str, dataset_type: str, source_name: str, authority: str, rel_score: float):
    db = SessionLocal()
    try:
        src = db.query(Source).filter(Source.name == source_name).first()
        if not src:
            src = Source(name=source_name, authority=authority, reliability_score=rel_score)
            db.add(src)
            db.commit()
            db.refresh(src)
        
        ds = db.query(Dataset).filter(Dataset.file_path == file_path).first()
        if not ds:
            ds = Dataset(
                file_path=file_path,
                dataset_type=dataset_type,
                source_id=src.id,
                status="uploaded",
            )
            db.add(ds)
            db.commit()
            db.refresh(ds)
        
        print(f"Ingesting {os.path.basename(file_path)}...")
        validate_dataset_geometry(ds.id, db)
        standardize_dataset_ingest(ds.id, db)
        f_res = standardize_dataset_fields(ds.id, db)
        print(f"Created {f_res.get('features_created')} features.")
    finally:
        db.close()

if __name__ == "__main__":
    ingest_file(
        "/app/uploads/rural/punjab_cadastral.geojson",
        "cadastral",
        "Punjab Land Records Society (Cadastral)",
        "State Revenue Dept",
        95.0
    )
    ingest_file(
        "/app/uploads/rural/punjab_panchayat.geojson",
        "municipal",
        "Gram Panchayat Crop Registry",
        "Local Panchayat",
        80.0
    )
    print("Done. Ready to match.")
