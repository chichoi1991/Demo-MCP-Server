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
    "description": "데이터 조회 기간 (6m=6개월, 1y=1년, 3y=3년, 5y=5년)",
    "enum": ["6m", "1y", "3y", "5y"],
    "default": "1y",
}

_UNITS_SCHEMA = {
    "type": "string",
    "description": (
        "데이터 변환 방식: "
        "lin=원본수치, chg=전기대비변화량, pch=전기대비변화율(%), "
        "pc1=전년동기대비변화율(%), "
        "pca=연율화복리변화율, log=자연로그"
    ),
    "enum": ["lin", "chg", "pch", "pc1", "pca", "log"],
    "default": "lin",
}


def _indicator_schema(series_map: dict) -> dict:
    """Build indicator enum schema from a series map."""
    return {
        "type": "string",
        "description": (
            "조회할 개별 지표 (생략 시 전체 조회). 선택지: "
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
                "미국 소비 수요 지표를 조회합니다: "
                "내구재 소비지출, 소비자심리지수, 신규주택착공, 신규주택판매, 자동차 총판매. "
                "주택착공·판매는 가전·건자재 수요의 선행지표입니다."
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
                "제조 원가 및 마진 압박 지표를 조회합니다: "
                "원/달러 환율, WTI 원유가격, 구리 PPI, 철강 PPI, 합성수지 PPI. "
                "생산원가, 물류비, 원자재 비용에 직접 영향을 미칩니다."
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
                "미국 거시경제 환경 데이터를 조회합니다: "
                "실질 GDP, CPI(전체·내구재), 연방기금금리, 실업률, "
                "10년물·2년물 국채금리. "
                "경기침체 위험(장단기 금리역전), 소비자 구매력, "
                "투자·금융 환경 판단에 활용됩니다."
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
                "미국 산업·제조업 동향 지표를 조회합니다: "
                "산업생산지수, 내구재 신규주문, 전체 제조업 신규주문, "
                "제조업 생산지수. "
                "공장 가동률 및 공급망 상황 파악에 활용됩니다."
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
                "EV 및 에너지 시장 지표를 조회합니다: "
                "자동차 총판매, 재고/판매 비율, WTI 원유가격, 휘발유 소매가격, "
                "자동차 생산지수. "
                "유가 상승은 EV 전환을 가속화하며, 차량 판매량은 OEM 부품 수요를 나타냅니다."
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
                "FRED 데이터베이스에서 키워드로 경제 시계열을 검색합니다. "
                "프리셋 5개 테마 외 추가 지표를 탐색할 때 사용합니다. "
                "시리즈 ID, 제목, 빈도, 단위, 인기도를 반환합니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색 키워드 (예: 'semiconductor production', 'Korea GDP', '반도체')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "최대 검색 결과 수 (1~50)",
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
