"""
HTTP transport wrapper for YouTube MCP Server.

Converts the stdio-based MCP server to Streamable HTTP transport
so it can run on Azure Container Apps and be accessed via HTTP POST /mcp.
"""

import logging
from contextlib import asynccontextmanager

import anyio
from mcp.server.streamable_http import StreamableHTTPServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

from .server import server as mcp_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

http_transport = StreamableHTTPServerTransport(
    mcp_session_id=None,
    is_json_response_enabled=True,
)


@asynccontextmanager
async def lifespan(app):
    """Application lifespan: connect transport to MCP server."""
    async with http_transport.connect() as (read_stream, write_stream):
        task_group = anyio.create_task_group()
        async with task_group as tg:
            async def run_mcp():
                await mcp_server.run(
                    read_stream, write_stream,
                    mcp_server.create_initialization_options(),
                )
            tg.start_soon(run_mcp)
            logger.info("YouTube MCP Server (HTTP) started on /mcp")
            yield
            tg.cancel_scope.cancel()


async def root(request: Request):
    return JSONResponse({
        "name": "YouTube Search MCP Server",
        "version": "0.1.0",
        "status": "running",
        "description": "YouTube video search and details via yt-dlp",
        "endpoints": {"mcp": "/mcp", "health": "/health"},
        "tools": ["search-youtube", "get-video-details"],
    })


async def health(request: Request):
    return JSONResponse({"status": "healthy"})


class MCPApp:
    """ASGI application that wraps Starlette with a custom /mcp handler."""
    def __init__(self, starlette_app, transport):
        self.starlette_app = starlette_app
        self.transport = transport

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].rstrip("/") == "/mcp":
            await self.transport.handle_request(scope, receive, send)
        elif scope["type"] == "lifespan":
            await self.starlette_app(scope, receive, send)
        else:
            await self.starlette_app(scope, receive, send)


_inner_app = Starlette(
    debug=False,
    routes=[Route("/", root), Route("/health", health)],
    lifespan=lifespan,
)

app = MCPApp(_inner_app, http_transport)
