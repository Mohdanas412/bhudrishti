from enum import Enum
from fastapi import APIRouter

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
    return [
        {
            "conflict_id": 47,
            "action": RecommendationAction.PREFER_SOURCE_A.value,
            "confidence": 89,
            "reason": "Higher source authority and stronger geometric evidence",
        }
    ]


@router.get("")
async def list_recommendations():
    return [
        {
            "conflict_id": 47,
            "action": RecommendationAction.PREFER_SOURCE_A.value,
            "confidence": 89,
            "reason": "Higher source authority and stronger geometric evidence",
        }
    ]
