"""
YouTube MCP Server – YouTube 영상 검색 및 정보 조회

yt-dlp 기반으로 API 키 없이 YouTube 검색 결과를 가져옵니다.
Provides 2 tools:
1. search-youtube: 키워드로 YouTube 영상 검색 (sp 필터 지원)
2. get-video-details: 특정 영상의 상세 정보 조회
"""

import asyncio
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

from .tools import (
    search_youtube,
    get_video_details,
    format_search_results,
    format_video_details,
    SP_PRESETS,
)

server = Server("youtube_search")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search-youtube",
            description=(
                "YouTube에서 키워드로 영상을 검색합니다. "
                "조회수순, 업로드일순, 평점순 등 정렬 필터를 지원하며, "
                "기간 필터(오늘/이번주/이번달/올해)도 사용할 수 있습니다. "
                "YouTube의 sp 파라미터를 직접 전달할 수도 있습니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색 키워드 (예: '로봇', 'AI robot', '인공지능')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "반환할 최대 영상 수 (기본 5, 최대 20)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                    "sort_filter": {
                        "type": "string",
                        "description": (
                            "정렬 및 기간 필터 프리셋. 선택지: "
                            + ", ".join(f"{k}" for k in SP_PRESETS.keys())
                        ),
                        "enum": list(SP_PRESETS.keys()),
                    },
                    "sp": {
                        "type": "string",
                        "description": (
                            "YouTube sp 필터 파라미터 (직접 지정). "
                            "sort_filter보다 우선합니다. "
                            "예: 'CAMSAggD' (조회수순+이번주)"
                        ),
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get-video-details",
            description=(
                "특정 YouTube 영상의 상세 정보를 조회합니다: "
                "제목, 채널, 조회수, 좋아요, 댓글 수, 길이, 업로드일, 태그, 설명. "
                "영상 URL 또는 video ID를 입력합니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "video_url": {
                        "type": "string",
                        "description": (
                            "YouTube 영상 URL 또는 video ID. "
                            "예: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' 또는 'dQw4w9WgXcQ'"
                        ),
                    },
                },
                "required": ["video_url"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None,
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if not arguments:
        arguments = {}

    if name == "search-youtube":
        query = arguments.get("query")
        if not query:
            return [types.TextContent(type="text", text="'query' 파라미터가 필요합니다.")]

        max_results = min(arguments.get("max_results", 5), 20)
        sp = arguments.get("sp")
        sp_preset = arguments.get("sort_filter")

        result = await search_youtube(
            query=query,
            max_results=max_results,
            sp=sp,
            sp_preset=sp_preset,
        )

        if isinstance(result, str):
            return [types.TextContent(type="text", text=result)]

        text = format_search_results(result, query)
        return [types.TextContent(type="text", text=text)]

    elif name == "get-video-details":
        video_url = arguments.get("video_url")
        if not video_url:
            return [types.TextContent(type="text", text="'video_url' 파라미터가 필요합니다.")]

        result = await get_video_details(video_url)

        if isinstance(result, str):
            return [types.TextContent(type="text", text=result)]

        text = format_video_details(result)
        return [types.TextContent(type="text", text=text)]

    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="youtube_search",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
