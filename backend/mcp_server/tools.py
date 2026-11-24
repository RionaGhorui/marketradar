from datetime import datetime

from psycopg_pool import ConnectionPool

from app.services.events import list_events
from app.services.events import weekly_briefing as build_briefing
from app.services.search import hybrid_search

SEARCH_FIELDS = ("company", "title", "summary", "event_type", "published_at", "url", "source")


def make_json_safe(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, dict):
        return {key: make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [make_json_safe(item) for item in value]
    return value


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


def search_news(pool: ConnectionPool, embedder, query: str, company=None, days=None, limit=5) -> list[dict]:
    hits = hybrid_search(pool, embedder, query, limit=clamp(limit, 1, 20), company=company, days=days)
    return [make_json_safe({field: hit[field] for field in SEARCH_FIELDS}) for hit in hits]


def get_competitor_events(pool: ConnectionPool, company: str, event_type=None, days=30, limit=10) -> list[dict]:
    rows = list_events(
        pool, company=company, event_type=event_type, days=clamp(days, 1, 365), limit=clamp(limit, 1, 50)
    )
    return [make_json_safe({field: row[field] for field in SEARCH_FIELDS}) for row in rows]


def weekly_briefing(pool: ConnectionPool, days=7) -> list[dict]:
    return make_json_safe(build_briefing(pool, days=clamp(days, 1, 90)))
