import logging
import sys

import httpx
import openai

from app.config import get_settings
from app.db import apply_schema, create_pool
from app.embeddings import Embedder
from app.seed import seed_companies
from etl.pipeline import Pipeline
from etl.sources import fetch_all
from etl.storage import LocalRawStore
from etl.tagger import CONFIG_ERRORS, Tagger

log = logging.getLogger("etl.run")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    settings = get_settings()
    if not settings.llm_api_key:
        log.error("LLM_API_KEY is empty. Add it to your .env file and run again.")
        return 1

    pool = create_pool(settings.database_url)
    apply_schema(pool)
    seed_companies(pool)

    client = openai.OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        max_retries=3,
        timeout=45.0,
    )
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MarketRadarBot/0.2)"}

    try:
        with httpx.Client(timeout=settings.http_timeout, headers=headers, follow_redirects=True) as http_client:
            pipeline = Pipeline(
                pool=pool,
                fetch=lambda companies: fetch_all(http_client, companies, settings.lookback_days),
                tagger=Tagger(client, settings.llm_model, settings.llm_requests_per_minute),
                embedder=Embedder(settings.embedding_model, settings.embedding_cache_dir),
                raw_store=LocalRawStore(settings.raw_data_dir),
                lookback_days=settings.lookback_days,
                max_new_per_company=settings.max_new_per_company,
            )
            stats = pipeline.run()
    except CONFIG_ERRORS as error:
        log.error("The language model provider rejected the request: %s", error)
        log.error("Check LLM_API_KEY, LLM_BASE_URL and LLM_MODEL in .env, then run: docker compose run --rm etl python -m etl.check_llm")
        return 1
    finally:
        pool.close()

    print()
    for key, value in sorted(stats.items()):
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
