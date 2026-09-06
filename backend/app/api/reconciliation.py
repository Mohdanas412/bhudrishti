from enum import Enum

from fastapi import APIRouter

router = APIRouter()


class RecommendationAction(str, Enum):
    """
    Closed set of recommendation actions. Frozen per Addendum v1 (Critical Fix 3),
    alongside docs/contracts/recommendation.json —
    do not add a value here without updating that file and notifying M1/M2/M5.
    """

    PREFER_SOURCE = (
        "prefer_source"  # include preferred_source_id (sources.id) when used
    )
    MERGE_ATTRIBUTES = "merge_attributes"
    FLAG_REAL_WORLD_CHANGE = "flag_real_world_change"
    FLAG_DUPLICATE = "flag_duplicate"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    NO_ACTION_NEEDED = "no_action_needed"


@router.post("/run")
async def run_reconciliation():
    """Generate explainable recommendations from conflicts. Delegates to engines/reconciliation. Owner: M5."""
    return [
        {
            "conflict_id": 47,
            "action": RecommendationAction.PREFER_SOURCE.value,
            "preferred_source_id": 1,
            "confidence": 89,
            "reason": "Higher source authority and stronger geometric evidence",
        }
    ]


@router.get("")
async def list_recommendations():
    return [
        {
            "conflict_id": 47,
            "action": RecommendationAction.PREFER_SOURCE.value,
            "preferred_source_id": 1,
            "confidence": 89,
            "reason": "Higher source authority and stronger geometric evidence",
        }
    ]
