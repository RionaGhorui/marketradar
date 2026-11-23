import html
import re
from collections import Counter
from datetime import datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from etl.models import RawItem

TRACKING_PARAMS = {"fbclid", "gclid", "ref", "ref_src", "mc_cid", "mc_eid"}
MIN_TITLE_LENGTH = 15


def strip_html(text: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query)
        if not key.startswith("utm_") and key not in TRACKING_PARAMS
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def reject_reason(item: RawItem, now: datetime, lookback_days: int) -> str | None:
    if not item.title or not item.url:
        return "missing_fields"
    if not item.url.startswith(("http://", "https://")):
        return "bad_url"
    if len(item.title) < MIN_TITLE_LENGTH:
        return "title_too_short"
    if item.published_at is None:
        return "missing_date"
    if item.published_at < now - timedelta(days=lookback_days):
        return "too_old"
    if item.published_at > now + timedelta(days=1):
        return "future_date"
    return None


def clean_items(items: list[RawItem], now: datetime, lookback_days: int) -> tuple[list[RawItem], Counter]:
    stats: Counter = Counter()
    seen_urls: set[str] = set()
    seen_titles: set[tuple[str, str]] = set()
    kept: list[RawItem] = []

    for item in items:
        item.title = strip_html(item.title)
        item.text = strip_html(item.text)

        reason = reject_reason(item, now, lookback_days)
        if reason:
            stats[f"rejected_{reason}"] += 1
            continue

        item.url = normalize_url(item.url)
        title_key = (item.company, normalize_title(item.title))
        if item.url in seen_urls or title_key in seen_titles:
            stats["duplicates"] += 1
            continue

        seen_urls.add(item.url)
        seen_titles.add(title_key)
        kept.append(item)

    return kept, stats
