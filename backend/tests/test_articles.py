def add_article(pool, company, title, url, event_type, minutes_ago):
    with pool.connection() as conn:
        company_id = conn.execute(
            "SELECT id FROM tracked_companies WHERE name = %s", (company,)
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO articles (url, title, source, published_at, company_id, event_type, summary) "
            "VALUES (%s, %s, 'Test', now() - make_interval(mins => %s), %s, %s, 'A summary')",
            (url, title, minutes_ago, company_id, event_type),
        )


def test_articles_endpoint_hides_irrelevant_and_sorts_newest_first(client, pool, empty_articles):
    add_article(pool, "Databricks", "Older Databricks story", "https://example.com/1", "funding", 120)
    add_article(pool, "Databricks", "Newest Databricks story", "https://example.com/2", "product_launch", 5)
    add_article(pool, "OpenAI", "Hidden irrelevant story", "https://example.com/3", "irrelevant", 1)

    articles = client.get("/articles").json()
    assert [a["title"] for a in articles] == ["Newest Databricks story", "Older Databricks story"]
    assert articles[0]["company"] == "Databricks"
    assert "embedding" not in articles[0]


def test_articles_endpoint_filters_by_company_and_limit(client, pool, empty_articles):
    add_article(pool, "Databricks", "Databricks story one", "https://example.com/1", "funding", 10)
    add_article(pool, "OpenAI", "OpenAI story one", "https://example.com/2", "funding", 20)
    add_article(pool, "OpenAI", "OpenAI story two", "https://example.com/3", "funding", 30)

    only_openai = client.get("/articles", params={"company": "OpenAI"}).json()
    assert {a["company"] for a in only_openai} == {"OpenAI"}
    assert len(client.get("/articles", params={"limit": 1}).json()) == 1
    assert client.get("/articles", params={"limit": 0}).status_code == 422
