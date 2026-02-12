"""
MCP Client for connecting to the local MCP server via stdio transport.

Launches the local MCP server (app.mcp_server.server) as a subprocess.
Explicitly passes DATABASE_URL to the subprocess environment.
"""

import logging
import os
import sys

from agents.mcp import MCPServerStdio

from app.config import settings

logger = logging.getLogger(__name__)


def get_mcp_server() -> MCPServerStdio:
    """Create a new MCPServerStdio instance pointing to the local MCP server.

    Each call creates a fresh instance. The actual subprocess lifecycle is
    managed via the ``async with mcp_server:`` context manager in the agent router.
    """
    logger.info("Creating local MCP server (stdio)")

    # Build env for the subprocess — inherit current env and ensure DATABASE_URL is set.
    env = os.environ.copy()
    env["DATABASE_URL"] = settings.DATABASE_URL

    return MCPServerStdio(
        name="Local Todo MCP Server",
        params={
            "command": sys.executable,
            "args": ["-m", "app.mcp_server.server"],
            "env": env,
        },
    )
