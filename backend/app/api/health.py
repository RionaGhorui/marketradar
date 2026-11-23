from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from psycopg_pool import ConnectionPool

from app.deps import get_pool

router = APIRouter()


@router.get("/health")
def health(pool: ConnectionPool = Depends(get_pool)):
    try:
        with pool.connection() as conn:
            conn.execute("SELECT 1")
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "down"},
        )
    return {"status": "ok", "database": "up"}
