import logging

import openai
from fastapi import APIRouter, Depends, HTTPException
from psycopg_pool import ConnectionPool

from app.deps import get_embedder, get_llm, get_pool
from app.rag.chain import build_chain, cited_sources
from app.rag.retriever import HybridRetriever
from app.schemas import AskRequest, AskResponse

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    pool: ConnectionPool = Depends(get_pool),
    embedder=Depends(get_embedder),
    llm=Depends(get_llm),
):
    if llm is None:
        raise HTTPException(503, "The language model is not configured. Set LLM_API_KEY in .env.")

    retriever = HybridRetriever(
        pool=pool,
        embedder=embedder,
        k=6,
        company=body.company,
        event_type=body.event_type,
        days=body.days,
    )
    chain = build_chain(retriever, llm)

    try:
        result = chain.invoke(body.question)
    except openai.RateLimitError:
        raise HTTPException(429, "The language model is busy right now. Try again in a minute.")
    except openai.APIError as error:
        log.error("language model call failed: %s", error)
        raise HTTPException(502, "The language model could not answer right now.")

    if not result["answer"]:
        raise HTTPException(502, "The language model returned an empty answer. Try again.")

    return {
        "answer": result["answer"],
        "sources": cited_sources(result["answer"], result["documents"]),
    }
