from fastapi import APIRouter, Depends
from psycopg_pool import ConnectionPool

from app.deps import get_pool
from app.schemas import CompanyOut

router = APIRouter()


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(pool: ConnectionPool = Depends(get_pool)):
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT id, name, website FROM tracked_companies ORDER BY name"
        ).fetchall()
    return rows
