# News API MCP Server - 환경 변수 설정 가이드

## 개요
[NewsAPI.org](https://newsapi.org/) 기반의 MCP 서버입니다.
뉴스 기사 검색, 헤드라인 조회, 뉴스 소스 목록 조회 기능을 MCP 도구로 제공합니다.

원본 프로젝트: [berlinbra/news-api-mcp](https://github.com/berlinbra/news-api-mcp)

## 환경 변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `NEWS_API_KEY` | **필수** | [NewsAPI.org](https://newsapi.org/) API 키 |

### API 키 발급 방법
1. https://newsapi.org/register 에서 무료 계정 생성
2. 대시보드에서 API 키 복사
3. 무료 티어: **일 100건 요청** 제한

## MCP 도구 (Tools)

| 도구 | 설명 |
|------|------|
| `search-news` | 키워드로 뉴스 기사 검색 (날짜, 소스, 언어 필터 지원) |
| `get-top-headlines` | 국가/카테고리별 최신 헤드라인 조회 |
| `get-news-sources` | 사용 가능한 뉴스 소스 목록 조회 |

## 전송 방식

- **원본**: stdio (Claude Desktop 용)
- **수정**: Streamable HTTP (`POST /mcp`) - Azure Container Apps 배포용

## 엔드포인트

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/mcp` | POST | MCP Streamable HTTP 엔드포인트 |
| `/health` | GET | 헬스체크 (API 키 설정 여부 확인) |
| `/` | GET | 서버 정보 |

## 설정 방법

### 1️⃣ 로컬 개발

```bash
# API 키 설정
export NEWS_API_KEY=your_api_key_here

# 의존성 설치 (uv 사용)
uv install -e .

# stdio 모드 실행 (원본)
uv run src/news_api_mcp/server.py

# HTTP 모드 실행 (Azure 배포용)
uvicorn src.news_api_mcp.http_server:app --host 0.0.0.0 --port 3000
```

### 2️⃣ Docker 실행

```bash
docker build -t news-api-mcp .
docker run -p 3000:3000 \
  -e NEWS_API_KEY="your_api_key_here" \
  news-api-mcp
```

### 3️⃣ Azure Container Apps 배포

```bash
azd up
```

배포 후 Azure Portal > Container App > 설정 > 환경 변수에서:
- `NEWS_API_KEY` 추가 (필수)

## 테스트

```bash
# 서버 정보
curl http://localhost:3000/

# 헬스체크
curl http://localhost:3000/health

# MCP 초기화 요청
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": { "name": "test", "version": "1.0" }
    }
  }'
```

## 참고 사항
- NewsAPI.org 무료 티어는 **일 100건** 요청 제한
- 프로덕션에서는 유료 플랜 권장
- 기본 포트: 3000
