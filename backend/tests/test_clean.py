from datetime import datetime, timedelta, timezone

from etl.clean import clean_items, normalize_title, normalize_url, reject_reason, strip_html
from etl.models import RawItem

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)


def make_item(title="Databricks announces a new product", url="https://example.com/post", days_old=1, company="Databricks"):
    return RawItem(
        company=company,
        source="Test",
        title=title,
        url=url,
        published_at=NOW - timedelta(days=days_old),
        text="",
    )


def test_strip_html_removes_tags_and_entities():
    assert strip_html("<a href='x'>Big&nbsp;news</a> <b>today</b>") == "Big news today"


def test_normalize_url_drops_tracking_and_trailing_slash():
    url = "HTTPS://Example.com/news/?utm_source=x&id=7&fbclid=abc#top"
    assert normalize_url(url) == "https://example.com/news?id=7"


def test_normalize_title_ignores_case_and_punctuation():
    assert normalize_title("Databricks, Raises $1B!") == normalize_title("databricks raises 1b")


def test_reject_reasons():
    assert reject_reason(make_item(title=""), NOW, 14) == "missing_fields"
    assert reject_reason(make_item(url="ftp://x"), NOW, 14) == "bad_url"
    assert reject_reason(make_item(title="Too short"), NOW, 14) == "title_too_short"
    assert reject_reason(make_item(days_old=30), NOW, 14) == "too_old"
    assert reject_reason(make_item(days_old=-5), NOW, 14) == "future_date"
    assert reject_reason(make_item(), NOW, 14) is None

    undated = make_item()
    undated.published_at = None
    assert reject_reason(undated, NOW, 14) == "missing_date"


def test_clean_items_removes_duplicates_and_bad_records():
    items = [
        make_item(url="https://example.com/a"),
        make_item(url="https://example.com/a/?utm_source=mail"),
        make_item(title="Databricks Announces a NEW product!", url="https://other.com/b"),
        make_item(title="Old story from last month", url="https://example.com/c", days_old=40),
        make_item(title="Snowflake ships a different thing", url="https://example.com/d", company="Snowflake"),
    ]
    kept, stats = clean_items(items, NOW, 14)
    assert [item.url for item in kept] == ["https://example.com/a", "https://example.com/d"]
    assert stats["duplicates"] == 2
    assert stats["rejected_too_old"] == 1
