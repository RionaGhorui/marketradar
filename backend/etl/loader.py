from psycopg_pool import ConnectionPool

from app.embeddings import vector_literal

INSERT_ARTICLE = """
INSERT INTO articles
    (url, title, source, published_at, content, company_id, event_type, summary, embedding)
VALUES
    (%(url)s, %(title)s, %(source)s, %(published_at)s, %(content)s,
     %(company_id)s, %(event_type)s, %(summary)s, %(embedding)s::vector)
ON CONFLICT (url) DO NOTHING
"""


def load_companies(pool: ConnectionPool) -> list[dict]:
    with pool.connection() as conn:
        return conn.execute(
            "SELECT id, name, news_query, blog_feed FROM tracked_companies ORDER BY id"
        ).fetchall()


def find_existing_urls(pool: ConnectionPool, urls: list[str]) -> set[str]:
    if not urls:
        return set()
    with pool.connection() as conn:
        rows = conn.execute("SELECT url FROM articles WHERE url = ANY(%s)", (urls,)).fetchall()
    return {row["url"] for row in rows}


def insert_articles(pool: ConnectionPool, rows: list[dict]) -> int:
    inserted = 0
    with pool.connection() as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(INSERT_ARTICLE, {**row, "embedding": vector_literal(row["embedding"])})
                inserted += cur.rowcount
    return inserted
