from app.services.search import hybrid_search
from tests.support import FakeEmbedder, add_article


def test_hybrid_search_combines_meaning_and_keywords(pool, empty_articles):
    add_article(pool, "Databricks", "Quarterly results overview", "https://example.com/a", vector_index=0)
    add_article(pool, "Databricks", "Databricks announces funding round", "https://example.com/b", vector_index=1)
    add_article(pool, "Databricks", "Unrelated hiring news", "https://example.com/c", event_type="hiring", vector_index=2)

    hits = hybrid_search(pool, FakeEmbedder(0), "funding")

    titles = [hit["title"] for hit in hits]
    assert titles[0] == "Databricks announces funding round"
    assert "Quarterly results overview" in titles[:2]
    assert hits[0]["score"] > hits[-1]["score"]


def test_keyword_match_works_without_an_embedding(pool, empty_articles):
    add_article(pool, "OpenAI", "Zebracorn partnership signed", "https://example.com/a")
    hits = hybrid_search(pool, FakeEmbedder(0), "zebracorn")
    assert [hit["title"] for hit in hits] == ["Zebracorn partnership signed"]


def test_irrelevant_articles_never_appear(pool, empty_articles):
    add_article(pool, "OpenAI", "Funding story hidden", "https://example.com/a", event_type="irrelevant", vector_index=0)
    assert hybrid_search(pool, FakeEmbedder(0), "funding") == []


def test_filters_narrow_the_results(pool, empty_articles):
    add_article(pool, "Databricks", "Databricks funding news", "https://example.com/a", "funding", 10, vector_index=0)
    add_article(pool, "OpenAI", "OpenAI funding news", "https://example.com/b", "funding", 10, vector_index=1)
    add_article(pool, "OpenAI", "OpenAI launches funding tool", "https://example.com/c", "product_launch", 10, vector_index=2)
    add_article(pool, "OpenAI", "OpenAI old funding news", "https://example.com/d", "funding", 60 * 24 * 40, vector_index=3)
    embedder = FakeEmbedder(0)

    by_company = hybrid_search(pool, embedder, "funding", company="OpenAI")
    assert {hit["company"] for hit in by_company} == {"OpenAI"}

    by_type = hybrid_search(pool, embedder, "funding", event_type="product_launch")
    assert [hit["title"] for hit in by_type] == ["OpenAI launches funding tool"]

    recent = hybrid_search(pool, embedder, "funding", days=7)
    assert "OpenAI old funding news" not in [hit["title"] for hit in recent]


def test_limit_and_empty_query(pool, empty_articles):
    for number in range(5):
        add_article(pool, "OpenAI", f"OpenAI funding story {number}", f"https://example.com/{number}", vector_index=number)
    assert len(hybrid_search(pool, FakeEmbedder(0), "funding", limit=2)) == 2
    assert hybrid_search(pool, FakeEmbedder(0), "   ") == []


def test_search_endpoint(client, pool, empty_articles):
    from app.deps import get_embedder
    from app.main import app

    add_article(pool, "Databricks", "Databricks funding news", "https://example.com/a", vector_index=0)
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder(0)
    try:
        response = client.get("/search", params={"q": "funding", "company": "Databricks"})
        too_short = client.get("/search", params={"q": "a"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body[0]["title"] == "Databricks funding news"
    assert body[0]["score"] > 0
    assert too_short.status_code == 422
