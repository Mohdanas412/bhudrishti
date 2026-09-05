import json
import os
import shutil

import geopandas as gpd
from fastapi import UploadFile
from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from app.engines.gis import (
    IngestError,
    ingest_dataset,
    repair_dataset,
    validate_dataset,
)
from app.models.dataset import Dataset
from app.models.feature import Feature

# Relative to cwd (backend/), per the db path convention
UPLOAD_DIR = "uploads"
STANDARDIZED_DIR = os.path.join(UPLOAD_DIR, "standardized")

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
    """Run per-feature geometry validation on a dataset.

    Thin wrapper around engines/gis.validate_dataset. The engine owns the
    per-feature loop and the CRS/empty/invalid checks; this function only
    loads the dataset row, persists the engine's verdict onto the row, and
    returns the engine result in M3's existing response shape.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if dataset is None:
        return None

    result = validate_dataset(dataset.file_path)

    dataset.crs = result.crs
    dataset.feature_count = result.feature_count
    dataset.status = "validated" if result.valid else "invalid"
    db.commit()

    return {"valid": result.valid, "issues": result.issues}


def standardize_dataset_ingest(dataset_id: int, db: Session) -> dict:
    """CRS-normalize a dataset and compute its coverage boundary.

    Delegates the actual transformation to engines/gis.ingestion so the engine
    stays storage-agnostic (per backend/app/db/README.md). Owner: M4.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if dataset is None:
        return None

    try:
        result = ingest_dataset(dataset.file_path)
    except IngestError as exc:
        return {"error": str(exc)}

    dataset.crs = result.crs
    dataset.feature_count = result.feature_count
    dataset.coverage_boundary_geojson = json.dumps(result.coverage_geojson)
    db.commit()

    return {"crs": result.crs, "feature_count": result.feature_count}


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


def repair_dataset_service(dataset_id: int, db: Session) -> dict:
    """Repair invalid geometries in a dataset and persist the cleaned GDF.

    The engine (engines/gis.repair_dataset) is storage-agnostic — it
    returns a RepairResult containing the cleaned GeoDataFrame. This
    service function handles the I/O wiring: writing the cleaned GDF
    to uploads/standardized/{id}.geojson and persisting the verdict
    on the dataset row.

    The cleaned file's path is derivable from `dataset_id`, so we don't
    add a new schema column in this PR — M6 may add `standardized_path`
    later. (See PR #11's open items.)

    Returns None when the dataset id is unknown.
    Returns a dict with `_error` set when the engine rejects the file.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if dataset is None:
        return None

    result = repair_dataset(dataset.file_path)

    # File-level failures (CRS missing, unreadable): no GDF, no I/O.
    # Detect via the absence of a usable CRS in the result.
    if result.crs is None and result.feature_count == 0 and result.dropped_count == 0:
        first = result.issues[0] if result.issues else {}
        return {
            "_error": first.get("code", "ingest_failed"),
            "detail": first.get("reason", ""),
        }

    # Persist the cleaned GDF to disk. The path is deterministic so a
    # re-run of /repair overwrites cleanly.
    os.makedirs(STANDARDIZED_DIR, exist_ok=True)
    standardized_path = os.path.join(STANDARDIZED_DIR, f"{dataset_id}.geojson").replace(
        os.sep, "/"
    )
    if not result.gdf.empty:
        result.gdf.to_file(standardized_path, driver="GeoJSON")
    else:
        # All features dropped — still write an empty FeatureCollection so
        # downstream readers don't have to special-case a missing file.
        empty = result.gdf.copy()  # empty GeoDataFrame with the same CRS (None)
        empty.to_file(standardized_path, driver="GeoJSON")

    dataset.crs = result.crs
    dataset.feature_count = result.feature_count
    dataset.status = "repaired"
    db.commit()

    return {
        "dataset_id": dataset_id,
        "status": dataset.status,
        "crs": result.crs,
        "feature_count": result.feature_count,
        "dropped_count": result.dropped_count,
        "repaired_count": len(result.repaired_indices),
        "repaired_indices": result.repaired_indices,
        "standardized_path": standardized_path,
        "issues": result.issues,
    }
