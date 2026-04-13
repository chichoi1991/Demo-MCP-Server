# FRED MCP 서버 환경 설정 가이드

## 1. API Key 발급

FRED API는 무료로 사용 가능하며, API Key 발급이 필요합니다.

1. [FRED API Key 신청 페이지](https://fred.stlouisfed.org/docs/api/api_key.html) 접속
2. 이메일로 계정 생성 후 API Key 발급
3. 32자리 영숫자 소문자 키가 이메일로 전달됨

> **참고:** FRED API는 요청 횟수 제한이 관대합니다 (일반적으로 초당 120회 이내 권장)

## 2. MCP 도구 설명

### get-consumer-demand (소비 수요 지표)
미국 소비자 수요와 가전/TV 전방 시장 지표를 조회합니다.

| 시리즈 ID | 설명 |
|-----------|------|
| PCEDG | 내구재 개인소비지출 (가전·TV 직접 수요) |
| UMCSENT | 미시건대 소비자심리지수 |
| HOUST | 신규주택착공건수 (가전 수요 선행지표) |
| HSN1F | 신규주택판매 |
| TOTALSA | 총 자동차 판매 |

### get-cost-pressure (원가/마진 압박 지표)
제조업 원가에 직결되는 환율, 원자재 동향을 조회합니다.

| 시리즈 ID | 설명 |
|-----------|------|
| DEXKOUS | 원/달러 환율 |
| DCOILWTICO | WTI 원유가격 |
| WPUSI012011 | PPI: 구리 |
| WPU101 | PPI: 철강 |
| PCU325211325211 | PPI: 합성수지 |

### get-macro-environment (거시경제 환경)
미국 거시경제 전반의 건강 상태를 파악합니다.

| 시리즈 ID | 설명 |
|-----------|------|
| GDPC1 | 실질 GDP |
| CPIAUCSL | CPI 전체 |
| CPIDURASL | CPI 내구재 |
| FEDFUNDS | 연방기금금리 |
| UNRATE | 실업률 |
| DGS10 | 10년 국채금리 |
| DGS2 | 2년 국채금리 |

### get-industry-production (산업/제조 동향)
미국 제조업 경기와 수주 동향을 파악합니다.

| 시리즈 ID | 설명 |
|-----------|------|
| INDPRO | 산업생산지수 |
| DGORDER | 내구재 신규주문 |
| AMTMNO | 전체 제조업 신규주문 |
| IPMAN | 제조업 생산지수 |

### get-ev-energy-market (EV/에너지 시장)
EV/자동차 시장 동향을 분석합니다.

| 시리즈 ID | 설명 |
|-----------|------|
| TOTALSA | 총 자동차 판매 |
| AISRSA | 자동차 재고/판매 비율 |
| DCOILWTICO | WTI 원유가격 |
| GASREGW | 휘발유 소매가격 |
| IPG3361T3S | 자동차 및 부품 생산지수 |

### search-fred-series (시리즈 검색)
키워드로 FRED 데이터베이스를 검색하여 추가 지표를 탐색합니다.

## 3. 배포 방법

### 로컬 실행
```bash
# 환경 변수 설정
export FRED_API_KEY=your_api_key_here

# 설치 및 실행 (stdio 모드)
pip install -e .
fred-mcp

# HTTP 서버 모드
uvicorn src.fred_mcp.http_server:app --host 0.0.0.0 --port 3000
```

### Docker 실행
```bash
docker build -t fred-mcp .
docker run -p 3000:3000 -e FRED_API_KEY=your_api_key_here fred-mcp
```

### Azure Container Apps 배포
```bash
azd auth login
azd init
azd up
```

## 4. 인증 방법

API Key는 다음 방법으로 전달할 수 있습니다:

| 방법 | 우선순위 | 설명 |
|------|---------|------|
| `x-fred-api-key` 헤더 | 1 (최우선) | HTTP 요청 헤더에 API Key 포함 |
| `api-key` 헤더 | 2 | 대체 헤더명 |
| `x-api-key` 헤더 | 3 | 대체 헤더명 |
| `Authorization: Bearer <key>` | 4 | Bearer 토큰 형식 |
| `FRED_API_KEY` 환경 변수 | 5 (최후) | 서버 환경 변수 |
