"""
HTTP transport wrapper for the Network Config MCP Server.

Converts the stdio-based MCP server to Streamable HTTP transport so it can
run on Azure Container Apps and be accessed via HTTP POST /mcp.

This server requires no authentication (PoC). To add Entra ID Easy Auth,
follow the Telecom-DB-mcp-auth bicep pattern.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import anyio
from mcp.server.streamable_http import StreamableHTTPServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import loader
from .server import server as mcp_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

http_transport = StreamableHTTPServerTransport(
    mcp_session_id=None,
    is_json_response_enabled=True,
)


@asynccontextmanager
async def lifespan(app):
    """Application lifespan: load catalog, then connect transport to MCP server."""
    loader.load_catalog()
    logger.info("Network Config MCP catalog loaded: %s", loader.list_devices())

    async with http_transport.connect() as (read_stream, write_stream):
        task_group = anyio.create_task_group()
        async with task_group as tg:

            async def run_mcp():
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options(),
                )

            tg.start_soon(run_mcp)
            logger.info("Network Config MCP Server (HTTP) started on /mcp")
            yield
            tg.cancel_scope.cancel()


async def root(request: Request):
    return JSONResponse(
        {
            "name": "Network Config MCP Server",
            "version": "0.1.0",
            "status": "running",
            "description": (
                "Returns standard network device configurations and vendor "
                "documentation links for use in Copilot Studio agents."
            ),
            "endpoints": {
                "mcp": "/mcp",
                "health": "/health",
            },
            "tools": ["get_standard_config"],
        }
    )


async def health(request: Request):
    devices = loader.list_devices()
    return JSONResponse(
        {
            "status": "healthy" if devices else "degraded",
            "device_count": len(devices),
            "devices": devices,
        }
    )


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
    routes=[
        Route("/", root),
        Route("/health", health),
    ],
    lifespan=lifespan,
)

app = MCPApp(_inner_app, http_transport)
