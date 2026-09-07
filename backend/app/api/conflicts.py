from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.reconciliation_service import get_all_conflicts

router = APIRouter()


@router.post("/detect")
async def detect_conflicts_route(db: Session = Depends(get_db)):
    """Run conflict detection on matches. Delegates to engines/reconciliation. Owner: M5."""
    return get_all_conflicts(db)


@router.get("")
async def list_conflicts(db: Session = Depends(get_db)):
    """List detected discrepancies across matched and candidate features."""
    return get_all_conflicts(db)

