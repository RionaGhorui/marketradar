from mcp.server.fastmcp import FastMCP

from app.config import get_settings
from app.db import apply_schema, create_pool
from app.embeddings import Embedder
from mcp_server import tools


def create_server(pool, embedder) -> FastMCP:
    server = FastMCP("MarketRadar")

    @server.tool(
        description=(
            "Search tracked competitor news by meaning and keywords. Optionally filter by "
            "company name (for example Databricks) and by how many days back to look."
        )
    )
    def search_news(
        query: str, company: str | None = None, days: int | None = None, limit: int = 5
    ) -> list[dict]:
        return tools.search_news(pool, embedder, query, company, days, limit)

    @server.tool(
        description=(
            "List recent events for one tracked company. event_type can be funding, "
            "product_launch, partnership, acquisition, leadership_change, hiring, "
            "pricing_change, legal_regulatory or other."
        )
    )
    def get_competitor_events(
        company: str, event_type: str | None = None, days: int = 30, limit: int = 10
    ) -> list[dict]:
        return tools.get_competitor_events(pool, company, event_type, days, limit)

    @server.tool(
        description=(
            "Summarise what happened across all tracked companies in the last few days: "
            "event counts per type and the newest headlines for each company."
        )
    )
    def weekly_briefing(days: int = 7) -> list[dict]:
        return tools.weekly_briefing(pool, days)

    return server


def main() -> None:
    settings = get_settings()
    pool = create_pool(settings.database_url)
    apply_schema(pool)
    embedder = Embedder(settings.embedding_model, settings.embedding_cache_dir)
    create_server(pool, embedder).run()


if __name__ == "__main__":
    main()
