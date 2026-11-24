from app.rag.retriever import HybridRetriever
from tests.support import FakeEmbedder, add_article


def test_retriever_returns_documents_with_source_metadata(pool, empty_articles):
    add_article(pool, "Databricks", "Databricks funding news", "https://example.com/a", summary="Raised money.", vector_index=0)
    add_article(pool, "OpenAI", "OpenAI funding news", "https://example.com/b", vector_index=1)

    retriever = HybridRetriever(pool=pool, embedder=FakeEmbedder(0), k=2)
    documents = retriever.invoke("funding")

    assert len(documents) == 2
    first = documents[0]
    assert "Databricks funding news" in first.page_content
    assert "Raised money." in first.page_content
    assert first.metadata["url"] == "https://example.com/a"
    assert first.metadata["company"] == "Databricks"
    assert first.metadata["event_type"] == "funding"
    assert len(first.metadata["published_at"]) == 10


def test_retriever_respects_company_filter(pool, empty_articles):
    add_article(pool, "Databricks", "Databricks funding news", "https://example.com/a", vector_index=0)
    add_article(pool, "OpenAI", "OpenAI funding news", "https://example.com/b", vector_index=1)

    retriever = HybridRetriever(pool=pool, embedder=FakeEmbedder(0), company="OpenAI")
    assert [d.metadata["company"] for d in retriever.invoke("funding")] == ["OpenAI"]
