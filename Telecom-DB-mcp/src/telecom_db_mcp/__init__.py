"""Telecom Device Analysis MCP Server.

Loads the bundled telecom device CSV into an in-memory DuckDB instance
and exposes both a REST query API and an MCP Streamable HTTP server.
"""

import asyncio


def main() -> None:
    """Entry point for the stdio MCP server (used by CLI)."""
    from .server import main as _server_main

    asyncio.run(_server_main())


__all__ = ["main"]
