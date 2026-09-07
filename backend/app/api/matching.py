from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.reconciliation_service import get_all_matches

router = APIRouter()


@router.post("/run")
async def run_matching(db: Session = Depends(get_db)):
    """Generate candidate matches from loaded features or canonical fixtures. Delegates to engines/matching. Owner: M5."""
    return get_all_matches(db)


@router.get("")
async def list_matches(db: Session = Depends(get_db)):
    """List pairwise match results with confidence scores and evidence breakdowns."""
    return get_all_matches(db)

