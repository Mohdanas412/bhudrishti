from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.reconciliation_service import get_all_reviews, record_review

router = APIRouter()


class ReviewDecision(BaseModel):
    reviewer: str = Field("Cadastral Officer", description="Name or role of the reviewer")
    decision: str = Field(..., description="'APPROVED', 'REJECTED', 'FLAGGED', 'accept', 'reject', 'edit'")
    comment: str | None = Field(None, description="Optional audit notes or rationale")


@router.post("/{conflict_id}")
async def submit_review(conflict_id: int, decision: ReviewDecision):
    """Accept, reject, or flag a conflict recommendation and persist to the certified audit trail."""
    entry = record_review(
        conflict_id, decision.decision, decision.reviewer, decision.comment
    )
    return {
        "conflict_id": conflict_id,
        "decision": entry["decision"],
        "status": "recorded",
        "entry": entry,
    }


@router.get("")
async def list_reviews():
    """List all recorded human review decisions from the audit trail."""
    return get_all_reviews()
