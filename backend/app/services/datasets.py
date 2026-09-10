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
    correct_topology,
    ingest_dataset,
    repair_dataset,
    validate_dataset,
)
from app.engines.standards import generate_ulpin, map_indic_properties
from app.models.dataset import Dataset
from app.models.feature import Feature
from app.models.source import Source

# Relative to cwd (backend/), per the db path convention
UPLOAD_DIR = "uploads"
STANDARDIZED_DIR = os.path.join(UPLOAD_DIR, "standardized")

TARGET_CRS = "EPSG:4326"

# UTM Zone 43N — covers North India, matches this project's test data and
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

    # If file doesn't exist on disk, check if features exist in the DB and serialize them to disk
    if not os.path.exists(dataset.file_path):
        features = db.query(Feature).filter(Feature.dataset_id == dataset.id).all()
        if features:
            os.makedirs(os.path.dirname(dataset.file_path), exist_ok=True)
            geojson_data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": json.loads(f.geojson) if isinstance(f.geojson, str) else f.geojson,
                        "properties": f.attributes or {}
                    }
                    for f in features
                ]
            }
            with open(dataset.file_path, "w") as f:
                json.dump(geojson_data, f)

    result = validate_dataset(dataset.file_path)

    dataset.crs = result.crs or dataset.crs or "EPSG:4326"
    dataset.feature_count = result.feature_count if result.feature_count is not None else dataset.feature_count
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
    Maps one feature's raw properties dict onto canonical fields using Indic NLP mapper
    and rapidfuzz fallback.
    Returns (feature_id, attributes, unmapped_field_names).
    """
    # First attempt Indic / Vernacular Term Translation
    indic_mapped = map_indic_properties(properties)

    flat_synonym_to_canonical = {}
    for canonical, synonyms in synonym_dict.items():
        for syn in synonyms:
            flat_synonym_to_canonical[syn] = canonical

    mapped = {}
    unmapped = []

    # Merge Indic-extracted fields if present
    if indic_mapped.get("parcel_id"):
        mapped["parcel_id"] = indic_mapped["parcel_id"]
    if indic_mapped.get("owner"):
        mapped["owner"] = indic_mapped["owner"]
    if indic_mapped.get("land_use"):
        mapped["land_use"] = indic_mapped["land_use"]
    if indic_mapped.get("khata_number"):
        mapped["khata_number"] = indic_mapped["khata_number"]
    if indic_mapped.get("village"):
        mapped["village"] = indic_mapped["village"]

    for raw_key, raw_value in properties.items():
        if raw_key.lower() in ("ulpin", "bhu_aadhar"):
            mapped[raw_key.lower()] = raw_value
            continue
        if raw_key.lower() in ("parcel_id", "plot_no", "khasra", "खसरा"):
            mapped["parcel_id"] = raw_value
            continue
        match = process.extractOne(
            raw_key.lower(), flat_synonym_to_canonical.keys(), scorer=fuzz.ratio
        )
        if match is not None and match[1] >= FIELD_MATCH_THRESHOLD:
            canonical_field = flat_synonym_to_canonical[match[0]]
            mapped[canonical_field] = raw_value
        else:
            if raw_key not in mapped:
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

    # Reproject once upfront for metric area calculation rather than per-row
    try:
        projected_gdf = gdf.to_crs(AREA_CALC_CRS) if gdf.crs is not None else None
    except Exception:
        projected_gdf = None

    # Idempotency: clear any previously-ingested features for this dataset
    db.query(Feature).filter(Feature.dataset_id == dataset.id).delete()

    created_count = 0
    all_unmapped = []

    for idx_num, (idx, row) in enumerate(gdf.iterrows()):
        properties = row.drop("geometry").to_dict()
        feature_id, attributes, unmapped = _map_properties(properties, synonym_dict)

        if unmapped:
            all_unmapped.append({"feature_index": idx, "unmapped_fields": unmapped})

        c = row.geometry.centroid
        ulpin_id = generate_ulpin(c.y, c.x, polygon=row.geometry)
        attributes["ulpin"] = ulpin_id
        attributes["bhu_aadhar"] = ulpin_id

        calc_area = 0.0
        if projected_gdf is not None and idx_num < len(projected_gdf):
            calc_area = float(projected_gdf.geometry.iloc[idx_num].area)
        elif hasattr(row.geometry, "area"):
            calc_area = float(row.geometry.area)

        new_feature = Feature(
            dataset_id=dataset.id,
            feature_id=str(feature_id) if feature_id is not None else f"unknown-{idx}",
            geometry_geojson=json.dumps(row.geometry.__geo_interface__),
            area=calc_area,
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
    with open(standardized_path, "w", encoding="utf-8") as f:
        f.write(result.gdf.to_json() if not result.gdf.empty else result.gdf.copy().to_json())

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


def correct_dataset_topology_service(
    dataset_id: int,
    db: Session,
    reference_dataset_id: int | None = None,
    tolerance: float = 0.00005,
    max_gap_area_sqm: float = 50.0,
    max_overlap_area_sqm: float = 100.0,
    auto_merge_overlaps: bool = True,
    auto_fill_gaps: bool = True,
) -> dict | None:
    """Automated Topology Correction and Snapping for a dataset.

    Loads the dataset GDF, optional reference GDF, applies multi-layer / intra-layer
    vertex snapping, gap filling, overlap merging, writes the corrected GeoJSON,
    and returns a comprehensive Topology Health Report.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        return None

    if not dataset.file_path or not os.path.exists(dataset.file_path):
        return {"_error": "file_not_found", "detail": f"Dataset file {dataset.file_path} not found"}

    try:
        gdf = gpd.read_file(dataset.file_path)
    except Exception as exc:
        return {"_error": "file_unreadable", "detail": str(exc)}

    if gdf.crs is not None and str(gdf.crs) != TARGET_CRS:
        gdf = gdf.to_crs(TARGET_CRS)

    reference_gdf = None
    if reference_dataset_id:
        ref_ds = db.query(Dataset).filter(Dataset.id == reference_dataset_id).first()
        if ref_ds and ref_ds.file_path and os.path.exists(ref_ds.file_path):
            try:
                reference_gdf = gpd.read_file(ref_ds.file_path)
                if reference_gdf.crs is not None and str(reference_gdf.crs) != TARGET_CRS:
                    reference_gdf = reference_gdf.to_crs(TARGET_CRS)
            except Exception:
                pass

    # Execute topology correction engine
    corrected_gdf, health_report = correct_topology(
        gdf=gdf,
        reference_gdf=reference_gdf,
        tolerance=tolerance,
        max_gap_area_sqm=max_gap_area_sqm,
        max_overlap_area_sqm=max_overlap_area_sqm,
        auto_merge_overlaps=auto_merge_overlaps,
        auto_fill_gaps=auto_fill_gaps,
    )

    # Persist corrected layer to standardized dir
    os.makedirs(STANDARDIZED_DIR, exist_ok=True)
    corrected_path = os.path.join(STANDARDIZED_DIR, f"{dataset_id}_topology_corrected.geojson").replace(os.sep, "/")
    with open(corrected_path, "w", encoding="utf-8") as f:
        f.write(corrected_gdf.to_json())

    dataset.status = "topology_corrected"
    dataset.feature_count = len(corrected_gdf)
    db.commit()

    return {
        "dataset_id": dataset_id,
        "status": dataset.status,
        "file_path": corrected_path,
        "feature_count": len(corrected_gdf),
        "health_report": health_report.to_dict(),
    }


