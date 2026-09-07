from enum import Enum

from fastapi import APIRouter

from app.engines.reconciliation import build_conflict, recommend_conflict

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


def _to_contract_shape(
    recommendation: dict, feature_a: dict | None, feature_b: dict | None
) -> dict:
    """
    Bridge layer: engines/reconciliation.recommend_conflict() (M5) returns
    'prefer_source_a' / 'prefer_source_b' to indicate WHICH side should be
    preferred, but the frozen public contract (docs/contracts/recommendation.json)
    only defines a single 'prefer_source' action plus a separate
    preferred_source_id field. This function translates between the two.

    TEMPORARY — flagged to M5 (rishi10-tech): ideally the engine itself would
    return 'prefer_source' + preferred_source_id directly, removing the need
    for this bridge. Not changed here since engines/reconciliation is M5's
    module, not M3's.
    """
    action = recommendation["action"]
    preferred_source_id = None

    if action == "prefer_source_a":
        action = RecommendationAction.PREFER_SOURCE.value
        preferred_source_id = (feature_a or {}).get("source_id")
    elif action == "prefer_source_b":
        action = RecommendationAction.PREFER_SOURCE.value
        preferred_source_id = (feature_b or {}).get("source_id")

    result = {
        "conflict_id": recommendation["conflict_id"],
        "action": action,
        "confidence": recommendation["confidence"],
        "reason": recommendation["reason"],
    }
    if preferred_source_id is not None:
        result["preferred_source_id"] = preferred_source_id

    return result


from app.db.session import get_db
from app.services.reconciliation_service import get_all_recommendations
from fastapi import Depends
from sqlalchemy.orm import Session


@router.post("/run")
async def run_reconciliation(db: Session = Depends(get_db)):
    """Generate explainable recommendations from conflicts. Delegates to engines/reconciliation. Owner: M5."""
    return get_all_recommendations(db)


@router.get("")
async def list_recommendations(db: Session = Depends(get_db)):
    """List recommendations for all detected conflicts."""
    return get_all_recommendations(db)

