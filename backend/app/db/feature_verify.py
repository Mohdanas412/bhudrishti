from app.db.session import SessionLocal
from app.models.feature import Feature

db = SessionLocal()
features = db.query(Feature).filter(Feature.dataset_id == 3).all()
for f in features:
    print(
        f"id={f.id} feature_id={f.feature_id} attributes={f.attributes} area={f.area}"
    )
db.close()
