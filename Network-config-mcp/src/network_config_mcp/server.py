"""
Network Config MCP Server.

Exposes a single tool, `get_standard_config`, that returns the full standard
operational configuration for a network device along with a list of vendor
documentation reference URLs, given a free-text query that names the
vendor and/or model (e.g. "cisco asr 9000", "asr9k").

Designed to back a Copilot Studio agent scenario where the agent retrieves
the standard configuration for a device, then compares it against a
user-uploaded configuration to produce a change guide.
"""

from __future__ import annotations

import asyncio
import json
import logging

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from . import loader

logger = logging.getLogger(__name__)

server = Server("network_config")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_standard_config",
            description=(
                "네트워크 장비의 운영 표준 전체 컨피그레이션과 제조사 참고 문서 URL "
                "리스트를 반환합니다. 쿼리에 제조사(예: cisco)와 모델(예: asr 9000, "
                "asr9k)을 포함하세요. 매칭된 각 장비에 대해 단일 'full_config' 텍스트와 "
                "공식 가이드/데이터시트로 구성된 'references' 리스트가 함께 반환됩니다. "
                "Copilot Studio 에이전트는 이 결과를 사용자가 업로드한 컨피그와 비교해 "
                "변경 가이드를 생성할 수 있습니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "장비 검색 쿼리. 예: 'cisco asr 9000', 'cisco asr9k', "
                            "'asr 9000', '시스코 asr9k'."
                        ),
                    },
                },
                "required": ["query"],
            },
        ),
    ]


def _format_no_match() -> str:
    devices = loader.list_devices()
    payload = {
        "matches": [],
        "message": (
            "쿼리에 해당하는 표준 컨피그레이션을 찾지 못했습니다. "
            "지원되는 장비 목록을 참조하여 다시 시도하세요."
        ),
        "supported_devices": devices,
        "examples": [
            "cisco asr 9000",
            "cisco asr9k",
            "시스코 asr9000",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _format_matches(query: str, matches: list[dict]) -> str:
    payload = {
        "query": query,
        "match_count": len(matches),
        "matches": matches,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    arguments = arguments or {}

    if name != "get_standard_config":
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    query = (arguments.get("query") or "").strip()
    if not query:
        return [
            types.TextContent(
                type="text",
                text="Missing required parameter 'query'.",
            )
        ]

    matches = loader.match_device(query)
    if not matches:
        return [types.TextContent(type="text", text=_format_no_match())]

    return [types.TextContent(type="text", text=_format_matches(query, matches))]


async def main() -> None:
    """Stdio entrypoint (for local development / debugging)."""
    loader.load_catalog()
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="network_config",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
