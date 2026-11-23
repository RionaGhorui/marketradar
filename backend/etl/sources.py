import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import feedparser
import httpx

from etl.clean import strip_html
from etl.models import RawItem

log = logging.getLogger(__name__)

GOOGLE_NEWS_URL = "https://news.google.com/rss/search?q={query}+when:7d&hl=en-US&gl=US&ceid=US:en"
HACKER_NEWS_URL = "https://hn.algolia.com/api/v1/search_by_date"
MIN_HN_POINTS = 5
MAX_TEXT_LENGTH = 1500


def entry_date(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc)


def parse_google_news(company: str, content: bytes) -> list[RawItem]:
    items = []
    for entry in feedparser.parse(content).entries:
        title = strip_html(entry.get("title", ""))
        publisher = entry.get("source", {}).get("title", "")
        suffix = f" - {publisher}"
        if publisher and title.endswith(suffix):
            title = title[: -len(suffix)].strip()
        source = f"Google News ({publisher})" if publisher else "Google News"
        items.append(
            RawItem(
                company=company,
                source=source,
                title=title,
                url=entry.get("link", ""),
                published_at=entry_date(entry),
                text=title,
            )
        )
    return items


def parse_blog_feed(company: str, source: str, content: bytes) -> list[RawItem]:
    items = []
    for entry in feedparser.parse(content).entries:
        summary = strip_html(entry.get("summary", ""))[:MAX_TEXT_LENGTH]
        items.append(
            RawItem(
                company=company,
                source=source,
                title=strip_html(entry.get("title", "")),
                url=entry.get("link", ""),
                published_at=entry_date(entry),
                text=summary,
            )
        )
    return items


def parse_hacker_news(company: str, payload: dict) -> list[RawItem]:
    items = []
    for hit in payload.get("hits", []):
        if (hit.get("points") or 0) < MIN_HN_POINTS:
            continue
        created = hit.get("created_at_i")
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        items.append(
            RawItem(
                company=company,
                source="Hacker News",
                title=hit.get("title") or "",
                url=url,
                published_at=datetime.fromtimestamp(created, tz=timezone.utc) if created else None,
                text=strip_html(hit.get("story_text") or "")[:MAX_TEXT_LENGTH],
            )
        )
    return items


def fetch_google_news(client: httpx.Client, company: dict) -> list[RawItem]:
    response = client.get(GOOGLE_NEWS_URL.format(query=quote_plus(company["news_query"])))
    response.raise_for_status()
    return parse_google_news(company["name"], response.content)


def fetch_blog_feed(client: httpx.Client, company: dict) -> list[RawItem]:
    response = client.get(company["blog_feed"])
    response.raise_for_status()
    return parse_blog_feed(company["name"], f"{company['name']} blog", response.content)


def fetch_hacker_news(client: httpx.Client, company: dict, lookback_days: int) -> list[RawItem]:
    since = int((datetime.now(timezone.utc) - timedelta(days=lookback_days)).timestamp())
    params = {
        "query": company["name"],
        "tags": "story",
        "numericFilters": f"created_at_i>{since}",
        "hitsPerPage": 30,
    }
    response = client.get(HACKER_NEWS_URL, params=params)
    response.raise_for_status()
    return parse_hacker_news(company["name"], response.json())


def fetch_all(client: httpx.Client, companies: list[dict], lookback_days: int) -> tuple[list[RawItem], int]:
    items: list[RawItem] = []
    failures = 0

    for company in companies:
        jobs = [
            ("google news", fetch_google_news, (client, company)),
            ("hacker news", fetch_hacker_news, (client, company, lookback_days)),
        ]
        if company.get("blog_feed"):
            jobs.append(("blog feed", fetch_blog_feed, (client, company)))

        for label, fetch, args in jobs:
            try:
                found = fetch(*args)
            except (httpx.HTTPError, ValueError) as error:
                failures += 1
                log.warning("%s failed for %s: %s", label, company["name"], error)
                continue
            log.info("%s: %d items for %s", label, len(found), company["name"])
            items.extend(found)

    return items, failures
