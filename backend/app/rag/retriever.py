from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from app.services.search import hybrid_search


def hit_to_document(hit: dict) -> Document:
    published = hit["published_at"].date().isoformat() if hit["published_at"] else None
    return Document(
        page_content=f"{hit['title']}\n{hit['summary'] or ''}".strip(),
        metadata={
            "id": hit["id"],
            "company": hit["company"],
            "url": hit["url"],
            "source": hit["source"],
            "event_type": hit["event_type"],
            "published_at": published,
            "score": hit["score"],
        },
    )


class HybridRetriever(BaseRetriever):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    pool: Any
    embedder: Any
    k: int = 6
    company: str | None = None
    event_type: str | None = None
    days: int | None = None

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        hits = hybrid_search(
            self.pool,
            self.embedder,
            query,
            limit=self.k,
            company=self.company,
            event_type=self.event_type,
            days=self.days,
        )
        return [hit_to_document(hit) for hit in hits]
