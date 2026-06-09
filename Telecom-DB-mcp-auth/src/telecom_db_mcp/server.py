"""
Telecom Devices MCP Server.

Exposes 4 tools backed by the in-memory DuckDB instance:
1. list-devices       — filtered device listing
2. get-device-stats   — group-by aggregations
3. get-table-schema   — schema + sample rows for LLM grounding
4. run-sql            — safe SELECT execution against the devices table
"""

from __future__ import annotations

import asyncio
import json
import logging

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from . import db

logger = logging.getLogger(__name__)

server = Server("telecom_devices")


# ── Tool definitions ────────────────────────────────────────────────


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list-devices",
            description=(
                "통신 단말 데이터(devices 테이블)에서 조건에 맞는 행을 조회합니다. "
                "제조사·모델명·네트워크·OS·최소 배터리 잔량 필터를 지원합니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "manufacturer": {
                        "type": "string",
                        "description": "제조사 (예: Samsung, Apple, Xiaomi, Google)",
                    },
                    "model_name": {
                        "type": "string",
                        "description": "모델명 (예: 'Galaxy S24', 'iPhone 15 Pro')",
                    },
                    "network_type": {
                        "type": "string",
                        "description": "네트워크 타입 (예: '5G', 'LTE')",
                    },
                    "os_version": {
                        "type": "string",
                        "description": "OS 버전 (예: 'Android 14', 'iOS 17')",
                    },
                    "min_battery_health": {
                        "type": "number",
                        "description": "Battery_Health_Pct 최솟값 (0~100+)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "반환 행 수 (1~500, 기본 50)",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 500,
                    },
                },
            },
        ),
        types.Tool(
            name="get-device-stats",
            description=(
                "devices 테이블을 group_by 컬럼으로 집계합니다. "
                "metrics 로 count, 평균 배터리, 평균 데이터 사용량, 평균 출시가 등을 선택할 수 있습니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "group_by": {
                        "type": "string",
                        "description": "그룹화 기준 컬럼",
                        "enum": [
                            "Manufacturer",
                            "Model_Name",
                            "Network_Type",
                            "OS_Version",
                            "Top_App_Category",
                            "Subsidy_Type",
                            "Preferred_Channel",
                            "Bundling_Status",
                            "Biometric_Type",
                            "Storage_Capacity_GB",
                            "Wireless_Charging",
                            "Device_Insurance",
                            "Trade_in_Program",
                        ],
                    },
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "count",
                                "avg_battery_health",
                                "avg_data_usage",
                                "avg_launch_price",
                                "avg_months_in_use",
                                "avg_brand_loyalty",
                                "total_remaining_installment",
                                "avg_repair_history",
                            ],
                        },
                        "description": "집계 메트릭 (생략 시 기본 4개)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "반환 그룹 수 (1~200, 기본 50)",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 200,
                    },
                },
                "required": ["group_by"],
            },
        ),
        types.Tool(
            name="get-table-schema",
            description=(
                "devices 테이블의 스키마(컬럼명·타입), 행 수, 샘플 5행을 반환합니다. "
                "run-sql 도구로 쿼리를 작성하기 전 컨텍스트 파악에 사용하세요."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="run-sql",
            description=(
                "devices 테이블에 대한 안전한 SELECT(또는 WITH ... SELECT) 쿼리를 실행합니다. "
                "INSERT/UPDATE/DELETE/DROP 등 변경 쿼리와 다중 statement는 거부됩니다. "
                "결과는 자동으로 limit 행으로 잘립니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": (
                            "실행할 SQL. 예: "
                            "\"SELECT Manufacturer, COUNT(*) AS cnt FROM devices "
                            "GROUP BY 1 ORDER BY cnt DESC\""
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": (
                            f"반환 행 수 한도 (기본 {db.DEFAULT_MAX_ROWS}, "
                            f"최대 {db.ABSOLUTE_MAX_ROWS})."
                        ),
                        "default": db.DEFAULT_MAX_ROWS,
                        "minimum": 1,
                        "maximum": db.ABSOLUTE_MAX_ROWS,
                    },
                },
                "required": ["sql"],
            },
        ),
    ]


# ── Tool dispatch ───────────────────────────────────────────────────


def _text(payload: dict | list | str) -> list[types.TextContent]:
    if isinstance(payload, str):
        return [types.TextContent(type="text", text=payload)]
    return [
        types.TextContent(
            type="text",
            text=json.dumps(payload, ensure_ascii=False, indent=2),
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    arguments = arguments or {}
    try:
        if name == "list-devices":
            result = db.list_devices(
                manufacturer=arguments.get("manufacturer"),
                model_name=arguments.get("model_name"),
                network_type=arguments.get("network_type"),
                os_version=arguments.get("os_version"),
                min_battery_health=arguments.get("min_battery_health"),
                limit=int(arguments.get("limit", 50)),
            )
            return _text(result)

        if name == "get-device-stats":
            group_by = arguments.get("group_by")
            if not group_by:
                return _text("'group_by' 파라미터가 필요합니다.")
            result = db.device_stats(
                group_by=group_by,
                metrics=arguments.get("metrics"),
                limit=int(arguments.get("limit", 50)),
            )
            return _text(result)

        if name == "get-table-schema":
            return _text(db.get_table_overview())

        if name == "run-sql":
            sql = arguments.get("sql")
            if not sql:
                return _text("'sql' 파라미터가 필요합니다.")
            result = db.safe_execute(
                sql=sql,
                max_rows=int(arguments.get("limit", db.DEFAULT_MAX_ROWS)),
            )
            return _text(result)

        return _text(f"Unknown tool: {name}")

    except db.SQLValidationError as e:
        return _text({"error": "SQLValidationError", "message": str(e)})
    except Exception as e:  # surface DuckDB errors back to caller
        logger.exception("Tool '%s' failed", name)
        return _text({"error": type(e).__name__, "message": str(e)})


# ── stdio entrypoint (used by CLI / `python -m telecom_db_mcp`) ────


async def main() -> None:
    db.init_db()
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="telecom_devices",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
