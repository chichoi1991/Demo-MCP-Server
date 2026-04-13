# News API MCP Server - Copilot Studio 연동 가이드

## 개요
Azure Container Apps에 배포된 News API MCP Server를 Copilot Studio 에이전트에 MCP 도구로 연결하는 방법입니다.

## 사전 준비

1. `azd up`으로 Azure Container Apps에 배포 완료
2. 배포된 Container App URL 확인 (예: `https://newsapi-mcp-python.<region>.azurecontainerapps.io`)
3. **News API 키 발급** (아래 참조)

### News API 키 발급 방법

1. [https://newsapi.org/register](https://newsapi.org/register) 에 접속
2. 이름, 이메일, 비밀번호를 입력하여 **무료 계정 생성**
3. 가입 완료 후 대시보드에서 **API Key** 복사 (예: `a1b2c3d4e5f6...`)
4. 이 키를 아래 Copilot Studio 설정 시 `x-news-api-key` 헤더 값으로 입력

> 💡 무료 티어: 일 100건 요청 제한 / 프로덕션에서는 유료 플랜 권장

## Copilot Studio 설정

### 1. MCP 커넥터 추가

1. Copilot Studio에서 에이전트 열기
2. **도구(Tools)** 탭 → **도구 추가** → **MCP (미리 보기)** 선택
3. **MCP 서버 URL** 입력: `https://<your-container-app-url>/mcp`

### 2. API 키 인증 설정

MCP 도구 등록 화면에서 **인증(Authentication)** 설정:

1. 인증 유형: **커스텀 헤더** 선택
2. 헤더 이름: `x-news-api-key`
3. 헤더 값: 위에서 발급받은 News API 키 입력 (예: `a1b2c3d4e5f6...`)

> `Authorization: Bearer <key>` 형식도 지원됩니다.
>
> 서버에 `NEWS_API_KEY` 환경변수가 설정되어 있으면 헤더 없이도 동작하지만,
> **헤더로 전달한 키가 환경변수보다 우선 적용**됩니다.

### 3. 사용 가능한 도구

연결 후 다음 MCP 도구들이 자동으로 인식됩니다:

- **search-news**: 키워드로 뉴스 기사 검색
- **get-top-headlines**: 국가/카테고리별 헤드라인 조회
- **get-news-sources**: 뉴스 소스 목록 조회

### 4. 에이전트 지침 예시

```
당신은 최신 뉴스를 검색하고 요약해주는 뉴스 리서처 에이전트입니다.
사용자가 특정 주제에 대한 뉴스를 요청하면:
1. search-news 도구로 관련 기사를 검색합니다
2. get-top-headlines 도구로 최신 헤드라인을 확인합니다
3. 핵심 내용을 한국어로 요약하여 제공합니다
```

## 주의 사항

- Copilot Studio MCP 연동은 Streamable HTTP 전송을 사용합니다
- API 키가 헤더에도 환경변수에도 없으면 도구 호출 시 안내 에러가 반환됩니다
- NewsAPI.org 무료 티어는 일 100건 요청 제한이 있으므로, 프로덕션에서는 유료 플랜 사용을 권장합니다
