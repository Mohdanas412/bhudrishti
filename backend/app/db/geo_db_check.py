from app.db.session import SessionLocal
from app.models.dataset import Dataset

db = SessionLocal()

for dataset_id in [3, 4]:
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if ds is None:
        print(f"Dataset {dataset_id}: NOT FOUND")
        continue
    print(
        f"Dataset {dataset_id}: status={ds.status}, crs={ds.crs}, feature_count={ds.feature_count}"
    )

db.close()
