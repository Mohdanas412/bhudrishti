"""
GeoAI Analytics API Router.

Provides:
  - Encroachment detection between Cadastral and Drone/Survey layers.
  - Dataset-to-dataset automated encroachment detection.
  - Right-of-Way (RoW) buffer breach detection.
"""

from typing import Any

import geopandas as gpd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.engines.gis.encroachment import (
    detect_encroachments,
    detect_row_buffer_breaches,
)
from app.services.datasets import get_dataset_geojson

router = APIRouter()


class EncroachmentRequest(BaseModel):
    cadastral_geojson: Any
    drone_geojson: Any
    permissible_variance_sqm: float = 5.0


class RowBufferRequest(BaseModel):
    corridor_geojson: Any
    parcels_geojson: Any
    buffer_meters: float = Field(10.0, description="Corridor buffer distance in meters")


@router.post("/analysis/encroachment")
async def analyze_encroachment_endpoint(req: EncroachmentRequest):
    """Run spatial intersection and delta analysis to detect illegal parcel encroachments."""
    try:
        cadastral_features = req.cadastral_geojson.get("features", [])
        drone_features = req.drone_geojson.get("features", [])

        if not cadastral_features or not drone_features:
            return {
                "total_encroachments": 0,
                "total_area_sqm": 0.0,
                "metrics": [],
                "geojson": {"type": "FeatureCollection", "features": []},
            }

        cadastral_gdf = gpd.GeoDataFrame.from_features(cadastral_features)
        drone_gdf = gpd.GeoDataFrame.from_features(drone_features)

        report = detect_encroachments(cadastral_gdf, drone_gdf, req.permissible_variance_sqm)
        return report.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Analysis failed: {exc!s}")


@router.post("/analysis/row-buffer")
async def analyze_row_buffer_endpoint(req: RowBufferRequest):
    """Analyze Right-of-Way (RoW) buffer breaches along transport or utility corridors."""
    try:
        def _extract_features(raw_obj: Any) -> list[dict[str, Any]]:
            if not raw_obj:
                return []
            if isinstance(raw_obj, dict):
                if raw_obj.get("type") == "FeatureCollection":
                    return raw_obj.get("features", [])
                if raw_obj.get("type") == "Feature":
                    return [raw_obj]
                # If raw geometry dict (e.g. {"type": "LineString", "coordinates": ...})
                if "type" in raw_obj and "coordinates" in raw_obj:
                    return [{"type": "Feature", "geometry": raw_obj, "properties": {}}]
            elif isinstance(raw_obj, list):
                feats = []
                for item in raw_obj:
                    if isinstance(item, dict):
                        if item.get("type") == "Feature":
                            feats.append(item)
                        elif "geometry" in item:
                            feats.append({"type": "Feature", "geometry": item["geometry"], "properties": item.get("properties", {})})
                        elif "type" in item and "coordinates" in item:
                            feats.append({"type": "Feature", "geometry": item, "properties": {}})
                return feats
            return []

        corridor_features = _extract_features(req.corridor_geojson)
        parcels_features = _extract_features(req.parcels_geojson)

        if not corridor_features or not parcels_features:
            return {
                "status": "success",
                "total_breaches": 0,
                "buffer_meters": req.buffer_meters,
                "breaches": [],
                "breach_features": {"type": "FeatureCollection", "features": []},
            }

        corridor_gdf = gpd.GeoDataFrame.from_features(corridor_features, crs="EPSG:4326")
        parcels_gdf = gpd.GeoDataFrame.from_features(parcels_features, crs="EPSG:4326")

        breaches = detect_row_buffer_breaches(corridor_gdf, parcels_gdf, req.buffer_meters)
        
        breach_feats = []
        for b in breaches:
            geom = b.get("breach_geometry")
            if geom:
                breach_feats.append({
                    "type": "Feature",
                    "geometry": geom,
                    "properties": {
                        "parcel_id": b.get("parcel_id"),
                        "severity": b.get("severity"),
                        "breach_area_sqm": b.get("breach_area_sqm"),
                    }
                })

        return {
            "status": "success",
            "total_breaches": len(breaches),
            "buffer_meters": req.buffer_meters,
            "breaches": breaches,
            "breach_features": {
                "type": "FeatureCollection",
                "features": breach_feats,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"RoW buffer analysis failed: {exc!s}")


@router.post("/datasets/encroachment")
async def analyze_datasets_encroachment_endpoint(
    cadastral_dataset_id: int = Query(..., description="Cadastral baseline dataset ID"),
    survey_dataset_id: int = Query(..., description="Survey or drone dataset ID"),
    permissible_variance_sqm: float = Query(5.0, description="Permissible variance threshold in m²"),
    db: Session = Depends(get_db),
):
    """Run encroachment analysis directly between two uploaded dataset IDs."""
    cadastral_json = get_dataset_geojson(cadastral_dataset_id, db)
    if not cadastral_json:
        raise HTTPException(status_code=404, detail="Cadastral dataset not found or has no features")

    survey_json = get_dataset_geojson(survey_dataset_id, db)
    if not survey_json:
        raise HTTPException(status_code=404, detail="Survey dataset not found or has no features")

    try:
        cad_features = cadastral_json.get("features", [])
        surv_features = survey_json.get("features", [])

        cad_gdf = gpd.GeoDataFrame.from_features(cad_features) if cad_features else gpd.GeoDataFrame()
        surv_gdf = gpd.GeoDataFrame.from_features(surv_features) if surv_features else gpd.GeoDataFrame()

        report = detect_encroachments(cad_gdf, surv_gdf, permissible_variance_sqm)
        return {
            "cadastral_dataset_id": cadastral_dataset_id,
            "survey_dataset_id": survey_dataset_id,
            **report.to_dict(),
        }
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Dataset encroachment analysis failed: {exc!s}")
