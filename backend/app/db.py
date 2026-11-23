from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def create_pool(url: str) -> ConnectionPool:
    pool = ConnectionPool(
        url,
        min_size=1,
        max_size=5,
        kwargs={"row_factory": dict_row},
        open=False,
    )
    pool.open(wait=True, timeout=30)
    return pool


def apply_schema(pool: ConnectionPool) -> None:
    schema = SCHEMA_FILE.read_text()
    with pool.connection() as conn:
        conn.execute(schema)
