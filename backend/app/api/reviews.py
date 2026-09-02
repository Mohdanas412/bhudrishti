from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ReviewDecision(BaseModel):
    reviewer: str
    decision: str  # "accept" | "reject" | "edit"
    comment: str | None = None


@router.post("/{conflict_id}")
async def submit_review(conflict_id: int, decision: ReviewDecision):
    """Accept / reject / edit a recommendation. Writes to audit log. Owner: M3 + M6."""
    return {"conflict_id": conflict_id, "decision": decision.decision, "status": "recorded"}
