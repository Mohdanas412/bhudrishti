from fastapi import APIRouter

from app.engines.reconciliation import build_conflict

router = APIRouter()


@router.post("/detect")
async def detect_conflicts():
    """Run conflict detection on matches. Delegates to engines/matching. Owner: M5."""
    return [build_conflict(47, "P102", "M458", "geometry", "medium")]


@router.get("")
async def list_conflicts():
    return [build_conflict(47, "P102", "M458", "geometry", "medium")]
