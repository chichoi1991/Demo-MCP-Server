"""
HTTP transport wrapper for FRED MCP Server.

Converts the stdio-based MCP server to Streamable HTTP transport
so it can run on Azure Container Apps and be accessed via HTTP POST /mcp.

API key can be provided via:
  - Request header: x-fred-api-key, api-key, x-api-key, or Authorization: Bearer <key>
  - Environment variable: FRED_API_KEY
Header takes priority over environment variable.
"""

import os
import logging
from contextlib import asynccontextmanager

import anyio
from mcp.server.streamable_http import StreamableHTTPServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

from .server import server as mcp_server
from . import tools as _tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

http_transport = StreamableHTTPServerTransport(
    mcp_session_id=None,
    is_json_response_enabled=True,
)


def _extract_api_key(request: Request) -> str | None:
    """Extract API key from request headers using multiple patterns."""
    key = (
        request.headers.get("x-fred-api-key")
        or request.headers.get("api-key")
        or request.headers.get("x-api-key")
        or request.headers.get("apikey")
        or None
    )
    if not key:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            key = auth[7:].strip() or None
    return key


@asynccontextmanager
async def lifespan(app):
    """Application lifespan: connect transport to MCP server."""
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
            logger.info("FRED MCP Server (HTTP) started on /mcp")
            yield
            tg.cancel_scope.cancel()


async def root(request: Request):
    return JSONResponse({
        "name": "FRED Economic Data MCP Server",
        "version": "0.1.0",
        "status": "running",
        "description": "US economic data insights via FRED API",
        "endpoints": {
            "mcp": "/mcp",
            "health": "/health",
        },
        "tools": [
            "get-consumer-demand",
            "get-cost-pressure",
            "get-macro-environment",
            "get-industry-production",
            "get-ev-energy-market",
            "search-fred-series",
        ],
    })


async def health(request: Request):
    env_key = os.environ.get("FRED_API_KEY", "")
    current_key = _tools.get_api_key()
    return JSONResponse({
        "status": "healthy" if current_key else "degraded",
        "env_api_key_configured": bool(env_key),
        "header_api_key_cached": bool(_tools._current_request_api_key),
        "effective_key_available": bool(current_key),
        "accepted_headers": [
            "x-fred-api-key",
            "api-key",
            "x-api-key",
            "Authorization: Bearer <key>",
        ],
    })


class MCPApp:
    """ASGI application that wraps Starlette with a custom /mcp handler."""

    def __init__(self, starlette_app, transport):
        self.starlette_app = starlette_app
        self.transport = transport

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].rstrip("/") == "/mcp":
            request = Request(scope, receive)
            header_key = _extract_api_key(request)

            logger.info(
                f"MCP request: method={request.method}, "
                f"x-fred-api-key={'[SET]' if request.headers.get('x-fred-api-key') else '[MISSING]'}, "
                f"api-key={'[SET]' if request.headers.get('api-key') else '[MISSING]'}, "
                f"authorization={'[SET]' if request.headers.get('authorization') else '[MISSING]'}, "
                f"resolved_key={'[SET]' if header_key else '[NONE]'}"
            )

            if header_key:
                _tools._current_request_api_key = header_key
                logger.info("API key updated from request header")

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
