import httpx
import openai
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.deps import get_embedder, get_llm
from app.main import app
from tests.support import FakeEmbedder, add_article


def call_ask(client, llm, body):
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder(0)
    app.dependency_overrides[get_llm] = lambda: llm
    try:
        return client.post("/ask", json=body)
    finally:
        app.dependency_overrides.clear()


def test_ask_returns_answer_with_cited_sources(client, pool, empty_articles):
    add_article(pool, "Databricks", "Databricks raises funding", "https://example.com/a", summary="Raised money.", vector_index=0)
    add_article(pool, "OpenAI", "OpenAI funding rumour", "https://example.com/b", vector_index=1)
    llm = GenericFakeChatModel(messages=iter([AIMessage(content="Databricks raised money [1].")]))

    response = call_ask(client, llm, {"question": "Who raised funding?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Databricks raised money [1]."
    assert len(body["sources"]) == 1
    assert body["sources"][0]["number"] == 1
    assert body["sources"][0]["url"] == "https://example.com/a"
    assert body["sources"][0]["company"] == "Databricks"


def test_ask_with_no_matching_articles_does_not_call_the_model(client, pool, empty_articles):
    llm = GenericFakeChatModel(messages=iter([]))
    response = call_ask(client, llm, {"question": "Anything about zebras?"})
    assert response.status_code == 200
    assert response.json()["sources"] == []
    assert "could not find" in response.json()["answer"]


def test_ask_without_a_configured_model_returns_503(client, pool, empty_articles):
    response = call_ask(client, None, {"question": "Who raised funding?"})
    assert response.status_code == 503


def test_ask_maps_provider_rate_limits_to_429(client, pool, empty_articles):
    add_article(pool, "Databricks", "Databricks raises funding", "https://example.com/a", vector_index=0)
    request = httpx.Request("POST", "https://example.test/v1/chat/completions")

    def explode(_):
        raise openai.RateLimitError("slow down", response=httpx.Response(429, request=request), body=None)

    response = call_ask(client, RunnableLambda(explode), {"question": "Who raised funding?"})
    assert response.status_code == 429


def test_ask_validates_the_question(client):
    response = call_ask(client, None, {"question": "hi"})
    assert response.status_code == 422
