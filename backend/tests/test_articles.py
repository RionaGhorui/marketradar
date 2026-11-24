from tests.support import add_article


def test_articles_endpoint_hides_irrelevant_and_sorts_newest_first(client, pool, empty_articles):
    add_article(pool, "Databricks", "Older Databricks story", "https://example.com/1", minutes_ago=120)
    add_article(pool, "Databricks", "Newest Databricks story", "https://example.com/2", "product_launch", 5)
    add_article(pool, "OpenAI", "Hidden irrelevant story", "https://example.com/3", "irrelevant", 1)

    articles = client.get("/articles").json()
    assert [a["title"] for a in articles] == ["Newest Databricks story", "Older Databricks story"]
    assert articles[0]["company"] == "Databricks"
    assert "embedding" not in articles[0]


def test_articles_endpoint_filters_by_company_type_days_and_limit(client, pool, empty_articles):
    add_article(pool, "Databricks", "Databricks story one", "https://example.com/1", "funding", 10)
    add_article(pool, "OpenAI", "OpenAI story one", "https://example.com/2", "product_launch", 20)
    add_article(pool, "OpenAI", "OpenAI old story", "https://example.com/3", "funding", 60 * 24 * 40)

    only_openai = client.get("/articles", params={"company": "OpenAI"}).json()
    assert {a["company"] for a in only_openai} == {"OpenAI"}

    launches = client.get("/articles", params={"event_type": "product_launch"}).json()
    assert [a["title"] for a in launches] == ["OpenAI story one"]

    recent = client.get("/articles", params={"days": 7}).json()
    assert "OpenAI old story" not in [a["title"] for a in recent]

    assert len(client.get("/articles", params={"limit": 1}).json()) == 1
    assert client.get("/articles", params={"limit": 0}).status_code == 422
