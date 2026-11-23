import os
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

DEFAULT_URL = "postgresql://marketradar:marketradar@localhost:5433/marketradar"
TEST_DATABASE = "marketradar_test"


def prepare_test_database() -> str:
    base = urlsplit(os.environ.get("DATABASE_URL", DEFAULT_URL))
    admin_url = urlunsplit(base._replace(path="/postgres"))
    test_url = urlunsplit(base._replace(path=f"/{TEST_DATABASE}"))
    with psycopg.connect(admin_url, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DATABASE,)
        ).fetchone()
        if not exists:
            conn.execute(f"CREATE DATABASE {TEST_DATABASE}")
    return test_url


os.environ["DATABASE_URL"] = prepare_test_database()

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def pool(client):
    return client.app.state.pool


@pytest.fixture
def empty_articles(pool):
    with pool.connection() as conn:
        conn.execute("DELETE FROM articles")
    yield
    with pool.connection() as conn:
        conn.execute("DELETE FROM articles")
