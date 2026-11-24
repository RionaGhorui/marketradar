import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp_server import tools
from tests.support import FakeEmbedder, add_article

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_search_news_returns_plain_json_values(pool, empty_articles):
    add_article(pool, "Databricks", "Databricks funding news", "https://example.com/a", summary="Raised money.", vector_index=0)

    results = tools.search_news(pool, FakeEmbedder(0), "funding", company="Databricks")

    assert results[0]["title"] == "Databricks funding news"
    assert results[0]["company"] == "Databricks"
    assert isinstance(results[0]["published_at"], str)
    assert "score" not in results[0]
    json.dumps(results)


def test_get_competitor_events_filters_by_company_and_type(pool, empty_articles):
    add_article(pool, "Databricks", "Databricks funding", "https://example.com/a", "funding")
    add_article(pool, "Databricks", "Databricks launch", "https://example.com/b", "product_launch")
    add_article(pool, "OpenAI", "OpenAI funding", "https://example.com/c", "funding")

    everything = tools.get_competitor_events(pool, "Databricks")
    assert {event["company"] for event in everything} == {"Databricks"}

    launches = tools.get_competitor_events(pool, "Databricks", event_type="product_launch")
    assert [event["title"] for event in launches] == ["Databricks launch"]


def test_weekly_briefing_tool_is_json_safe(pool, empty_articles):
    add_article(pool, "OpenAI", "OpenAI funding", "https://example.com/c", "funding")
    briefing = tools.weekly_briefing(pool, days=7)
    assert briefing[0]["company"] == "OpenAI"
    json.dumps(briefing)


def test_limits_are_clamped():
    assert tools.clamp(500, 1, 20) == 20
    assert tools.clamp(-3, 1, 20) == 1


async def talk_to_server():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        env=dict(os.environ),
        cwd=str(BACKEND_DIR),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listing = await session.list_tools()
            briefing = await session.call_tool("weekly_briefing", {"days": 7})
            events = await session.call_tool("get_competitor_events", {"company": "Databricks"})
            return listing, briefing, events


def test_mcp_server_works_over_stdio(pool, empty_articles):
    add_article(pool, "Databricks", "Databricks funding news", "https://example.com/a", "funding")

    listing, briefing, events = asyncio.run(asyncio.wait_for(talk_to_server(), timeout=90))

    assert {tool.name for tool in listing.tools} == {
        "search_news",
        "get_competitor_events",
        "weekly_briefing",
    }
    assert all(tool.description for tool in listing.tools)
    assert json.loads(briefing.content[0].text)["company"] == "Databricks"
    assert json.loads(events.content[0].text)["title"] == "Databricks funding news"
