from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.dataset import (
    Dataset,  # noqa: F401  — import so 'datasets' table registers for the FK
)
from app.models.feature import Feature

Base.metadata.create_all(
    bind=engine
)  # creates 'features' table if it doesn't exist yet — safe, never drops existing tables

db = SessionLocal()

new_feature = Feature(
    dataset_id=3,
    feature_id="P001",
    geometry_geojson='{"type":"Polygon","coordinates":[[[77.209,28.6139],[77.211,28.6139],[77.211,28.6159],[77.209,28.6159],[77.209,28.6139]]]}',
    area=None,
    attributes={"land_use": "residential"},
)
db.add(new_feature)
db.commit()
db.refresh(new_feature)
print("Created:", new_feature.id, new_feature.feature_id, new_feature.attributes)

fetched = db.query(Feature).filter(Feature.id == new_feature.id).first()
print(
    "Fetched:", fetched.id, fetched.dataset_id, fetched.feature_id, fetched.attributes
)

db.close()
