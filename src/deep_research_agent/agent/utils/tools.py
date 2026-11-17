import asyncio

from fastmcp import Client

from deep_research_agent.mcp_server import mcp


async def list_mcp_tools() -> list[str]:
    async with Client(mcp) as client:
        return [tool.name for tool in await client.list_tools()]


async def call_mcp_tool(name: str, arguments: dict[str, object]) -> object:
    async with Client(mcp) as client:
        result = await client.call_tool(name, arguments)
        return result.data


async def main() -> None:
    print(await list_mcp_tools())


if __name__ == "__main__":
    asyncio.run(main())
