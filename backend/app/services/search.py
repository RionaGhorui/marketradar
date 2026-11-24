from psycopg_pool import ConnectionPool

from app.embeddings import vector_literal

CANDIDATES = 30

FILTERS = """
      AND {prefix}event_type <> 'irrelevant'
      AND (%(company)s::text IS NULL
           OR {prefix}company_id = (SELECT id FROM tracked_companies WHERE name = %(company)s))
      AND (%(event_type)s::text IS NULL OR {prefix}event_type = %(event_type)s)
      AND (%(days)s::int IS NULL
           OR {prefix}published_at >= now() - make_interval(days => %(days)s::int))
"""

HYBRID_SQL = (
    """
WITH vector_hits AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> %(embedding)s::vector) AS position
    FROM articles
    WHERE embedding IS NOT NULL
"""
    + FILTERS.format(prefix="")
    + """
    ORDER BY embedding <=> %(embedding)s::vector
    LIMIT %(candidates)s
),
keyword_hits AS (
    SELECT a.id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(a.search_vector, q.query) DESC) AS position
    FROM articles a, websearch_to_tsquery('english', %(query)s) AS q(query)
    WHERE a.search_vector @@ q.query
"""
    + FILTERS.format(prefix="a.")
    + """
    ORDER BY ts_rank_cd(a.search_vector, q.query) DESC
    LIMIT %(candidates)s
),
fused AS (
    SELECT id, SUM(1.0 / (60 + position)) AS score
    FROM (
        SELECT id, position FROM vector_hits
        UNION ALL
        SELECT id, position FROM keyword_hits
    ) ranked
    GROUP BY id
)
SELECT a.id, c.name AS company, a.title, a.url, a.source, a.published_at,
       a.event_type, a.summary, f.score::float8 AS score
FROM fused f
JOIN articles a ON a.id = f.id
JOIN tracked_companies c ON c.id = a.company_id
ORDER BY f.score DESC, a.published_at DESC NULLS LAST
LIMIT %(limit)s
"""
)


def hybrid_search(
    pool: ConnectionPool,
    embedder,
    query: str,
    limit: int = 8,
    company: str | None = None,
    event_type: str | None = None,
    days: int | None = None,
) -> list[dict]:
    query = query.strip()
    if not query:
        return []
    params = {
        "embedding": vector_literal(embedder.embed([query])[0]),
        "query": query,
        "company": company,
        "event_type": event_type,
        "days": days,
        "candidates": CANDIDATES,
        "limit": limit,
    }
    with pool.connection() as conn:
        return conn.execute(HYBRID_SQL, params).fetchall()
