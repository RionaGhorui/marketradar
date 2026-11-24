from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.rag.chain import NO_RESULTS_ANSWER, build_chain, cited_sources, format_documents


def make_document(number: int) -> Document:
    return Document(
        page_content=f"Story {number} headline\nStory {number} summary",
        metadata={
            "id": number,
            "company": "Databricks",
            "url": f"https://example.com/{number}",
            "source": "Test",
            "event_type": "funding",
            "published_at": "2026-11-20",
            "score": 0.1,
        },
    )


class StubRetriever:
    def __init__(self, documents):
        self.documents = documents
        self.questions = []

    def invoke(self, question):
        self.questions.append(question)
        return self.documents


def fake_llm(*replies):
    return GenericFakeChatModel(messages=iter([AIMessage(content=reply) for reply in replies]))


def test_chain_answers_from_retrieved_documents():
    retriever = StubRetriever([make_document(1), make_document(2)])
    chain = build_chain(retriever, fake_llm("  Databricks raised money [1].  "))

    result = chain.invoke("Who raised money?")

    assert result["answer"] == "Databricks raised money [1]."
    assert len(result["documents"]) == 2
    assert retriever.questions == ["Who raised money?"]


def test_chain_skips_the_model_when_nothing_is_found():
    chain = build_chain(StubRetriever([]), fake_llm())
    result = chain.invoke("Anything?")
    assert result == {"answer": NO_RESULTS_ANSWER, "documents": []}


def test_format_documents_numbers_every_article():
    text = format_documents([make_document(1), make_document(2)])
    assert text.startswith("[1] Databricks | funding | 2026-11-20")
    assert "[2] Databricks | funding | 2026-11-20" in text
    assert "Story 2 summary" in text


def test_cited_sources_keeps_only_cited_numbers():
    documents = [make_document(1), make_document(2), make_document(3)]
    sources = cited_sources("Both happened [3] and [1].", documents)
    assert [source["number"] for source in sources] == [1, 3]
    assert sources[0]["url"] == "https://example.com/1"
    assert sources[0]["title"] == "Story 1 headline"


def test_cited_sources_falls_back_to_all_when_nothing_valid_is_cited():
    documents = [make_document(1), make_document(2)]
    assert [s["number"] for s in cited_sources("No citations here.", documents)] == [1, 2]
    assert [s["number"] for s in cited_sources("Bad citation [9].", documents)] == [1, 2]
