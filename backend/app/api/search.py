from fastapi import APIRouter, Depends, Query
from psycopg_pool import ConnectionPool

from app.deps import get_embedder, get_pool
from app.schemas import SearchHitOut
from app.services.search import hybrid_search

router = APIRouter()


@router.get("/search", response_model=list[SearchHitOut])
def search(
    q: str = Query(min_length=2, max_length=300),
    company: str | None = None,
    event_type: str | None = None,
    days: int | None = Query(None, ge=1, le=365),
    limit: int = Query(8, ge=1, le=25),
    pool: ConnectionPool = Depends(get_pool),
    embedder=Depends(get_embedder),
):
    return hybrid_search(
        pool, embedder, q, limit=limit, company=company, event_type=event_type, days=days
    )
