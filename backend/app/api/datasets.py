from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.datasets import (
    compute_topology_health_service,
    correct_dataset_topology_service,
    create_dataset,
    get_dataset_by_id,
    get_dataset_geojson,
    list_datasets,
    repair_dataset_service,
    seed_sample_sih_project,
    standardize_dataset_fields,
    standardize_dataset_ingest,
    validate_dataset_geometry,
)

router = APIRouter()


class DatasetType(str, Enum):
    """Closed set of dataset types, per Addendum v1 Critical Fix 1 canonical schema."""

    CADASTRAL = "cadastral"
    MUNICIPAL = "municipal"
    BUILDING = "building"


@router.post("")
async def upload_dataset(
    file: UploadFile, dataset_type: DatasetType, db: Session = Depends(get_db)
):
    """Upload + register a dataset (GeoJSON/Shapefile/CSV). Owner: M3 + M4."""
    dataset = create_dataset(file, dataset_type.value, db)
    return {
        "id": dataset.id,
        "filename": file.filename,
        "status": dataset.status,
        "dataset_type": dataset.dataset_type,
    }


@router.post("/{dataset_id}/validate")
async def validate_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Run CRS + geometry checks. Delegates to engines/gis. Owner: M4."""
    result = validate_dataset_geometry(dataset_id, db)

    if result is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return {
        "dataset_id": dataset_id,
        "valid": result["valid"],
        "issues": result["issues"],
    }


@router.post("/{dataset_id}/standardize")
async def standardize_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """CRS-normalize, compute coverage boundary (M4), then map fields to
    canonical attributes and create Feature rows (M3). Owner: M3 + M4."""
    ingest_result = standardize_dataset_ingest(dataset_id, db)

    if ingest_result is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if "error" in ingest_result:
        raise HTTPException(status_code=422, detail=ingest_result["error"])

    fields_result = standardize_dataset_fields(dataset_id, db)

    if fields_result is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if "error" in fields_result:
        raise HTTPException(status_code=422, detail=fields_result["error"])

    return {
        "dataset_id": dataset_id,
        "status": "standardized",
        "crs": ingest_result["crs"],
        "feature_count": ingest_result["feature_count"],
        "features_created": fields_result.get("features_created"),
        "unmapped_fields": fields_result.get("unmapped_fields"),
    }


@router.post("/{dataset_id}/repair")
async def repair_dataset_route(dataset_id: int, db: Session = Depends(get_db)):
    """Repair invalid geometries in a dataset and persist the cleaned GDF.

    Delegates to engines/gis.repair_dataset (M4). Self-intersections are
    fixed in place via shapely.make_valid; empty or unrepairable geoms
    are dropped. The cleaned GeoDataFrame is written to
    uploads/standardized/{id}.geojson. Dataset.status is set to
    'repaired'. Returns 422 for engine-level failures, 404 for missing id.
    """
    result = repair_dataset_service(dataset_id, db)

    if result is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if result.get("_error") in ("ingest_failed", "crs_missing", "file_unreadable"):
        raise HTTPException(status_code=422, detail=result["detail"])

    return result


@router.post("/{dataset_id}/topology/correct")
async def correct_dataset_topology_endpoint(
    dataset_id: int,
    reference_dataset_id: int | None = Query(None, description="Optional reference layer to snap onto"),
    tolerance: float = Query(0.00005, description="Vertex snap distance tolerance (degrees/approx meters)"),
    max_gap_area_sqm: float = Query(50.0, description="Max micro-gap area in m² to absorb"),
    max_overlap_area_sqm: float = Query(100.0, description="Max micro-overlap area in m² to resolve"),
    auto_merge_overlaps: bool = Query(True, description="Automatically merge/clip micro-overlaps"),
    auto_fill_gaps: bool = Query(True, description="Automatically fill micro-gaps/slivers"),
    db: Session = Depends(get_db),
):
    """Run Shapely automated multi-layer snap and topology correction on a dataset."""
    result = correct_dataset_topology_service(
        dataset_id=dataset_id,
        db=db,
        reference_dataset_id=reference_dataset_id,
        tolerance=tolerance,
        max_gap_area_sqm=max_gap_area_sqm,
        max_overlap_area_sqm=max_overlap_area_sqm,
        auto_merge_overlaps=auto_merge_overlaps,
        auto_fill_gaps=auto_fill_gaps,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if "_error" in result:
        raise HTTPException(status_code=422, detail=result.get("detail", "Topology correction error"))

    return result


@router.get("/{dataset_id}/topology/health")
async def get_dataset_topology_health_endpoint(
    dataset_id: int,
    reference_dataset_id: int | None = Query(None, description="Optional reference layer to inspect against"),
    tolerance: float = Query(0.00005, description="Snap tolerance threshold"),
    db: Session = Depends(get_db),
):
    """Retrieve Topology Health Report (gaps fixed, overlaps merged, health score) for a dataset."""
    result = compute_topology_health_service(
        dataset_id=dataset_id,
        db=db,
        reference_dataset_id=reference_dataset_id,
        tolerance=tolerance,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if "_error" in result:
        raise HTTPException(status_code=422, detail=result.get("detail", "Topology check error"))

    return result


@router.get("")
async def get_all_datasets(db: Session = Depends(get_db)):
    """List all registered datasets with metadata, status, and feature counts."""
    return list_datasets(db)


@router.get("/{dataset_id}")
async def get_single_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Retrieve details for a single dataset."""
    dataset = get_dataset_by_id(dataset_id, db)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/geojson")
async def get_dataset_features_geojson(dataset_id: int, db: Session = Depends(get_db)):
    """Stream standardized or raw dataset features as GeoJSON FeatureCollection."""
    geojson = get_dataset_geojson(dataset_id, db)
    if geojson is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return geojson


@router.post("/sample-seed")
async def seed_sample_datasets(db: Session = Depends(get_db)):
    """Pre-seed canonical Cadastral, Municipal, and Building datasets for SIH demonstration."""
    result = seed_sample_sih_project(db)
    return result
