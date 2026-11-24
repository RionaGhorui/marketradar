from psycopg_pool import ConnectionPool

LIST_EVENTS_SQL = """
SELECT a.id, c.name AS company, a.title, a.url, a.source,
       a.published_at, a.event_type, a.summary
FROM articles a
JOIN tracked_companies c ON c.id = a.company_id
WHERE a.event_type <> 'irrelevant'
  AND (%(company)s::text IS NULL OR c.name = %(company)s)
  AND (%(event_type)s::text IS NULL OR a.event_type = %(event_type)s)
  AND (%(days)s::int IS NULL
       OR a.published_at >= now() - make_interval(days => %(days)s::int))
ORDER BY a.published_at DESC NULLS LAST
LIMIT %(limit)s
"""

BRIEFING_COUNTS_SQL = """
SELECT c.name AS company, a.event_type, COUNT(*) AS total
FROM articles a
JOIN tracked_companies c ON c.id = a.company_id
WHERE a.event_type <> 'irrelevant'
  AND a.published_at >= now() - make_interval(days => %(days)s)
GROUP BY c.name, a.event_type
"""

BRIEFING_HEADLINES_SQL = """
SELECT company, title, url, event_type, summary, published_at
FROM (
    SELECT c.name AS company, a.title, a.url, a.event_type, a.summary, a.published_at,
           ROW_NUMBER() OVER (PARTITION BY c.id ORDER BY a.published_at DESC) AS position
    FROM articles a
    JOIN tracked_companies c ON c.id = a.company_id
    WHERE a.event_type <> 'irrelevant'
      AND a.published_at >= now() - make_interval(days => %(days)s)
) ranked
WHERE position <= %(per_company)s
ORDER BY company, published_at DESC
"""


def list_events(
    pool: ConnectionPool,
    company: str | None = None,
    event_type: str | None = None,
    days: int | None = None,
    limit: int = 20,
) -> list[dict]:
    params = {"company": company, "event_type": event_type, "days": days, "limit": limit}
    with pool.connection() as conn:
        return conn.execute(LIST_EVENTS_SQL, params).fetchall()


def weekly_briefing(pool: ConnectionPool, days: int = 7, headlines_per_company: int = 3) -> list[dict]:
    with pool.connection() as conn:
        counts = conn.execute(BRIEFING_COUNTS_SQL, {"days": days}).fetchall()
        headlines = conn.execute(
            BRIEFING_HEADLINES_SQL, {"days": days, "per_company": headlines_per_company}
        ).fetchall()

    companies: dict[str, dict] = {}
    for row in counts:
        entry = companies.setdefault(
            row["company"], {"company": row["company"], "total": 0, "by_type": {}, "headlines": []}
        )
        entry["by_type"][row["event_type"]] = row["total"]
        entry["total"] += row["total"]

    for row in headlines:
        companies[row["company"]]["headlines"].append(
            {
                "title": row["title"],
                "url": row["url"],
                "event_type": row["event_type"],
                "summary": row["summary"],
                "published_at": row["published_at"],
            }
        )

    return sorted(companies.values(), key=lambda entry: entry["total"], reverse=True)
