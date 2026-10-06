import sys

from mcp import Client, StdioServerParameters, types

from app.config import BASE_DIR


class MCPClient:
    """Starts the MCP server as a subprocess and talks to it over stdio.

    Use as an async context manager: the subprocess lives as long as the block.
    """

    def __init__(self) -> None:
        self._client = Client(
            StdioServerParameters(
                command=sys.executable,
                args=["-m", "app.mcp_server"],
                cwd=BASE_DIR,
            )
        )

    async def __aenter__(self) -> "MCPClient":
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self._client.__aexit__(*exc_info)

    async def list_tools(self) -> list[types.Tool]:
        return (await self._client.list_tools()).tools

    async def call_tool(self, name: str, arguments: dict) -> str:
        """Call a tool and return its result as text (errors included)."""
        result = await self._client.call_tool(name, arguments)
        return "\n".join(block.text for block in result.content if block.type == "text")


def to_openai_tools(tools: list[types.Tool]) -> list[dict]:
    """Convert MCP tool definitions into the OpenAI `tools` format."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
            },
        }
        for tool in tools
    ]