def compute_topology_health_service(
    dataset_id: int,
    db: Session,
    reference_dataset_id: int | None = None,
    tolerance: float = 0.00005,
) -> dict | None:
    """Audit dataset topology health without mutating files."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        return None

    if not dataset.file_path or not os.path.exists(dataset.file_path):
        return {"_error": "file_not_found", "detail": f"Dataset file {dataset.file_path} not found"}

    try:
        gdf = gpd.read_file(dataset.file_path)
    except Exception as exc:
        return {"_error": "file_unreadable", "detail": str(exc)}

    if gdf.crs is not None and str(gdf.crs) != TARGET_CRS:
        gdf = gdf.to_crs(TARGET_CRS)

    reference_gdf = None
    if reference_dataset_id:
        ref_ds = db.query(Dataset).filter(Dataset.id == reference_dataset_id).first()
        if ref_ds and ref_ds.file_path and os.path.exists(ref_ds.file_path):
            try:
                reference_gdf = gpd.read_file(ref_ds.file_path)
                if reference_gdf.crs is not None and str(reference_gdf.crs) != TARGET_CRS:
                    reference_gdf = reference_gdf.to_crs(TARGET_CRS)
            except Exception:
                pass

    # Run check without applying mutation
    _, health_report = correct_topology(
        gdf=gdf,
        reference_gdf=reference_gdf,
        tolerance=tolerance,
        auto_merge_overlaps=False,
        auto_fill_gaps=False,
    )

    return {
        "dataset_id": dataset_id,
        "status": dataset.status,
        "feature_count": len(gdf),
        "health_report": health_report.to_dict(),
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
                    "id": f.feature_id,
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


def seed_sample_sih_project(db: Session, num_datasets: int = 6) -> dict:
    """Pre-seeds canonical pilot datasets (Cadastral, Municipal, Building footprint)
    with realistic overlapping parcels, area discrepancies, and attributes for SIH evaluation.

    Args:
        db: Database session
        num_datasets: Number of datasets to create (default 6, distributed across 3 types)
    """
    import random


    os.makedirs(UPLOAD_DIR, exist_ok=True)
    sample_dir = os.path.join(UPLOAD_DIR, "sih_sample")
    os.makedirs(sample_dir, exist_ok=True)

    # 1. Sources
    src_cad = db.query(Source).filter(Source.name == "State Revenue & Land Records Authority").first()
    if not src_cad:
        src_cad = Source(name="State Revenue & Land Records Authority", authority="State Govt", reliability_score=95.0)
        db.add(src_cad)
    src_mun = db.query(Source).filter(Source.name == "Municipal Urban Local Body").first()
    if not src_mun:
        src_mun = Source(name="Municipal Urban Local Body", authority="Municipal Urban Local Body", reliability_score=82.0)
        db.add(src_mun)
    src_bld = db.query(Source).filter(Source.name == "Urban Shelter & Building Registry").first()
    if not src_bld:
        src_bld = Source(name="Urban Shelter & Building Registry", authority="Building & Housing Authority", reliability_score=88.0)
        db.add(src_bld)
    db.commit()
    db.refresh(src_cad)
    db.refresh(src_mun)
    db.refresh(src_bld)

    # 2. Helper functions to generate synthetic parcel geometries
    def generate_grid_parcels(base_lon: float, base_lat: float, rows: int, cols: int, cell_size: float,
                               parcel_type: str, start_id: int, jitter: float = 0.00002) -> list:
        """Generate a grid of parcels with optional jitter for realistic topology issues."""
        features = []
        land_uses = ["Residential", "Commercial", "Industrial", "Public Utility", "Agricultural"]
        owners = ["Sunita Devi", "Ramesh Sharma", "Apex Retailers Pvt Ltd", "Parks & Recreation Board",
                  "Vikas Logistics & Warehousing", "Municipal Corp", "Private Developer", "Govt Agency"]
        zones = ["Zone R-1", "Zone R-2", "Zone C-1", "Zone I-1", "Green Belt", "Mixed Use"]

        feat_idx = 0
        for row in range(rows):
            for col in range(cols):
                # Base coordinates
                min_lon = base_lon + col * cell_size
                max_lon = min_lon + cell_size
                min_lat = base_lat + row * cell_size
                max_lat = min_lat + cell_size

                # Add small random jitter to simulate survey discrepancies
                jitter_lon = random.uniform(-jitter, jitter)
                jitter_lat = random.uniform(-jitter, jitter)

                coords = [
                    [min_lon + jitter_lon, min_lat + jitter_lat],
                    [max_lon + jitter_lon, min_lat + jitter_lat],
                    [max_lon + jitter_lon, max_lat + jitter_lat],
                    [min_lon + jitter_lon, max_lat + jitter_lat],
                    [min_lon + jitter_lon, min_lat + jitter_lat]
                ]

                if parcel_type == "cadastral":
                    props = {
                        "parcel_id": f"P-{start_id + feat_idx:05d}",
                        "land_use": random.choice(land_uses),
                        "owner": random.choice(owners)
                    }
                elif parcel_type == "municipal":
                    props = {
                        "parcel_id": f"M-{start_id + feat_idx:05d}",
                        "zone": random.choice(zones),
                        "address": f"Plot {start_id + feat_idx}, Sector {row + 1}"
                    }
                else:  # building
                    props = {
                        "parcel_id": f"BLD-{start_id + feat_idx:05d}",
                        "building_type": random.choice(["Residential Multi-family", "Residential Villa", "Commercial Plaza",
                                                        "Industrial Warehouse", "Public Facility"]),
                        "status": random.choice(["Occupied", "Under Construction", "Completed", "Vacant"])
                    }

                features.append({
                    "type": "Feature",
                    "properties": props,
                    "geometry": {"type": "Polygon", "coordinates": [coords]}
                })
                feat_idx += 1
        return features

    # 3. Generate datasets with configurable counts
    # Distribute datasets: ~40% cadastral, ~35% municipal, ~25% building
    cad_count = int(num_datasets * 0.4)
    mun_count = int(num_datasets * 0.35)
    bld_count = num_datasets - cad_count - mun_count

    created_datasets = []
    dataset_configs = [
        ("cadastral", src_cad.id, cad_count, 77.2000, 28.6100),
        ("municipal", src_mun.id, mun_count, 77.2000, 28.6100),
        ("building", src_bld.id, bld_count, 77.2000, 28.6100),
    ]

    for dtype, s_id, count, base_lon, base_lat in dataset_configs:
        if count <= 0:
            continue

        for ds_idx in range(count):
            # Each dataset gets a grid of parcels
            # Vary grid size and position per dataset
            rows = random.randint(3, 8)
            cols = random.randint(3, 8)
            cell_size = random.uniform(0.0015, 0.0030)
            offset_lon = random.uniform(0, 0.02)
            offset_lat = random.uniform(0, 0.02)

            # Number of features per dataset: 9-64
            features = generate_grid_parcels(
                base_lon + offset_lon, base_lat + offset_lat,
                rows, cols, cell_size, dtype,
                start_id=ds_idx * 1000,
                jitter=0.00003  # Small jitter for topology issues
            )

            data = {
                "type": "FeatureCollection",
                "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
                "features": features
            }

            fname = f"national_{dtype}_records_{ds_idx:03d}.geojson"
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

    return {
        "status": "seeded",
        "dataset_ids": created_datasets,
        "region": "Authoritative National Pilot Extent",
        "summary": {
            "cadastral": cad_count,
            "municipal": mun_count,
            "building": bld_count,
            "total_datasets": len(created_datasets)
        }
    }

