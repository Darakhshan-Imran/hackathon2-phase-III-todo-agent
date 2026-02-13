"""
MCP Client for connecting to the local MCP server via stdio transport.

Launches the local MCP server (app.mcp_server.server) as a subprocess.
Explicitly passes DATABASE_URL to the subprocess environment.
"""

import logging
import os
import sys
from pathlib import Path

from agents.mcp import MCPServerStdio

from app.config import settings

# backend/ directory — the cwd for the MCP subprocess so `-m app.mcp_server.server` resolves
# mcp_client.py -> agent/ -> app/ -> backend/
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent.parent)

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
    # Ensure the backend/ dir is on PYTHONPATH so `-m app.mcp_server.server` resolves
    env["PYTHONPATH"] = _BACKEND_DIR + os.pathsep + env.get("PYTHONPATH", "")

    server_script = str(Path(_BACKEND_DIR) / "app" / "mcp_server" / "server.py")

    return MCPServerStdio(
        name="Local Todo MCP Server",
        params={
            "command": sys.executable,
            "args": [server_script],
            "env": env,
            "cwd": _BACKEND_DIR,
        },
    )
