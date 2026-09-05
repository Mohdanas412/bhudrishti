from app.db.session import SessionLocal
from app.models.source import (
    Source,  # noqa: F401 — import so 'sources' table registers for the FK
)
from app.services.datasets import standardize_dataset_fields

db = SessionLocal()
result = standardize_dataset_fields(6, db)  # dataset_id=6 = plot_variant.geojson
print(result)
db.close()
