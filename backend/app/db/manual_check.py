from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.dataset import Dataset
from app.models.source import Source  # noqa: F401

Base.metadata.create_all(bind=engine)

db = SessionLocal()
new_ds = Dataset(file_path="uploads/test_cadastral.geojson", status="uploaded")
db.add(new_ds)
db.commit()
db.refresh(new_ds)
print("Created:", new_ds.id, new_ds.status)

fetched = db.query(Dataset).filter(Dataset.id == new_ds.id).first()
print("Fetched:", fetched.id, fetched.file_path)
db.close()
