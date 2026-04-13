"""
HTTP transport wrapper for News API MCP Server.

Converts the stdio-based MCP server to Streamable HTTP transport
so it can run on Azure Container Apps and be accessed via HTTP POST /mcp.

API key can be provided via:
  - Request header: x-news-api-key, api-key, x-api-key, or Authorization: Bearer <key>
  - Environment variable: NEWS_API_KEY
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

# Single stateless transport instance (no session tracking needed)
http_transport = StreamableHTTPServerTransport(
    mcp_session_id=None,
    is_json_response_enabled=True,
)


def _extract_api_key(request: Request) -> str | None:
    """Extract API key from request headers using multiple patterns."""
    key = (
        request.headers.get("x-news-api-key")
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
            logger.info("News API MCP Server (HTTP) started on /mcp")
            yield
            tg.cancel_scope.cancel()


async def root(request: Request):
    return JSONResponse({
        "name": "News API MCP Server",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "mcp": "/mcp",
            "health": "/health",
        },
    })


async def health(request: Request):
    from .tools import get_api_key
    env_key = os.environ.get("NEWS_API_KEY", "")
    current_key = get_api_key()
    return JSONResponse({
        "status": "healthy" if current_key else "degraded",
        "env_api_key_configured": bool(env_key),
        "header_api_key_cached": bool(_tools._current_request_api_key),
        "effective_key_available": bool(current_key),
        "accepted_headers": ["x-news-api-key", "api-key", "x-api-key", "Authorization: Bearer <key>"],
    })


async def debug_headers(request: Request):
    """Debug endpoint: shows all received headers (values sanitized)."""
    headers = {}
    for key, value in request.headers.items():
        if any(s in key.lower() for s in ["key", "auth", "token", "secret"]):
            headers[key] = f"[SET: {len(value)} chars]"
        else:
            headers[key] = value
    return JSONResponse({
        "method": request.method,
        "path": str(request.url.path),
        "headers": headers,
        "current_api_key_cached": bool(_tools._current_request_api_key),
    })


class MCPApp:
    """ASGI application that wraps Starlette with a custom /mcp handler.
    
    Routes /mcp directly to the StreamableHTTP transport (avoiding Starlette's
    Mount which causes 307 redirects that drop custom headers).
    All other routes go through the normal Starlette app.
    """

    def __init__(self, starlette_app, transport):
        self.starlette_app = starlette_app
        self.transport = transport

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].rstrip("/") == "/mcp":
            # Extract API key from headers before forwarding to transport
            request = Request(scope, receive)
            header_key = _extract_api_key(request)

            logger.info(
                f"MCP request: method={request.method}, "
                f"x-news-api-key={'[SET]' if request.headers.get('x-news-api-key') else '[MISSING]'}, "
                f"api-key={'[SET]' if request.headers.get('api-key') else '[MISSING]'}, "
                f"authorization={'[SET]' if request.headers.get('authorization') else '[MISSING]'}, "
                f"resolved_key={'[SET]' if header_key else '[NONE]'}"
            )

            if header_key:
                _tools._current_request_api_key = header_key
                logger.info("API key updated from request header")

            # Delegate directly to MCP transport (no redirect)
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
        Route("/debug/headers", debug_headers),
    ],
    lifespan=lifespan,
)

app = MCPApp(_inner_app, http_transport)
