# News API MCP Server

전 세계 뉴스를 AI 에이전트에서 검색하고 활용할 수 있는 MCP(Model Context Protocol) 서버입니다.  
[News API](https://newsapi.org/)를 통해 뉴스 기사 검색, 톱 헤드라인 조회, 뉴스 소스 목록 조회 기능을 제공합니다.

---

## 프로젝트 구조

```
News-api-mcp/
├── src/news_api_mcp/
│   ├── __init__.py             # 패키지 엔트리포인트
│   ├── tools.py                # News API 호출 헬퍼 + 응답 포매팅
│   ├── server.py               # MCP 서버 (3개 도구 정의)
│   └── http_server.py          # Streamable HTTP 래퍼 (Azure 배포용)
├── infra/                      # Azure Bicep IaC
├── Dockerfile
├── azure.yaml
├── pyproject.toml
├── ENVIRONMENT_SETUP.md
└── COPILOT_STUDIO_SETUP.md
```

### 데이터 흐름

```
클라이언트 (Copilot Studio / VS Code)
  → HTTP POST /mcp (x-news-api-key 헤더)
    → http_server.py (API Key 추출)
      → server.py (도구 라우팅)
        → tools.py (News API 호출)
          → https://newsapi.org/v2/
```

---

## 도구 상세

### Tool 1: `search-news` (뉴스 검색)

키워드로 전 세계 뉴스 기사를 검색합니다.

| 파라미터 | 필수 | 설명 |
|---------|:----:|------|
| `query` | ✅ | 검색 키워드 (기사 제목 및 본문에서 검색) |
| `from_date` | | 검색 시작일 (YYYY-MM-DD) |
| `to_date` | | 검색 종료일 (YYYY-MM-DD) |
| `sources` | | 뉴스 소스 필터 (쉼표 구분, 예: `bbc-news,cnn`) |
| `language` | | 언어 코드 (기본값: `en`) |
| `sort_by` | | 정렬 기준: `relevancy`, `popularity`, `publishedAt` |
| `page_size` | | 페이지당 결과 수 (최대 100, 기본값: 20) |
| `page` | | 페이지 번호 (기본값: 1) |

```json
{
  "query": "artificial intelligence",
  "language": "en",
  "sort_by": "publishedAt",
  "page_size": 5
}
```

---

### Tool 2: `get-top-headlines` (톱 헤드라인)

국가, 카테고리, 소스별 최신 헤드라인을 조회합니다.

| 파라미터 | 필수 | 설명 |
|---------|:----:|------|
| `country` | | 2자리 ISO 국가 코드 (예: `us`, `kr`, `jp`) |
| `category` | | 카테고리: `business`, `entertainment`, `general`, `health`, `science`, `sports`, `technology` |
| `sources` | | 뉴스 소스 ID (쉼표 구분) |
| `query` | | 헤드라인 내 검색 키워드 |
| `page_size` | | 페이지당 결과 수 (최대 100) |
| `page` | | 페이지 번호 |

> `country`/`category`/`sources`/`query` 중 최소 1개는 필수

```json
{
  "country": "us",
  "category": "technology",
  "page_size": 10
}
```

---

### Tool 3: `get-news-sources` (뉴스 소스 목록)

제공 가능한 뉴스 소스를 카테고리, 언어, 국가별로 조회합니다.

| 파라미터 | 필수 | 설명 |
|---------|:----:|------|
| `category` | | 카테고리 필터 |
| `language` | | 언어 코드 필터 |
| `country` | | 국가 코드 필터 |

```json
{
  "category": "technology",
  "language": "en"
}
```

---

## 활용 시나리오

| 질문 예시 | 도구 |
|----------|------|
| "AI 관련 최신 뉴스 알려줘" | `search-news(query="artificial intelligence")` |
| "한국 비즈니스 헤드라인은?" | `get-top-headlines(country="kr", category="business")` |
| "BBC와 CNN 뉴스만 검색해줘" | `search-news(query="economy", sources="bbc-news,cnn")` |
| "기술 분야 영어 뉴스 소스 목록" | `get-news-sources(category="technology", language="en")` |

---

## 빠른 시작

### 1. News API Key 발급

[https://newsapi.org/register](https://newsapi.org/register) 에서 무료 API Key를 발급받습니다.  
> 무료 티어: 하루 100건 요청 제한

### 2. Docker 빌드 및 실행

```bash
docker build -t news-api-mcp .
docker run -p 3000:3000 -e NEWS_API_KEY=your_api_key news-api-mcp
```

### 3. Azure Container Apps 배포

```bash
azd auth login
azd init
azd up
```

배포 후 API Key는 요청 헤더 `x-news-api-key`로 전달합니다.

---

## 인증 방법

| 방법 | 우선순위 | 설명 |
|------|:-------:|------|
| `x-news-api-key` 헤더 | 1 | HTTP 요청 헤더에 API Key 포함 (Copilot Studio 권장) |
| `api-key` 헤더 | 2 | 대체 헤더명 |
| `x-api-key` 헤더 | 3 | 대체 헤더명 |
| `Authorization: Bearer <key>` | 4 | Bearer 토큰 형식 |
| `NEWS_API_KEY` 환경 변수 | 5 | 서버 환경 변수 (Docker/Azure 설정) |

---

## 에러 처리

| 상황 | 대응 |
|------|------|
| 요청 한도 초과 (429) | 무료 티어 하루 100건 제한 안내 |
| 잘못된 API Key (401) | 키 재확인 안내 |
| 네트워크 오류 | 연결 실패 메시지 반환 |
| 타임아웃 (30초) | 재시도 안내 |

---

## 라이선스

MIT

- [berlinbra](https://github.com/berlinbra)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This MCP server is licensed under the MIT License.
This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.
