import json
import os
import shutil
from json import JSONDecodeError

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
from app.models.source import Source

# Relative to cwd (backend/), per the db path convention
UPLOAD_DIR = "uploads"
STANDARDIZED_DIR = os.path.join(UPLOAD_DIR, "standardized")

TARGET_CRS = "EPSG:4326"

# UTM Zone 43N — covers Delhi/North India, matches this project's test data and
# MVP scope (Section 3: "single project, single city/area"). Revisit if the
# project ever expands beyond this region — a different UTM zone would be needed.
AREA_CALC_CRS = "EPSG:32643"

# Canonical field -> known name variants seen in raw source files.
CADASTRAL_SYNONYMS = {
    "parcel_id": ["parcel_id", "plot_no", "plot_number", "feature_id", "id"],
    "land_use": ["land_use", "landuse", "use_type"],
    "owner": ["owner", "owner_name"],
}

MUNICIPAL_SYNONYMS = {
    "parcel_id": ["parcel_id", "property_id", "pin", "plot_no", "feature_id", "id"],
    "zone": ["zone", "zoning", "ward", "subzone"],
    "address": ["address", "addr", "street", "locality", "location"],
}

BUILDING_SYNONYMS = {
    "parcel_id": ["parcel_id", "building_id", "bldg_id", "feature_id", "id"],
    "building_type": ["building_type", "type", "structure_type", "usage"],
    "status": ["status", "condition", "occupancy", "building_status"],
}

