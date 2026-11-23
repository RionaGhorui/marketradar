from fastapi import APIRouter, Depends, Query
from psycopg_pool import ConnectionPool

from app.deps import get_pool
from app.schemas import ArticleOut

router = APIRouter()

LATEST_ARTICLES = """
SELECT a.id, c.name AS company, a.title, a.url, a.source,
       a.published_at, a.event_type, a.summary
FROM articles a
JOIN tracked_companies c ON c.id = a.company_id
WHERE a.event_type <> 'irrelevant'
  AND (%(company)s::text IS NULL OR c.name = %(company)s)
ORDER BY a.published_at DESC NULLS LAST
LIMIT %(limit)s
"""


@router.get("/articles", response_model=list[ArticleOut])
def latest_articles(
    company: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    pool: ConnectionPool = Depends(get_pool),
):
    with pool.connection() as conn:
        rows = conn.execute(LATEST_ARTICLES, {"company": company, "limit": limit}).fetchall()
    return rows
