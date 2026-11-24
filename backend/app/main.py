from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import articles, ask, briefing, companies, health, search
from app.config import get_settings
from app.db import apply_schema, create_pool
from app.embeddings import Embedder
from app.rag.llm import build_llm
from app.seed import seed_companies


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    pool = create_pool(settings.database_url)
    apply_schema(pool)
    seed_companies(pool)
    app.state.pool = pool
    app.state.embedder = Embedder(settings.embedding_model, settings.embedding_cache_dir)
    app.state.llm = build_llm(settings)
    yield
    pool.close()


app = FastAPI(title="MarketRadar API", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(companies.router)
app.include_router(articles.router)
app.include_router(search.router)
app.include_router(ask.router)
app.include_router(briefing.router)
