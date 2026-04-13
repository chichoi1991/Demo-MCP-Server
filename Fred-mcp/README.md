# FRED Economic Data MCP Server

미국 경제 데이터 인사이트를 AI 에이전트에서 바로 활용할 수 있는 MCP(Model Context Protocol) 서버입니다.  
[FRED (Federal Reserve Economic Data)](https://fred.stlouisfed.org/) API를 통해 81만개 이상의 경제 시계열 데이터에 접근합니다.

소비 수요, 원자재·환율, 거시경제, 산업 생산, EV·에너지 등 **비즈니스 의사결정에 직결되는 5개 테마 도구 + 1개 검색 도구**를 제공합니다.

### 누가 사용할 수 있나요?

- **기업 경영진/전략팀** — 시장 진입, 설비 투자, 가격 정책 판단을 위한 거시경제 데이터 조회
- **금융 애널리스트** — 금리, 인플레이션, 산업 생산 트렌드 모니터링
- **데이터 사이언티스트/리서처** — AI 에이전트를 통한 경제 시계열 분석 자동화
- **제조업 SCM/구매팀** — 원자재(구리·철강·플라스틱) 가격 동향 추적
- **자동차/EV 산업 관계자** — 차량 판매, 유가, 생산지수 등 시장 분석

---

## 프로젝트 구조

```
Fred-mcp/
├── Dockerfile                  # Azure Container Apps용 Docker 빌드
├── azure.yaml                  # azd 배포 설정
├── pyproject.toml              # Python 의존성 정의
├── README.md
├── ENVIRONMENT_SETUP.md        # 환경 설정 가이드
├── COPILOT_STUDIO_SETUP.md     # Copilot Studio 연결 가이드
├── infra/                      # Azure Bicep IaC
│   ├── main.bicep
│   ├── main.parameters.json
│   ├── resources.bicep
│   ├── abbreviations.json
│   └── modules/
│       └── fetch-container-image.bicep
└── src/fred_mcp/
    ├── __init__.py             # 패키지 엔트리포인트
    ├── tools.py                # FRED API 호출 + 시리즈별 매핑 + 포매팅
    ├── server.py               # MCP 서버 (6개 도구 정의)
    └── http_server.py          # Streamable HTTP 래퍼 (Azure 배포용)
```

### 핵심 파일 설명

| 파일 | 역할 |
|------|------|
| `tools.py` | FRED API 호출 헬퍼, 5개 테마별 시리즈 ID 매핑, 응답 포매팅, 시리즈 검색 |
| `server.py` | MCP 프로토콜로 6개 도구를 등록하고 호출을 처리 (stdio 모드) |
| `http_server.py` | `server.py`를 Streamable HTTP로 래핑하여 Azure Container Apps에서 서비스 |
| `resources.bicep` | Container Registry, Container Apps, Managed Identity, Application Insights 프로비저닝 |

### 데이터 흐름

```
Copilot Studio → HTTP POST /mcp (x-fred-api-key 헤더)
  → http_server.py (API Key 추출 → MCP Transport)
    → server.py (도구 라우팅)
      → tools.py (FRED API 호출 → 포매팅)
        → https://api.stlouisfed.org/fred/series/observations
```

---

## 도구 상세 설계

### Tool 1: `get-consumer-demand` (소비 수요 지표)

**왜 필요한가:** 내구재·주택·자동차 등 소비 지출의 선행지표

| 시리즈 ID | 설명 | 의미 |
|-----------|------|------|
| `PCEDG` | 내구재 개인소비지출 | 가전·전자제품 직접 수요 |
| `UMCSENT` | 미시건대 소비자심리지수 | 고가 내구재 구매 의향 선행지표 |
| `HOUST` | 신규주택착공건수 | 가전·건자재 수요 선행지표 |
| `HSN1F` | 신규주택판매 | 빌트인 가전·인테리어 수요 |
| `TOTALSA` | 자동차 총판매 | 자동차·부품 산업 수요 |

```json
{
  "indicator": "PCEDG",       // 특정 지표만 (생략 시 전체 조회)
  "period": "1y",             // 6m | 1y | 3y | 5y
  "units": "pc1"              // lin | chg | pch | pc1 | pca | log
}
```

→ "미국 내구재 소비 전망이 어때?" 같은 질문에 종합 판단 근거 제공

---

### Tool 2: `get-cost-pressure` (원가/마진 압박 지표)

**왜 필요한가:** 제조원가와 환율이 수익성을 좌우

| 시리즈 ID | 설명 | 의미 |
|-----------|------|------|
| `DEXKOUS` | 원/달러 환율 | 수출입 환산, 원자재 수입 비용 |
| `DCOILWTICO` | WTI 유가 | 물류비, 에너지·화학 원재료 |
| `WPUSI012011` | PPI: 구리 | 전선·모터·PCB 등 핵심 원자재 |
| `WPU101` | PPI: 철강 | 구조재, 외판, 건설자재 |
| `PCU325211325211` | PPI: 합성수지 | 플라스틱 부품·포장재 원가 |

```json
{
  "indicator": "DEXKOUS",
  "period": "1y",
  "units": "pch"
}
```

→ "원자재 가격 추세가 마진에 미칠 영향은?" 에 대응

---

### Tool 3: `get-macro-environment` (거시경제 환경)

**왜 필요한가:** 투자·설비확장·채권발행 등 전략적 의사결정의 배경

| 시리즈 ID | 설명 | 의미 |
|-----------|------|------|
| `GDPC1` | 실질 GDP | 미국 시장 전체 경기 |
| `CPIAUCSL` | CPI (전체) | 인플레이션 → 소비자 구매력 |
| `CPIDURASL` | CPI: 내구재 | 내구재 제품 가격 동향 |
| `FEDFUNDS` | 연방기금금리 | 할부금융 비용, 투자 환경 |
| `UNRATE` | 실업률 | 소비 여력 |
| `DGS10` | 10년 국채금리 | 부동산·설비투자 환경 |
| `DGS2` | 2년 국채금리 | 장단기 금리 역전 = 침체 신호 |

```json
{
  "indicator": "FEDFUNDS",
  "period": "3y",
  "units": "lin"
}
```

→ "미국 경기 침체 가능성은?" — `DGS10`과 `DGS2`를 함께 조회하여 금리 역전 여부를 확인

---

### Tool 4: `get-industry-production` (산업/제조 동향)

**왜 필요한가:** 글로벌 제조업 경기와 공급망 상황 파악

| 시리즈 ID | 설명 | 의미 |
|-----------|------|------|
| `INDPRO` | 산업생산지수 | 제조업 전반 |
| `DGORDER` | 내구재 신규주문 | 수주 트렌드 |
| `AMTMNO` | 전체 제조업 신규주문 | 향후 생산 파이프라인 |
| `IPMAN` | 제조업 생산지수 | 공장 가동률 |

```json
{
  "indicator": "INDPRO",
  "period": "3y",
  "units": "pc1"
}
```

→ "미국 제조업 경기가 공장 신설/증설 투자에 적합한 시점인가?"

---

### Tool 5: `get-ev-energy-market` (EV·에너지 시장)

**왜 필요한가:** EV 전환이 자동차·부품·에너지 산업 전체를 재편

| 시리즈 ID | 설명 | 의미 |
|-----------|------|------|
| `TOTALSA` | 자동차 총판매 | 전체 시장 규모 |
| `AISRSA` | 자동차 재고/판매 비율 | 재고 과잉/부족 |
| `DCOILWTICO` | WTI 유가 | 유가↑ → EV 수요↑ |
| `GASREGW` | 휘발유 소매가격 | 소비자 EV 전환 동기 |
| `IPG3361T3S` | 자동차 생산지수 | OEM 생산 활동 → 부품 수요 |

```json
{
  "indicator": "GASREGW",
  "period": "3y",
  "units": "pch"
}
```

→ "EV 전환 가속화 조건이 형성되고 있는가?"

---

### Tool 6: `search-fred-series` (시리즈 검색)

**왜 필요한가:** 프리셋 5개 테마 외 추가 지표 탐색

```json
{
  "query": "semiconductor production",
  "limit": 10
}
```

→ 키워드로 FRED 데이터베이스(81만+ 시리즈)를 검색하여 시리즈 ID, 제목, 빈도, 단위, 인기도를 반환

---

## 복합 분석 시나리오 (도구 조합)

| 질문 예시 | 도구 조합 |
|----------|----------|
| "올해 미국 내구재 소비 전망은?" | Tool 1 (주택착공 + 소비심리) + Tool 3 (GDP + 고용) |
| "환율 변동에 따른 가격 전략은?" | Tool 2 (환율) + Tool 3 (CPI 내구재) |
| "미국 공장 증설 타이밍이 맞나?" | Tool 3 (금리) + Tool 4 (산업생산 + 수주) |
| "자동차 부품 투자를 확대할까?" | Tool 5 (차량판매 + 유가) + Tool 1 (자동차판매) |
| "경기 침체 가능성과 대비 전략은?" | Tool 3 (금리역전 + GDP + 실업률) + Tool 2 (원자재) |
| "원자재 수급이 안정적인가?" | Tool 2 (구리 + 철강 + 합성수지 PPI) |
| "EV 전환이 가속화되고 있는가?" | Tool 5 (유가 + 차량판매 + 자동차생산) |

---

## 파라미터 설명

### period (조회 기간)
| 값 | 설명 |
|----|------|
| `6m` | 최근 6개월 |
| `1y` | 최근 1년 (기본값) |
| `3y` | 최근 3년 |
| `5y` | 최근 5년 |

### units (데이터 변환)
| 값 | 설명 | 추천 상황 |
|----|------|----------|
| `lin` | 원본 수치 (기본값) | 절대값 확인 |
| `chg` | 전기 대비 변화량 | 단기 증감 |
| `pch` | 전기 대비 변화율 (%) | 월간/분기 트렌드 |
| `pc1` | 전년 동기 대비 변화율 (%) | **경영 보고·트렌드 분석에 가장 추천** |
| `pca` | 연율화된 복리 변화율 | 연율 환산 비교 |
| `log` | 자연로그 | 통계 분석용 |

### indicator (개별 지표)
각 도구는 특정 시리즈 ID를 `indicator`로 지정하여 개별 지표만 조회할 수 있습니다.  
생략하면 해당 테마의 **모든 지표를 한번에** 조회합니다.

---

## 구현 설계 원칙

1. **`fred/series/observations`가 핵심** — 5개 테마 도구 모두 이 엔드포인트 하나로 데이터를 가져옴
2. **`fred/series/search`는 보조** — 새로운 지표 탐색용 검색 도구로 추가
3. **`units=pc1` (전년대비 변화율)을 권장** — 의사결정자에게는 절대값보다 추세가 중요
4. **여러 시리즈를 한 도구에서 묶어서 반환** — 개별 시리즈 호출보다 테마별 종합 조회가 실용적
5. **기존 News API MCP의 구조를 그대로 계승** — `tools.py` / `server.py` / `http_server.py` 3파일 구조

---

## 빠른 시작

### 1. FRED API Key 발급

[https://fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html) 에서 무료 API Key를 발급받습니다.

### 2. Docker 빌드 및 실행

```bash
docker build -t fred-mcp .
docker run -p 3000:3000 -e FRED_API_KEY=your_32_character_api_key fred-mcp
```

### 3. Azure Container Apps 배포

```bash
azd auth login
azd init
azd up
```

배포 후 API Key는 요청 헤더 `x-fred-api-key`로 전달합니다.

---

## 인증 방법

| 방법 | 우선순위 | 설명 |
|------|:-------:|------|
| `x-fred-api-key` 헤더 | 1 | HTTP 요청 헤더에 API Key 포함 (Copilot Studio 권장) |
| `api-key` 헤더 | 2 | 대체 헤더명 |
| `x-api-key` 헤더 | 3 | 대체 헤더명 |
| `Authorization: Bearer <key>` | 4 | Bearer 토큰 형식 |
| `FRED_API_KEY` 환경 변수 | 5 | 서버 환경 변수 (Docker/Azure 설정) |

---

## 라이선스

MIT
