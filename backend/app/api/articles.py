from fastapi import APIRouter, Depends, Query
from psycopg_pool import ConnectionPool

from app.deps import get_pool
from app.schemas import ArticleOut
from app.services.events import list_events

router = APIRouter()


@router.get("/articles", response_model=list[ArticleOut])
def latest_articles(
    company: str | None = None,
    event_type: str | None = None,
    days: int | None = Query(None, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    pool: ConnectionPool = Depends(get_pool),
):
    return list_events(pool, company=company, event_type=event_type, days=days, limit=limit)