DATASET_TYPE_SYNONYMS = {
    "cadastral": CADASTRAL_SYNONYMS,
    "municipal": MUNICIPAL_SYNONYMS,
    "building": BUILDING_SYNONYMS,
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

    # Idempotency: clear any previously-ingested features for this dataset so
    # re-running the pipeline (or seeding twice) doesn't create duplicate rows
    # that pollute matching with N identical pairs.
    db.query(Feature).filter(Feature.dataset_id == dataset.id).delete()

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


def list_datasets(db: Session) -> list[dict]:
    datasets = db.query(Dataset).order_by(Dataset.id.desc()).all()
    out = []
    for d in datasets:
        source_name = None
        if d.source_id:
            s = db.query(Source).filter(Source.id == d.source_id).first()
            if s:
                source_name = s.name
        out.append({
            "id": d.id,
            "filename": os.path.basename(d.file_path) if d.file_path else f"dataset_{d.id}",
            "file_path": d.file_path,
            "dataset_type": d.dataset_type,
            "status": d.status,
            "crs": d.crs,
            "feature_count": d.feature_count,
            "source_id": d.source_id,
            "source_name": source_name,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })
    return out


def get_dataset_by_id(dataset_id: int, db: Session) -> dict | None:
    d = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not d:
        return None
    source_name = None
    if d.source_id:
        s = db.query(Source).filter(Source.id == d.source_id).first()
        if s:
            source_name = s.name
    return {
        "id": d.id,
        "filename": os.path.basename(d.file_path) if d.file_path else f"dataset_{d.id}",
        "file_path": d.file_path,
        "dataset_type": d.dataset_type,
        "status": d.status,
        "crs": d.crs,
        "feature_count": d.feature_count,
        "source_id": d.source_id,
        "source_name": source_name,
        "coverage_boundary": json.loads(d.coverage_boundary_geojson) if d.coverage_boundary_geojson else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


def get_dataset_geojson(dataset_id: int, db: Session) -> dict | None:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        return None

    features = db.query(Feature).filter(Feature.dataset_id == dataset_id).all()
    if features:
        feature_list = []
        for f in features:
            try:
                geom = json.loads(f.geometry_geojson)
            except JSONDecodeError:
                geom = None
            props = {
                "id": f.id,
                "feature_id": f.feature_id,
                "dataset_id": f.dataset_id,
                "area": f.area,
                "authority": f.authority,
                "accuracy": f.accuracy,
                "dataset_type": dataset.dataset_type,
                **(f.attributes if isinstance(f.attributes, dict) else {}),
            }
            if geom:
                feature_list.append({
                    "type": "Feature",
                    "geometry": geom,
                    "properties": props,
                })
        return {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": dataset.crs or TARGET_CRS}},
            "features": feature_list,
        }

    # Fallback to reading file directly if features not yet persisted in table
    if dataset.file_path and os.path.exists(dataset.file_path):
        try:
            gdf = gpd.read_file(dataset.file_path)
            if gdf.crs is not None and str(gdf.crs) != TARGET_CRS:
                gdf = gdf.to_crs(TARGET_CRS)
            return json.loads(gdf.to_json())
        except (OSError, ValueError, JSONDecodeError):
            pass

    return {"type": "FeatureCollection", "features": []}


def seed_sample_sih_project(db: Session) -> dict:
    """Pre-seeds canonical Delhi-NCR datasets (Cadastral, Municipal, Building footprint)
    with realistic overlapping parcels, area discrepancies, and attributes for SIH evaluation."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    sample_dir = os.path.join(UPLOAD_DIR, "sih_sample")
    os.makedirs(sample_dir, exist_ok=True)

    # 1. Sources
    src_cad = db.query(Source).filter(Source.name == "Delhi Revenue & Land Records Authority").first()
    if not src_cad:
        src_cad = Source(name="Delhi Revenue & Land Records Authority", authority="State Govt", reliability_score=95.0)
        db.add(src_cad)
    src_mun = db.query(Source).filter(Source.name == "Municipal Corporation of Delhi (MCD)").first()
    if not src_mun:
        src_mun = Source(name="Municipal Corporation of Delhi (MCD)", authority="Municipal Urban Local Body", reliability_score=82.0)
        db.add(src_mun)
    src_bld = db.query(Source).filter(Source.name == "Delhi Urban Shelter & Building Registry").first()
    if not src_bld:
        src_bld = Source(name="Delhi Urban Shelter & Building Registry", authority="Building & Housing Authority", reliability_score=88.0)
        db.add(src_bld)
    db.commit()
    db.refresh(src_cad)
    db.refresh(src_mun)
    db.refresh(src_bld)

    # 2. GeoJSON Fixtures in Dwarka, Delhi (UTM 43N)
    cadastral_data = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": [
            {
                "type": "Feature",
                "properties": {"parcel_id": "P-101", "land_use": "Residential", "owner": "Sunita Devi"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2085, 28.6135], [77.2095, 28.6135], [77.2095, 28.6142], [77.2085, 28.6142], [77.2085, 28.6135]]]
                }
            },
            {
                "type": "Feature",
                "properties": {"parcel_id": "P-102", "land_use": "Residential", "owner": "Ramesh Sharma"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2096, 28.6135], [77.2108, 28.6135], [77.2108, 28.6144], [77.2096, 28.6144], [77.2096, 28.6135]]]
                }
            },
            {
                "type": "Feature",
                "properties": {"parcel_id": "P-103", "land_use": "Commercial", "owner": "Apex Retailers Pvt Ltd"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2110, 28.6136], [77.2122, 28.6136], [77.2122, 28.6145], [77.2110, 28.6145], [77.2110, 28.6136]]]
                }
            },
            {
                "type": "Feature",
                "properties": {"parcel_id": "P-104", "land_use": "Public Utility", "owner": "DDA Parks & Recreation"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2085, 28.6144], [77.2095, 28.6144], [77.2095, 28.6152], [77.2085, 28.6152], [77.2085, 28.6144]]]
                }
            },
            {
                "type": "Feature",
                "properties": {"parcel_id": "P-105", "land_use": "Industrial", "owner": "Vikas Logistics & Warehousing"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2097, 28.6146], [77.2115, 28.6146], [77.2115, 28.6155], [77.2097, 28.6155], [77.2097, 28.6146]]]
                }
            }
        ]
    }

    # Municipal dataset: overlaps with slight boundary shift & area differences
    municipal_data = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": [
            {
                "type": "Feature",
                "properties": {"parcel_id": "M-456", "zone": "Zone R-1", "address": "Plot 101, Sector 14, Dwarka"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2085, 28.6135], [77.2095, 28.6135], [77.2095, 28.6142], [77.2085, 28.6142], [77.2085, 28.6135]]]
                }
            },
            {
                "type": "Feature",
                "properties": {"parcel_id": "M-458", "zone": "Zone R-2", "address": "Plot 102, Sector 14, Dwarka"},
                "geometry": {
                    "type": "Polygon",
                    # Slightly expanded boundary simulating 16 m² encroachment / survey variation
                    "coordinates": [[[77.20955, 28.61348], [77.21085, 28.61348], [77.21085, 28.61442], [77.20955, 28.61442], [77.20955, 28.61348]]]
                }
            },
            {
                "type": "Feature",
                "properties": {"parcel_id": "M-459", "zone": "Zone C-1", "address": "Commercial Hub 103, Sector 14"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2110, 28.6136], [77.2122, 28.6136], [77.2122, 28.6145], [77.2110, 28.6145], [77.2110, 28.6136]]]
                }
            },
            {
                "type": "Feature",
                "properties": {"parcel_id": "M-460", "zone": "Green Belt", "address": "DDA Park Sector 14"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2085, 28.6144], [77.2095, 28.6144], [77.2095, 28.6152], [77.2085, 28.6152], [77.2085, 28.6144]]]
                }
            },
            {
                "type": "Feature",
                "properties": {"parcel_id": "M-461", "zone": "Industrial Zone", "address": "Plot 105, Phase 2, Dwarka"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2097, 28.6146], [77.2115, 28.6146], [77.2115, 28.6155], [77.2097, 28.6155], [77.2097, 28.6146]]]
                }
            }
        ]
    }

    # Building footprint dataset
    building_data = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": [
            {
                "type": "Feature",
                "properties": {"parcel_id": "BLD-101", "building_type": "Residential Multi-family", "status": "Occupied"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2087, 28.6136], [77.2093, 28.6136], [77.2093, 28.6141], [77.2087, 28.6141], [77.2087, 28.6136]]]
                }
            },
            {
                "type": "Feature",
                "properties": {"parcel_id": "BLD-102", "building_type": "Residential Villa", "status": "Under Construction"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2098, 28.6136], [77.2106, 28.6136], [77.2106, 28.6142], [77.2098, 28.6142], [77.2098, 28.6136]]]
                }
            },
            {
                "type": "Feature",
                "properties": {"parcel_id": "BLD-103", "building_type": "Commercial Plaza", "status": "Completed"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.2112, 28.6137], [77.2120, 28.6137], [77.2120, 28.6144], [77.2112, 28.6144], [77.2112, 28.6137]]]
                }
            }
        ]
    }

    created_datasets = []
    specs = [
        ("delhi_cadastral_records.geojson", cadastral_data, "cadastral", src_cad.id),
        ("delhi_municipal_gis.geojson", municipal_data, "municipal", src_mun.id),
        ("delhi_building_footprints.geojson", building_data, "building", src_bld.id),
    ]

    for fname, data, dtype, s_id in specs:
        fpath = os.path.join(sample_dir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Look for existing dataset or create new
        ds = db.query(Dataset).filter(Dataset.file_path == fpath).first()
        if not ds:
            ds = Dataset(
                file_path=fpath,
                dataset_type=dtype,
                source_id=s_id,
                status="uploaded",
            )
            db.add(ds)
            db.commit()
            db.refresh(ds)

        # Run validate and standardize
        validate_dataset_geometry(ds.id, db)
        standardize_dataset_ingest(ds.id, db)
        standardize_dataset_fields(ds.id, db)
        created_datasets.append(ds.id)

    return {"status": "seeded", "dataset_ids": created_datasets, "region": "Dwarka, New Delhi (UTM 43N)"}

