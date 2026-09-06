from enum import Enum
from fastapi import APIRouter

from app.engines.reconciliation import build_conflict, recommend_conflict

router = APIRouter()


class RecommendationAction(str, Enum):
    """
    Closed set of recommendation actions. Frozen alongside docs/contracts/recommendation.json —
    do not add a value here without updating that file and notifying M1/M2/M5.
    """
    PREFER_SOURCE_A = "prefer_source_a"
    PREFER_SOURCE_B = "prefer_source_b"
    MERGE_ATTRIBUTES = "merge_attributes"
    FLAG_REAL_WORLD_CHANGE = "flag_real_world_change"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


@router.post("/run")
async def run_reconciliation():
    """Generate explainable recommendations from conflicts. Delegates to engines/reconciliation. Owner: M5."""
    conflict = build_conflict(47, "P102", "M458", "geometry", "medium")
    return [
        recommend_conflict(
            conflict,
            {"source_reliability": 95},
            {"source_reliability": 80},
            match_score=89,
        )
    ]


@router.get("")
async def list_recommendations():
    return await run_reconciliation()
