import json
import os
import shutil

import geopandas as gpd
from fastapi import UploadFile
from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.feature import Feature

# Relative to cwd (backend/), per the db path convention
UPLOAD_DIR = "uploads"

TARGET_CRS = "EPSG:4326"

# UTM Zone 43N — covers Delhi/North India, matches this project's test data and
# MVP scope (Section 3: "single project, single city/area"). Revisit if the
# project ever expands beyond this region — a different UTM zone would be needed.
AREA_CALC_CRS = "EPSG:32643"

# Canonical field -> known name variants seen in raw source files.
# Municipal/Building dictionaries not added yet — no real test data for those types yet.
CADASTRAL_SYNONYMS = {
    "parcel_id": ["parcel_id", "plot_no", "plot_number"],
    "land_use": ["land_use", "landuse", "use_type"],
    "owner": ["owner", "owner_name"],
}

DATASET_TYPE_SYNONYMS = {
    "cadastral": CADASTRAL_SYNONYMS,
    # "municipal": MUNICIPAL_SYNONYMS,   — add when real test data exists
    # "building": BUILDING_SYNONYMS,     — add when real test data exists
}

FIELD_MATCH_THRESHOLD = (
    70  # configurable engineering parameter, per playbook's convention (Section 8)
)


def create_dataset(file: UploadFile, dataset_type: str, db: Session) -> Dataset:
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    save_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # source_id left unset (null) — no Source-creation flow yet, confirmed
    new_dataset = Dataset(
        file_path=save_path, status="uploaded", dataset_type=dataset_type
    )
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


def _map_properties(properties: dict, synonym_dict: dict) -> tuple:
    """
    Maps one feature's raw properties dict onto canonical fields using rapidfuzz.
    Returns (feature_id, attributes, unmapped_field_names).
    """
    flat_synonym_to_canonical = {}
    for canonical, synonyms in synonym_dict.items():
        for syn in synonyms:
            flat_synonym_to_canonical[syn] = canonical

    mapped = {}
    unmapped = []

    for raw_key, raw_value in properties.items():
        match = process.extractOne(
            raw_key.lower(), flat_synonym_to_canonical.keys(), scorer=fuzz.ratio
        )
        if match is not None and match[1] >= FIELD_MATCH_THRESHOLD:
            canonical_field = flat_synonym_to_canonical[match[0]]
            mapped[canonical_field] = raw_value
        else:
            unmapped.append(raw_key)

    feature_id = mapped.pop("parcel_id", None)
    attributes = mapped

    return feature_id, attributes, unmapped


def standardize_dataset_fields(dataset_id: int, db: Session) -> dict:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if dataset is None:
        return None

    synonym_dict = DATASET_TYPE_SYNONYMS.get(dataset.dataset_type)
    if synonym_dict is None:
        return {
            "error": f"No field-mapping dictionary yet for dataset_type '{dataset.dataset_type}'"
        }

    gdf = gpd.read_file(dataset.file_path)

    # Reproject to one common CRS (pyproj, via GeoPandas' to_crs) — Addendum-aligned Stage 4 requirement
    if gdf.crs is not None and str(gdf.crs) != TARGET_CRS:
        gdf = gdf.to_crs(TARGET_CRS)

    created_count = 0
    all_unmapped = []

    for idx, row in gdf.iterrows():
        properties = row.drop("geometry").to_dict()
        feature_id, attributes, unmapped = _map_properties(properties, synonym_dict)

        if unmapped:
            all_unmapped.append({"feature_index": idx, "unmapped_fields": unmapped})

        new_feature = Feature(
            dataset_id=dataset.id,
            feature_id=str(feature_id) if feature_id is not None else f"unknown-{idx}",
            geometry_geojson=json.dumps(row.geometry.__geo_interface__),
            area=gdf.loc[[idx]].to_crs(AREA_CALC_CRS).geometry.iloc[0].area,
            attributes=attributes,
        )
        db.add(new_feature)
        created_count += 1

    dataset.status = "standardized"
    db.commit()

    return {"features_created": created_count, "unmapped_fields": all_unmapped}
