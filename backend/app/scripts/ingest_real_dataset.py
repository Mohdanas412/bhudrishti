"""Driver to ingest real GeoJSON into the full BhuDrishti pipeline."""
import os
import sys

from app.db.session import SessionLocal
from app.models.dataset import Dataset
from app.models.source import Source
from app.services.datasets import (
    validate_dataset_geometry,
    standardize_dataset_ingest,
    standardize_dataset_fields,
)
from app.services.reconciliation_service import get_all_matches

def ingest_file(file_path: str, dataset_type: str, source_name: str, authority: str, rel_score: float):
    db = SessionLocal()
    try:
        # 1. Provide a real Source
        src = db.query(Source).filter(Source.name == source_name).first()
        if not src:
            src = Source(name=source_name, authority=authority, reliability_score=rel_score)
            db.add(src)
            db.commit()
            db.refresh(src)
            print(f"Created source: {src.name} (id={src.id})")
        else:
            print(f"Found source: {src.name} (id={src.id})")

        # 2. Register Dataset
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
            print(f"Created dataset row id={ds.id} for {os.path.basename(file_path)}")
        else:
            print(f"Found dataset row id={ds.id} for {os.path.basename(file_path)}")

        # 3. Pipeline
        print("  Running validate_dataset_geometry...")
        v_res = validate_dataset_geometry(ds.id, db)
        print(f"    valid={v_res.get('valid')} issues={len(v_res.get('issues',[]))}")

        print("  Running standardize_dataset_ingest (CRS + coverage)...")
        i_res = standardize_dataset_ingest(ds.id, db)
        print(f"    crs={i_res.get('crs')} feature_count={i_res.get('feature_count')}")

        print("  Running standardize_dataset_fields (GeoPandas + DB Feature mapping)...")
        f_res = standardize_dataset_fields(ds.id, db)
        print(f"    features_created={f_res.get('features_created')} unmapped={len(f_res.get('unmapped_fields',[]))}")

    finally:
        db.close()


if __name__ == "__main__":
    datasets_to_run = [
        (
            "/app/uploads/real/bbmp_boundary.geojson",
            "municipal",
            "Bruhat Bengaluru Mahanagara Palike (OSM)",
            "Municipal/Open Data",
            85.0
        ),
        (
            "/app/uploads/real/bengaluru_buildings_osm.geojson",
            "building",
            "OpenStreetMap Contributors (Bengaluru Base)",
            "OSM Foundation",
            90.0
        ),
        (
            "/app/uploads/real/bengaluru_buildings_survey.geojson",
            "building",
            "Bengaluru Urban Survey 2024 (Simulated)",
            "Local Authority",
            80.0
        ),
    ]

    for path, dtype, sname, auth, rel in datasets_to_run:
        print(f"\n{'='*60}\nIngesting: {os.path.basename(path)}")
        ingest_file(path, dtype, sname, auth, rel)

    print("\n" + "="*60 + "\nPipeline run complete. Verifying matches available...")
    db = SessionLocal()
    try:
        matches = get_all_matches(db)
        print(f"Generated {len(matches)} matches across real datasets.")
        high = sum(1 for m in matches if m["score"] >= 90)
        review = sum(1 for m in matches if 70 <= m["score"] < 90)
        low = sum(1 for m in matches if m["score"] < 70)
        print(f"  Distribution: High Conf={high} | Review={review} | Low={low}")
    finally:
        db.close()
