from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_harmonized():
    """Final unified dataset as GeoJSON, traceable to source_feature_ids. Owner: M3 + M6."""
    return {
        "type": "FeatureCollection",
        "features": [],
    }
