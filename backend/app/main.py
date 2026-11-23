from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import articles, companies, health
from app.config import get_settings
from app.db import apply_schema, create_pool
from app.seed import seed_companies


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    pool = create_pool(settings.database_url)
    apply_schema(pool)
    seed_companies(pool)
    app.state.pool = pool
    yield
    pool.close()


app = FastAPI(title="MarketRadar API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(companies.router)
app.include_router(articles.router)
