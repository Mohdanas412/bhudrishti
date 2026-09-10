"""
Analytics & Reporting API Router for BhuDrishti.

Exposes:
  - Spatial hotspot density clusters.
  - KPI summary metrics and charts for compliance reporting.
  - Conflict discrepancy heatmaps for spatial GIS overlays.
  - Certified parcel registry export in GeoJSON and CSV formats.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.analytics_service import (
    generate_export_data,
    get_analytics_summary,
    get_discrepancy_heatmap,
    get_spatial_hotspots,
)

router = APIRouter()


@router.get("/hotspots")
async def get_hotspots_route(db: Session = Depends(get_db)):
    """Computes and returns spatial density hotspot clusters for detected conflicts."""
    return get_spatial_hotspots(db)


@router.get("/summary")
async def get_analytics_summary_route(db: Session = Depends(get_db)):
    """Returns official executive summary KPIs, resolution rates, and quality index metrics."""
    return get_analytics_summary(db)


@router.get("/discrepancy-heatmap")
async def get_discrepancy_heatmap_route(db: Session = Depends(get_db)):
    """Returns weighted discrepancy point FeatureCollection for GIS intensity heatmaps."""
    return get_discrepancy_heatmap(db)


@router.get("/export/{export_format}")
async def export_certified_registry(
    export_format: str,
    db: Session = Depends(get_db),
):
    """Exports certified harmonized land records in GeoJSON or CSV format."""
    fmt = export_format.lower()
    if fmt not in ("geojson", "json", "csv"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{export_format}'. Use 'geojson' or 'csv'.",
        )

    content, media_type, filename = generate_export_data(
        db, "csv" if fmt == "csv" else "geojson"
    )

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
