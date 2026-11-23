def test_companies_are_seeded(client):
    response = client.get("/companies")
    assert response.status_code == 200
    names = [company["name"] for company in response.json()]
    assert len(names) >= 8
    assert "Databricks" in names
    assert "Anthropic" in names


def test_companies_are_sorted_by_name(client):
    names = [company["name"] for company in client.get("/companies").json()]
    assert names == sorted(names)


def test_seeding_twice_does_not_duplicate(client):
    from app.main import app
    from app.seed import seed_companies

    before = len(client.get("/companies").json())
    seed_companies(app.state.pool)
    after = len(client.get("/companies").json())
    assert before == after
