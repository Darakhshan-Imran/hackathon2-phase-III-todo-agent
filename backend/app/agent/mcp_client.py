"""
MCP Client for connecting to a remote MCP server (Production).

Uses the openai-agents SDK's MCPServerStreamableHttp transport
to connect to the remote MCP server over Streamable HTTP.

The remote MCP server handles all tool execution (task CRUD, batch ops, SQL queries)
and database access. This client simply connects and exposes the tools to the agent.
"""

import logging
from typing import Optional

from agents.mcp import MCPServerStreamableHttp

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level MCP server instance (reusable across requests)
_mcp_server: Optional[MCPServerStreamableHttp] = None


def get_mcp_server() -> MCPServerStreamableHttp:
    """Get or create a configured MCP server connection instance.

    Returns a MCPServerStreamableHttp configured for the remote MCP server.
    The server instance is created once and reused across requests.

    The actual connection is managed via async context manager in the agent router.
    """
    global _mcp_server

    if _mcp_server is not None:
        return _mcp_server

    # Build connection headers
    headers: dict[str, str] = {}
    if settings.MCP_API_KEY:
        headers["Authorization"] = f"Bearer {settings.MCP_API_KEY}"

    logger.info("Creating MCP server connection")

    _mcp_server = MCPServerStreamableHttp(
        name="Neon Task MCP Server",
        params={
            "url": settings.MCP_SERVER_URL,
            "headers": headers,
            "timeout": settings.MCP_SERVER_TIMEOUT,
        },
        cache_tools_list=settings.MCP_CACHE_TOOLS,
        max_retry_attempts=settings.MCP_MAX_RETRIES,
    )

    return _mcp_server


async def cleanup_mcp_server():
    """Cleanup the MCP server connection on shutdown."""
    global _mcp_server
    if _mcp_server is not None:
        logger.info("Cleaning up MCP server connection")
        _mcp_server = None
