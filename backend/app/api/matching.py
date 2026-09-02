from fastapi import APIRouter

router = APIRouter()


@router.post("/run")
async def run_matching():
    """Generate candidate matches. Delegates to engines/matching. Owner: M5."""
    return [
        {"feature_a": "P102", "feature_b": "M458", "score": 91, "status": "matched"}
    ]


@router.get("")
async def list_matches():
    return [
        {"feature_a": "P102", "feature_b": "M458", "score": 91, "status": "matched"}
    ]
