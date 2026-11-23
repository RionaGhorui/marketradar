from datetime import datetime, timedelta, timezone

from etl.models import RawItem, Tag
from etl.pipeline import Pipeline

NOW = datetime.now(timezone.utc)


def make_item(title, url, company="Databricks", days_old=1):
    return RawItem(
        company=company,
        source="Test feed",
        title=title,
        url=url,
        published_at=NOW - timedelta(days=days_old),
        text="",
    )


class FakeTagger:
    def tag(self, item):
        if "unreliable" in item.title:
            return None
        if "irrelevant" in item.title:
            return Tag("irrelevant", "Not about the company.")
        return Tag("funding", f"Summary of {item.title}")


class FakeEmbedder:
    def embed(self, texts):
        return [[0.1] * 384 for _ in texts]


class FakeStore:
    def __init__(self):
        self.saved = []

    def save(self, items, run_time):
        self.saved.append(len(items))
        return "memory"


def build_pipeline(pool, items, max_new=15):
    return Pipeline(
        pool=pool,
        fetch=lambda companies: (list(items), 0),
        tagger=FakeTagger(),
        embedder=FakeEmbedder(),
        raw_store=FakeStore(),
        lookback_days=14,
        max_new_per_company=max_new,
    )


def stored_rows(pool):
    with pool.connection() as conn:
        return conn.execute(
            "SELECT title, event_type, summary, embedding IS NOT NULL AS has_embedding "
            "FROM articles ORDER BY title"
        ).fetchall()


def test_pipeline_stores_tagged_and_embedded_articles(pool, empty_articles):
    items = [
        make_item("Databricks raises a big funding round", "https://example.com/a"),
        make_item("OpenAI launches a brand new model", "https://example.com/b", company="OpenAI"),
    ]
    stats = build_pipeline(pool, items).run()

    assert stats["loaded"] == 2
    rows = stored_rows(pool)
    assert [row["event_type"] for row in rows] == ["funding", "funding"]
    assert all(row["has_embedding"] for row in rows)
    assert rows[0]["summary"].startswith("Summary of")


def test_second_run_adds_nothing_new(pool, empty_articles):
    items = [make_item("Databricks raises a big funding round", "https://example.com/a")]
    build_pipeline(pool, items).run()
    stats = build_pipeline(pool, items).run()

    assert stats["loaded"] == 0
    assert stats["already_in_database"] == 1
    assert len(stored_rows(pool)) == 1


def test_bad_and_duplicate_records_are_dropped(pool, empty_articles):
    items = [
        make_item("Databricks raises a big funding round", "https://example.com/a"),
        make_item("Databricks raises a big funding round", "https://example.com/a?utm_source=x"),
        make_item("Short", "https://example.com/b"),
        make_item("An old story from long ago", "https://example.com/c", days_old=60),
    ]
    stats = build_pipeline(pool, items).run()

    assert stats["loaded"] == 1
    assert stats["duplicates"] == 1
    assert stats["rejected_title_too_short"] == 1
    assert stats["rejected_too_old"] == 1


def test_irrelevant_items_are_stored_without_embedding(pool, empty_articles):
    items = [make_item("Something irrelevant about a cooperative", "https://example.com/a")]
    stats = build_pipeline(pool, items).run()

    assert stats["irrelevant"] == 1
    rows = stored_rows(pool)
    assert rows[0]["event_type"] == "irrelevant"
    assert rows[0]["has_embedding"] is False


def test_failed_tagging_is_not_stored_so_next_run_retries(pool, empty_articles):
    items = [make_item("This one is unreliable to tag", "https://example.com/a")]
    stats = build_pipeline(pool, items).run()

    assert stats["tag_failed"] == 1
    assert stored_rows(pool) == []


def test_per_company_cap_keeps_the_newest(pool, empty_articles):
    items = [
        make_item("Databricks story number one here", "https://example.com/1", days_old=1),
        make_item("Databricks story number two here", "https://example.com/2", days_old=2),
        make_item("Databricks story number three here", "https://example.com/3", days_old=3),
    ]
    stats = build_pipeline(pool, items, max_new=2).run()

    assert stats["loaded"] == 2
    assert stats["skipped_over_cap"] == 1
    titles = [row["title"] for row in stored_rows(pool)]
    assert "Databricks story number three here" not in titles


class AlwaysFailingTagger:
    def tag(self, item):
        return None


def test_pipeline_stops_early_when_the_model_keeps_failing(pool, empty_articles):
    items = [
        make_item(f"Databricks story number {number} here", f"https://example.com/{number}", days_old=number)
        for number in range(1, 9)
    ]
    pipeline = Pipeline(
        pool=pool,
        fetch=lambda companies: (list(items), 0),
        tagger=AlwaysFailingTagger(),
        embedder=FakeEmbedder(),
        raw_store=FakeStore(),
        lookback_days=14,
        max_new_per_company=10,
    )
    stats = pipeline.run()

    assert stats["tag_failed"] == 5
    assert stats["stopped_early"] == 1
    assert stored_rows(pool) == []
