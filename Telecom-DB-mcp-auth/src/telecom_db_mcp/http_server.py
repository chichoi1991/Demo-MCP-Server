"""
HTTP transport wrapper for the Telecom Devices MCP server.

Exposes:
- GET  /          service metadata
- GET  /health    DB connection + row count
- GET  /schema    devices table columns + sample rows
- POST /query     execute a safe read-only SQL query
- ANY  /mcp       MCP Streamable HTTP transport endpoint
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import anyio
import duckdb
from mcp.server.streamable_http import StreamableHTTPServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import db
from .server import server as mcp_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

http_transport = StreamableHTTPServerTransport(
    mcp_session_id=None,
    is_json_response_enabled=True,
)


# ── Lifespan ────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app):
    """Initialise DuckDB and connect MCP transport for the app lifetime."""
    db.init_db()
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
            logger.info(
                "Telecom Devices MCP Server started — REST /query and MCP /mcp ready"
            )
            yield
            tg.cancel_scope.cancel()


# ── REST routes ─────────────────────────────────────────────────────


async def root(request: Request):
    return JSONResponse(
        {
            "name": "Telecom Devices MCP Server",
            "version": "0.1.0",
            "status": "running",
            "description": (
                "In-memory DuckDB query service for telecom device analysis data, "
                "exposed via REST and MCP."
            ),
            "endpoints": {
                "metadata": "/",
                "health": "/health",
                "schema": "/schema",
                "query": "/query",
                "mcp": "/mcp",
            },
            "table": db.TABLE_NAME,
            "tools": [
                "list-devices",
                "get-device-stats",
                "get-table-schema",
                "run-sql",
            ],
        }
    )


async def health(request: Request):
    try:
        rows = db.get_row_count()
        return JSONResponse(
            {
                "status": "healthy",
                "table": db.TABLE_NAME,
                "row_count": rows,
            }
        )
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("Health check failed")
        return JSONResponse(
            {"status": "unhealthy", "error": str(e)}, status_code=503
        )


async def schema(request: Request):
    try:
        return JSONResponse(db.get_table_overview())
    except Exception as e:
        logger.exception("Schema lookup failed")
        return JSONResponse({"error": str(e)}, status_code=500)


async def query(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"error": "InvalidJSON", "message": "Request body must be JSON"},
            status_code=400,
        )

    sql = body.get("sql")
    params = body.get("params")
    limit = body.get("limit", db.DEFAULT_MAX_ROWS)

    if params is not None and not isinstance(params, list):
        return JSONResponse(
            {"error": "InvalidParams", "message": "'params' must be an array"},
            status_code=400,
        )

    try:
        result = db.safe_execute(sql=sql, params=params, max_rows=int(limit))
        return JSONResponse(result)
    except db.SQLValidationError as e:
        return JSONResponse(
            {"error": "SQLValidationError", "message": str(e)},
            status_code=400,
        )
    except duckdb.Error as e:
        return JSONResponse(
            {"error": type(e).__name__, "message": str(e)},
            status_code=422,
        )
    except Exception as e:
        logger.exception("Query failed")
        return JSONResponse(
            {"error": type(e).__name__, "message": str(e)}, status_code=500
        )


# ── ASGI app: route /mcp directly to the MCP transport ─────────────


class MCPApp:
    """ASGI wrapper that routes /mcp directly to StreamableHTTP transport."""

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
        Route("/schema", schema),
        Route("/query", query, methods=["POST"]),
    ],
    lifespan=lifespan,
)

app = MCPApp(_inner_app, http_transport)
