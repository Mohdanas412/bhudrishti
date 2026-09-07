from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.reconciliation_service import get_harmonized_feature_collection

router = APIRouter()


@router.get("")
async def get_harmonized(db: Session = Depends(get_db)):
    """Final unified dataset as GeoJSON, traceable to source_feature_ids. Owner: M3 + M6."""
    return get_harmonized_feature_collection(db)

