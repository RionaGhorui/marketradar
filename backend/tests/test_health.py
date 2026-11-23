from app.deps import get_pool
from app.main import app


class BrokenPool:
    def connection(self):
        raise RuntimeError("database is unreachable")


def test_health_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


def test_health_reports_database_down(client):
    app.dependency_overrides[get_pool] = lambda: BrokenPool()
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["database"] == "down"
