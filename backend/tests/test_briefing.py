from tests.support import add_article


def test_briefing_groups_counts_and_headlines_by_company(client, pool, empty_articles):
    add_article(pool, "Databricks", "Databricks funding one", "https://example.com/1", "funding", 10)
    add_article(pool, "Databricks", "Databricks launch two", "https://example.com/2", "product_launch", 20)
    add_article(pool, "OpenAI", "OpenAI launch three", "https://example.com/3", "product_launch", 30)
    add_article(pool, "OpenAI", "OpenAI too old", "https://example.com/4", "funding", 60 * 24 * 20)
    add_article(pool, "OpenAI", "OpenAI irrelevant", "https://example.com/5", "irrelevant", 5)

    response = client.get("/briefing", params={"days": 7})

    assert response.status_code == 200
    body = response.json()
    assert [entry["company"] for entry in body] == ["Databricks", "OpenAI"]
    assert body[0]["total"] == 2
    assert body[0]["by_type"] == {"funding": 1, "product_launch": 1}
    assert body[0]["headlines"][0]["title"] == "Databricks funding one"
    assert body[1]["total"] == 1


def test_briefing_is_empty_when_nothing_happened(client, empty_articles):
    assert client.get("/briefing").json() == []
