
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.reconciliation_service import (
    bulk_auto_match_service,
    correct_harmonized_topology_service,
    get_harmonized_feature_collection,
    merge_parcels_service,
    split_parcel_service,
)

router = APIRouter()


class ParcelMergeRequest(BaseModel):
    parcel_ids: list[str] = Field(..., min_length=2, description="List of parcel IDs to merge")
    target_parcel_id: str | None = Field(None, description="Optional custom parcel ID for the merged entity")
    combined_owner: str | None = Field(None, description="Optional reconciled owner name")


class ParcelSplitRequest(BaseModel):
    parcel_id: str = Field(..., description="Parcel ID to subdivide")
    split_parts: int = Field(2, ge=2, le=10, description="Number of sub-parcels to create")
    direction: str = Field("vertical", description="'vertical' or 'horizontal' subdivision axis")


class AutoMatchRequest(BaseModel):
    threshold: int = Field(90, ge=50, le=100, description="Minimum confidence threshold to auto-approve")


@router.get("")
async def get_harmonized(db: Session = Depends(get_db)):
    """Final unified dataset as GeoJSON, traceable to source_feature_ids. Owner: M3 + M6."""
    return get_harmonized_feature_collection(db)


@router.post("/topology/correct")
async def correct_harmonized_topology(
    tolerance: float = Query(0.00005, description="Vertex snap distance tolerance"),
    max_gap_area_sqm: float = Query(50.0, description="Max micro-gap area in m² to absorb"),
    max_overlap_area_sqm: float = Query(100.0, description="Max micro-overlap area in m² to resolve"),
    auto_merge_overlaps: bool = Query(True, description="Automatically merge/clip micro-overlaps"),
    auto_fill_gaps: bool = Query(True, description="Automatically fill micro-gaps/slivers"),
    db: Session = Depends(get_db),
):
    """Run automated multi-layer vertex snapping and topology correction on harmonized parcels."""
    return correct_harmonized_topology_service(
        db=db,
        tolerance=tolerance,
        max_gap_area_sqm=max_gap_area_sqm,
        max_overlap_area_sqm=max_overlap_area_sqm,
        auto_merge_overlaps=auto_merge_overlaps,
        auto_fill_gaps=auto_fill_gaps,
    )


@router.post("/merge")
async def merge_parcels_endpoint(req: ParcelMergeRequest, db: Session = Depends(get_db)):
    """Merge multiple parcels into a single contiguous entity with re-generated 14-char ULPIN."""
    try:
        merged = merge_parcels_service(
            db=db,
            parcel_ids=req.parcel_ids,
            target_parcel_id=req.target_parcel_id,
            combined_owner=req.combined_owner,
        )
        return {
            "status": "merged",
            "merged_feature": merged,
            "total_harmonized": len(get_harmonized_feature_collection(db)["features"]),
        }
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Parcel merge failed: {exc!s}")


@router.post("/split")
async def split_parcel_endpoint(req: ParcelSplitRequest, db: Session = Depends(get_db)):
    """Subdivide a parcel into clean, contiguous sub-parcels with derived ULPINs."""
    try:
        sub_parcels = split_parcel_service(
            db=db,
            parcel_id=req.parcel_id,
            split_parts=req.split_parts,
            direction=req.direction,
        )
        return {
            "status": "split",
            "parcel_id": req.parcel_id,
            "sub_parcels": sub_parcels,
            "total_harmonized": len(get_harmonized_feature_collection(db)["features"]),
        }
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Parcel split failed: {exc!s}")


@router.post("/auto-match")
async def auto_match_endpoint(
    req: AutoMatchRequest | None = Body(None),
    threshold: int | None = Query(None, ge=50, le=100),
    db: Session = Depends(get_db),
):
    """Batch auto-approve high-confidence candidate matches into the harmonized registry."""
    try:
        t = (req.threshold if req is not None else None) or threshold or 90
        res = bulk_auto_match_service(db=db, threshold=t)
        return res
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Auto-match failed: {exc!s}")
