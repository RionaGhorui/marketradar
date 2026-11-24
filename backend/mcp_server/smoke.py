import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check_server() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        env=dict(os.environ),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            listing = await session.list_tools()
            print("Tools exposed by the MCP server:")
            for tool in listing.tools:
                print(f"  {tool.name}")

            result = await session.call_tool("weekly_briefing", {"days": 30})
            text = result.content[0].text if result.content else ""
            print(f"\nweekly_briefing returned {len(text)} characters:")
            print(text[:400])


if __name__ == "__main__":
    asyncio.run(check_server())
