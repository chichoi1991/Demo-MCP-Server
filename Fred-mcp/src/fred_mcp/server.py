"""
FRED MCP Server - US Economic Data for Business Decision Making

Provides 5 themed tools for querying Federal Reserve Economic Data (FRED):
1. Consumer Demand Indicators (housing, durable goods, vehicle sales)
2. Cost & Margin Pressure (exchange rate, commodities, PPI)
3. Macro Environment (GDP, CPI, interest rates, employment)
4. Industry & Manufacturing (production, orders)
5. EV & Energy Market (vehicle sales, fuel prices, auto production)
"""

from typing import Any
import asyncio
import httpx
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

from .tools import (
    fetch_theme_data,
    search_fred_series,
    API_KEY,
    CONSUMER_DEMAND_SERIES,
    COST_PRESSURE_SERIES,
    MACRO_ENVIRONMENT_SERIES,
    INDUSTRY_PRODUCTION_SERIES,
    EV_ENERGY_SERIES,
)

import logging as _logging

if not API_KEY:
    _logging.getLogger(__name__).warning(
        "FRED_API_KEY environment variable not set. "
        "FRED API requests will fail until the key is configured."
    )

server = Server("fred_economic_data")

# ── Shared schema fragments ─────────────────────────────────────────

_PERIOD_SCHEMA = {
    "type": "string",
    "description": "Time period for data retrieval",
    "enum": ["6m", "1y", "3y", "5y"],
    "default": "1y",
}

_UNITS_SCHEMA = {
    "type": "string",
    "description": (
        "Data transformation: "
        "lin=Levels, chg=Change, pch=Percent Change, "
        "pc1=Percent Change from Year Ago, "
        "pca=Compounded Annual Rate of Change, log=Natural Log"
    ),
    "enum": ["lin", "chg", "pch", "pc1", "pca", "log"],
    "default": "lin",
}


def _indicator_schema(series_map: dict) -> dict:
    """Build indicator enum schema from a series map."""
    return {
        "type": "string",
        "description": (
            "Specific indicator to query (omit for all). Options: "
            + ", ".join(f"{k} ({v})" for k, v in series_map.items())
        ),
        "enum": list(series_map.keys()),
    }


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        # ── Tool 1: Consumer Demand ──────────────────────────────────
        types.Tool(
            name="get-consumer-demand",
            description=(
                "Get US consumer demand indicators: "
                "durable goods spending, consumer sentiment, housing starts, new home sales, vehicle sales. "
                "Housing starts and new home sales are leading indicators for appliance and building material demand."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "indicator": _indicator_schema(CONSUMER_DEMAND_SERIES),
                    "period": _PERIOD_SCHEMA,
                    "units": _UNITS_SCHEMA,
                },
            },
        ),
        # ── Tool 2: Cost & Margin Pressure ───────────────────────────
        types.Tool(
            name="get-cost-pressure",
            description=(
                "Get cost and margin pressure indicators for manufacturing: "
                "KRW/USD exchange rate, WTI crude oil price, copper PPI, steel PPI, plastics resin PPI. "
                "These directly impact production costs, logistics, and raw material expenses."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "indicator": _indicator_schema(COST_PRESSURE_SERIES),
                    "period": _PERIOD_SCHEMA,
                    "units": _UNITS_SCHEMA,
                },
            },
        ),
        # ── Tool 3: Macro Environment ────────────────────────────────
        types.Tool(
            name="get-macro-environment",
            description=(
                "Get US macroeconomic environment data: "
                "real GDP, CPI (all items & durables), federal funds rate, unemployment rate, "
                "10-year and 2-year Treasury rates. "
                "Useful for assessing recession risk (yield curve inversion), consumer purchasing power, "
                "and investment/financing conditions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "indicator": _indicator_schema(MACRO_ENVIRONMENT_SERIES),
                    "period": _PERIOD_SCHEMA,
                    "units": _UNITS_SCHEMA,
                },
            },
        ),
        # ── Tool 4: Industry & Manufacturing ─────────────────────────
        types.Tool(
            name="get-industry-production",
            description=(
                "Get US industry and manufacturing indicators: "
                "industrial production index, durable goods new orders, total manufacturing orders, "
                "manufacturing production index. "
                "Relevant for assessing factory capacity utilization and supply chain conditions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "indicator": _indicator_schema(INDUSTRY_PRODUCTION_SERIES),
                    "period": _PERIOD_SCHEMA,
                    "units": _UNITS_SCHEMA,
                },
            },
        ),
        # ── Tool 5: EV & Energy Market ───────────────────────────────
        types.Tool(
            name="get-ev-energy-market",
            description=(
                "Get EV and energy market indicators: "
                "total vehicle sales, auto inventory/sales ratio, WTI crude oil, gasoline prices, "
                "motor vehicle production index. "
                "High fuel prices accelerate EV adoption; vehicle sales indicate OEM parts demand."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "indicator": _indicator_schema(EV_ENERGY_SERIES),
                    "period": _PERIOD_SCHEMA,
                    "units": _UNITS_SCHEMA,
                },
            },
        ),
        # ── Bonus: Search Series ─────────────────────────────────────
        types.Tool(
            name="search-fred-series",
            description=(
                "Search FRED for economic data series by keyword. "
                "Use this to discover additional indicators beyond the preset themes. "
                "Returns series ID, title, frequency, units, and popularity."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords to search for (e.g., 'semiconductor production', 'Korea GDP')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (1-50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["query"],
            },
        ),
    ]


# ── Theme lookup ─────────────────────────────────────────────────────

_TOOL_THEME_MAP = {
    "get-consumer-demand": "consumer_demand",
    "get-cost-pressure": "cost_pressure",
    "get-macro-environment": "macro_environment",
    "get-industry-production": "industry_production",
    "get-ev-energy-market": "ev_energy",
}


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None,
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if not arguments:
        arguments = {}

    # ── Themed data tools ────────────────────────────────────────────
    if name in _TOOL_THEME_MAP:
        theme = _TOOL_THEME_MAP[name]
        indicator = arguments.get("indicator")
        period = arguments.get("period", "1y")
        units = arguments.get("units", "lin")

        async with httpx.AsyncClient() as client:
            result = await fetch_theme_data(
                client,
                theme=theme,
                indicator=indicator,
                period=period,
                units=units,
            )
        return [types.TextContent(type="text", text=result)]

    # ── Search tool ──────────────────────────────────────────────────
    elif name == "search-fred-series":
        query = arguments.get("query")
        if not query:
            return [types.TextContent(type="text", text="Missing 'query' parameter.")]

        limit = arguments.get("limit", 10)

        async with httpx.AsyncClient() as client:
            result = await search_fred_series(client, query, limit=limit)
        return [types.TextContent(type="text", text=result)]

    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="fred_economic_data",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
