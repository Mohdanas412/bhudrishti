from fastapi import APIRouter
from pydantic import BaseModel

from app.services.reconciliation_service import get_all_reviews, record_review

router = APIRouter()


class ReviewDecision(BaseModel):
    reviewer: str
    decision: str  # "accept" | "reject" | "edit"
    comment: str | None = None


@router.post("/{conflict_id}")
async def submit_review(conflict_id: int, decision: ReviewDecision):
    """Accept / reject / edit a recommendation. Writes to audit log. Owner: M3 + M6."""
    entry = record_review(
        conflict_id, decision.decision, decision.reviewer, decision.comment
    )
    return {
        "conflict_id": conflict_id,
        "decision": decision.decision,
        "status": "recorded",
        "entry": entry,
    }


@router.get("")
async def list_reviews():
    """List all recorded human review decisions from the audit trail."""
    return get_all_reviews()
