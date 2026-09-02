from fastapi import APIRouter

router = APIRouter()


@router.post("/detect")
async def detect_conflicts():
    """Run conflict detection on matches. Delegates to engines/matching. Owner: M5."""
    return [
        {"id": 47, "type": "geometry", "severity": "medium", "feature_a": "P102", "feature_b": "M458"}
    ]


@router.get("")
async def list_conflicts():
    return [
        {"id": 47, "type": "geometry", "severity": "medium", "feature_a": "P102", "feature_b": "M458"}
    ]
