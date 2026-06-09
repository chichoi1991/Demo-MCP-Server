# YouTube MCP Server

YouTube 영상 검색 및 상세 정보를 제공하는 MCP (Model Context Protocol) 서버입니다.  
`yt-dlp` 기반으로 **API 키 없이** 동작합니다.

## 도구 (Tools)

| 도구 | 설명 |
|------|------|
| `search-youtube` | 키워드로 YouTube 영상 검색 (정렬/기간 필터 지원) |
| `get-video-details` | 특정 영상의 상세 정보 조회 (조회수, 좋아요, 태그 등) |

## 로컬 실행

```bash
# 의존성 설치
pip install -e .

# stdio 모드 (MCP 클라이언트 연결용)
python -m youtube_mcp

# HTTP 모드 (Azure Container Apps / 웹 배포용)
uvicorn src.youtube_mcp.http_server:app --host 0.0.0.0 --port 3000
```

## Azure 배포

```bash
azd init
azd up
```

## 검색 필터 프리셋

| 프리셋 | 설명 | sp 값 |
|--------|------|--------|
| `relevance` | 관련성순 (기본) | - |
| `upload_date` | 업로드 날짜순 | `CAISAhAB` |
| `view_count` | 조회수순 | `CAMSAhAB` |
| `rating` | 평점순 | `CAESAhAB` |
| `view_count_today` | 조회수순 + 오늘 | `CAMSAggC` |
| `view_count_week` | 조회수순 + 이번 주 | `CAMSAggD` |
| `view_count_month` | 조회수순 + 이번 달 | `CAMSAggE` |
| `view_count_year` | 조회수순 + 올해 | `CAMSAggF` |

## 사용 예시

```json
{
  "tool": "search-youtube",
  "arguments": {
    "query": "로봇",
    "max_results": 3,
    "sort_filter": "view_count_week"
  }
}
```
