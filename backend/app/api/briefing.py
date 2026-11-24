from fastapi import APIRouter, Depends, Query
from psycopg_pool import ConnectionPool

from app.deps import get_pool
from app.schemas import BriefingCompanyOut
from app.services.events import weekly_briefing

router = APIRouter()


@router.get("/briefing", response_model=list[BriefingCompanyOut])
def briefing(
    days: int = Query(7, ge=1, le=90),
    pool: ConnectionPool = Depends(get_pool),
):
    return weekly_briefing(pool, days=days)
