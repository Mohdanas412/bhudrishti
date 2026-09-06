from fastapi import APIRouter

from app.engines.matching import match_features

router = APIRouter()


DEMO_FEATURE_A = {
    "id": "P102",
    "geometry": {"type": "Point", "coordinates": [0, 0]},
    "area": 100,
    "land_use": "Residential",
    "source_reliability": 90,
}
DEMO_FEATURE_B = {
    "id": "M458",
    "geometry": {"type": "Point", "coordinates": [0, 0]},
    "area": 100,
    "land_use": "Residential",
    "source_reliability": 90,
}


@router.post("/run")
async def run_matching():
    """Generate candidate matches. Delegates to engines/matching. Owner: M5."""
    return [match_features(DEMO_FEATURE_A, DEMO_FEATURE_B).to_contract()]


@router.get("")
async def list_matches():
    return [match_features(DEMO_FEATURE_A, DEMO_FEATURE_B).to_contract()]
