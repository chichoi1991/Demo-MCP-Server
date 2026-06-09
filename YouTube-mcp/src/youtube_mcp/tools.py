"""
YouTube MCP Tools Module

yt-dlp 기반 YouTube 검색 및 영상 정보 추출 유틸리티.
API 키 없이 YouTube 검색 결과를 가져올 수 있습니다.
"""

from typing import Any, Dict, List, Optional
import asyncio
import logging
import re

import yt_dlp

logger = logging.getLogger(__name__)

# ── SP filter presets ────────────────────────────────────────────────
# YouTube sp parameter는 protobuf 인코딩된 필터입니다.
# 자주 쓰는 조합을 프리셋으로 제공합니다.

SP_PRESETS = {
    "relevance": None,                  # 기본 (관련성)
    "upload_date": "CAISAhAB",          # 업로드 날짜순
    "view_count": "CAMSAhAB",           # 조회수순
    "rating": "CAESAhAB",              # 평점순
    "view_count_today": "CAMSAggC",     # 조회수순 + 오늘
    "view_count_week": "CAMSAggD",      # 조회수순 + 이번 주 (사용자 원본 쿼리와 동일 패턴)
    "view_count_month": "CAMSAggE",     # 조회수순 + 이번 달
    "view_count_year": "CAMSAggF",      # 조회수순 + 올해
}


def _build_search_url(query: str, sp: Optional[str] = None) -> str:
    """Build a YouTube search URL with optional sp filter."""
    from urllib.parse import quote
    url = f"https://www.youtube.com/results?search_query={quote(query)}"
    if sp:
        url += f"&sp={sp}"
    return url


def _extract_video_info(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant fields from a yt-dlp entry."""
    video_id = entry.get("id", "")
    return {
        "title": entry.get("title", "N/A"),
        "video_id": video_id,
        "url": entry.get("url") or entry.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}",
        "channel": entry.get("channel") or entry.get("uploader") or "N/A",
        "channel_url": entry.get("channel_url") or entry.get("uploader_url"),
        "duration_string": entry.get("duration_string") or _format_duration(entry.get("duration")),
        "view_count": entry.get("view_count"),
        "upload_date": _format_date(entry.get("upload_date")),
        "description": _truncate(entry.get("description") or "", 200),
        "thumbnail": entry.get("thumbnail"),
    }


def _format_duration(seconds) -> Optional[str]:
    if seconds is None:
        return None
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _format_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str or len(date_str) != 8:
        return date_str
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


async def search_youtube(
    query: str,
    max_results: int = 5,
    sp: Optional[str] = None,
    sp_preset: Optional[str] = None,
) -> List[Dict[str, Any]] | str:
    """Search YouTube and return video information.

    Args:
        query: 검색 키워드
        max_results: 반환할 최대 영상 수 (1~20)
        sp: YouTube sp 필터 파라미터 (직접 지정)
        sp_preset: SP_PRESETS 키 (sp보다 우선순위 낮음)

    Returns:
        영상 정보 딕셔너리 리스트 또는 에러 문자열
    """
    # Resolve sp filter
    effective_sp = sp
    if not effective_sp and sp_preset:
        effective_sp = SP_PRESETS.get(sp_preset)

    # Build search target
    if effective_sp:
        search_url = _build_search_url(query, effective_sp)
    else:
        search_url = f"ytsearch{max_results}:{query}"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "ignoreerrors": True,
    }

    # When using URL with sp filter, limit results
    if effective_sp:
        ydl_opts["playlistend"] = max_results

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _sync_extract, search_url, ydl_opts)
    except Exception as e:
        return f"YouTube 검색 중 오류 발생: {e}"

    if isinstance(result, str):
        return result

    entries = result.get("entries", [])
    if not entries:
        return f"'{query}' 검색 결과가 없습니다."

    videos = []
    for entry in entries[:max_results]:
        if entry and entry.get("id"):
            videos.append(_extract_video_info(entry))

    return videos


def _sync_extract(url: str, opts: dict) -> Dict[str, Any] | str:
    """Synchronous yt-dlp extraction (runs in thread executor)."""
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            result = ydl.extract_info(url, download=False)
            if result is None:
                return "검색 결과를 가져올 수 없습니다."
            return result
    except yt_dlp.utils.DownloadError as e:
        return f"YouTube 접근 오류: {e}"
    except Exception as e:
        return f"예상치 못한 오류: {e}"


async def get_video_details(video_url: str) -> Dict[str, Any] | str:
    """Get detailed information for a specific YouTube video.

    Args:
        video_url: YouTube 영상 URL 또는 video ID

    Returns:
        영상 상세 정보 딕셔너리 또는 에러 문자열
    """
    # Normalize input: support video ID or full URL
    if not video_url.startswith("http"):
        video_url = f"https://www.youtube.com/watch?v={video_url}"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": True,
    }

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _sync_extract, video_url, ydl_opts)
    except Exception as e:
        return f"영상 정보 조회 중 오류 발생: {e}"

    if isinstance(result, str):
        return result

    return {
        "title": result.get("title", "N/A"),
        "video_id": result.get("id", ""),
        "url": result.get("webpage_url", video_url),
        "channel": result.get("channel") or result.get("uploader") or "N/A",
        "channel_url": result.get("channel_url"),
        "duration_string": result.get("duration_string") or _format_duration(result.get("duration")),
        "view_count": result.get("view_count"),
        "like_count": result.get("like_count"),
        "comment_count": result.get("comment_count"),
        "upload_date": _format_date(result.get("upload_date")),
        "description": _truncate(result.get("description") or "", 500),
        "tags": (result.get("tags") or [])[:10],
        "categories": result.get("categories"),
        "thumbnail": result.get("thumbnail"),
    }


def format_search_results(videos: List[Dict[str, Any]], query: str) -> str:
    """Format search results into readable text."""
    if not videos:
        return f"'{query}' 검색 결과가 없습니다."

    lines = [f"## YouTube 검색 결과: '{query}' (총 {len(videos)}건)\n"]

    for i, v in enumerate(videos, 1):
        view_str = f"{v['view_count']:,}회" if v.get("view_count") else "N/A"
        duration_str = v.get("duration_string") or "N/A"
        date_str = v.get("upload_date") or "N/A"

        lines.append(
            f"### {i}. {v['title']}\n"
            f"- **채널**: {v['channel']}\n"
            f"- **조회수**: {view_str}\n"
            f"- **길이**: {duration_str}\n"
            f"- **업로드**: {date_str}\n"
            f"- **URL**: {v['url']}\n"
        )

    return "\n".join(lines)


def format_video_details(video: Dict[str, Any]) -> str:
    """Format video details into readable text."""
    view_str = f"{video['view_count']:,}회" if video.get("view_count") else "N/A"
    like_str = f"{video['like_count']:,}" if video.get("like_count") else "N/A"
    comment_str = f"{video['comment_count']:,}" if video.get("comment_count") else "N/A"
    duration_str = video.get("duration_string") or "N/A"
    date_str = video.get("upload_date") or "N/A"
    tags_str = ", ".join(video.get("tags", [])) if video.get("tags") else "없음"

    lines = [
        f"## {video['title']}\n",
        f"- **채널**: {video['channel']}",
        f"- **URL**: {video['url']}",
        f"- **조회수**: {view_str}",
        f"- **좋아요**: {like_str}",
        f"- **댓글 수**: {comment_str}",
        f"- **길이**: {duration_str}",
        f"- **업로드**: {date_str}",
        f"- **태그**: {tags_str}",
        f"\n### 설명\n{video.get('description', 'N/A')}",
    ]

    return "\n".join(lines)
