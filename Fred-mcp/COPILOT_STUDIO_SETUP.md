# Copilot Studio에서 FRED MCP 서버 연결 가이드

## 개요

Azure Container Apps에 배포된 FRED MCP 서버를 Copilot Studio의 MCP 커넥터를 통해 연결하는 방법입니다.

## 사전 준비

1. FRED API Key 발급 완료 ([발급 페이지](https://fred.stlouisfed.org/docs/api/api_key.html))
2. Azure Container Apps에 MCP 서버 배포 완료 (`azd up`)
3. 배포된 서버 URL 확인 (예: `https://fred-mcp-python.xxxxx.azurecontainerapps.io`)

## Copilot Studio 설정

### 1. MCP 커넥터 추가

1. Copilot Studio에서 에이전트 열기
2. **도구(Tools)** → **커넥터 추가** → **MCP (Streamable HTTP)**
3. 서버 URL 입력: `https://<your-container-app-url>/mcp`

### 2. 인증 설정

**인증 유형:** Custom Header

| 설정 | 값 |
|------|-----|
| Header Name | `x-fred-api-key` |
| Header Value | `your_32_character_fred_api_key` |

### 3. 사용 가능한 도구

연결 후 다음 6개 도구가 Copilot Studio에서 자동으로 인식됩니다:

| 도구 | 설명 | 주요 시리즈 |
|------|------|------------|
| `get-consumer-demand` | 소비 수요 지표 | PCEDG, UMCSENT, HOUST, HSN1F, TOTALSA |
| `get-cost-pressure` | 원가 압박 지표 | DEXKOUS, DCOILWTICO, WPUSI019011, WPU101, PCU325211325211 |
| `get-macro-environment` | 거시경제 환경 | GDPC1, CPIAUCSL, CUSR0000SAD, FEDFUNDS, UNRATE, DGS10, DGS2 |
| `get-industry-production` | 산업/제조 동향 | INDPRO, DGORDER, AMTMNO, IPMAN |
| `get-ev-energy-market` | EV/에너지 시장 | TOTALSA, AISRSA, DCOILWTICO, GASREGW, IPG3361T3S |
| `search-fred-series` | FRED 시리즈 검색 | 키워드로 81만+ 시리즈 탐색 |

---

## 예제 프롬프트

### 소비 수요 (get-consumer-demand)

```
"미국 내구재 소비 지출이 최근 1년간 어떻게 변했어?"
"소비자심리지수 최근 3년 추이를 보여줘"
"신규주택착공건수가 늘고 있어? 최근 6개월 데이터로 알려줘"
"미국 자동차 판매량 전년대비 변화율을 보여줘"
"주택 판매와 소비자 심리 데이터를 종합해서 가전 수요 전망을 분석해줘"
"HOUST 지표 5년치 데이터를 조회해줘"
```

### 원가/마진 압박 (get-cost-pressure)

```
"원/달러 환율 최근 1년 추이를 알려줘"
"WTI 원유 가격이 최근 어떻게 움직이고 있어?"
"구리 PPI와 철강 PPI를 비교해서 보여줘"
"합성수지 가격 추세가 어떻게 돼? 전기대비 변화율로 보여줘"
"환율과 원유가격을 함께 분석해서 수입 원가 영향을 알려줘"
"최근 3년간 원자재 가격 동향을 전년대비 변화율로 보여줘"
"철강 PPI 6개월 데이터를 조회해줘"
```

### 거시경제 (get-macro-environment)

```
"미국 실질 GDP 최근 3년 추이를 보여줘"
"CPI가 최근 어떻게 변하고 있어? 인플레이션 추세를 분석해줘"
"연방기금금리 변화 추이를 3년간 보여줘"
"미국 실업률이 올라가고 있어?"
"10년물과 2년물 국채금리를 비교해서 장단기 금리 역전 여부를 확인해줘"
"내구재 CPI 추이를 보여줘. 가전제품 가격이 오르고 있는지 알고 싶어"
"GDP, 실업률, 금리를 종합해서 경기 침체 가능성을 평가해줘"
"FEDFUNDS 5년 데이터를 원본 수치로 조회해줘"
```

### 산업/제조 (get-industry-production)

```
"미국 산업생산지수 추이를 보여줘"
"내구재 신규주문이 늘고 있어?"
"제조업 신규주문 전체를 전년대비 변화율로 보여줘"
"제조업 생산지수와 신규주문을 종합해서 공장 가동 상황을 분석해줘"
"INDPRO 3년 데이터를 전년동기대비 변화율로 조회해줘"
"미국 제조업 경기가 공장 증설 투자에 적합한 시점인지 판단해줘"
```

### EV/에너지 (get-ev-energy-market)

```
"미국 자동차 총판매량 추이를 보여줘"
"자동차 재고/판매 비율이 어떻게 돼? 재고가 쌓이고 있어?"
"WTI 유가와 휘발유 소매가격을 함께 보여줘"
"자동차 생산지수 최근 1년 데이터를 조회해줘"
"유가 상승이 EV 전환을 가속화하고 있는지 분석해줘"
"휘발유 가격 3년 추이를 전기대비 변화율로 보여줘"
"차량 판매량과 재고 비율을 종합해서 자동차 시장 상황을 알려줘"
```

### 시리즈 검색 (search-fred-series)

```
"반도체 생산 관련 FRED 시리즈를 검색해줘"
"한국 GDP 데이터가 FRED에 있어?"
"consumer confidence 관련 지표를 찾아줘"
"housing starts 관련 시리즈를 5개만 검색해줘"
"semiconductor production 키워드로 검색해줘"
"electric vehicle sales 관련 데이터를 찾아줘"
"inflation expectations 지표를 검색해줘"
```

### 복합 분석 (여러 도구 조합)

```
"환율과 원자재 가격 추세를 보고, GDP와 금리 환경을 함께 분석해서 올해 제조업 투자 환경을 평가해줘"
"주택착공, 소비자심리, 내구재 소비를 종합해서 가전 시장 전망을 알려줘"
"유가, 휘발유 가격, 자동차 판매를 분석해서 EV 전환 가속화 여부를 판단해줘"
"금리 역전 여부, GDP, 실업률, 산업생산지수를 종합해서 경기 침체 가능성을 평가해줘"
"구리·철강·합성수지 PPI와 환율을 함께 보고, 제조 원가 전망을 분석해줘"
"소비자심리지수, 자동차 판매, 내구재 주문을 함께 분석해서 소비 경기를 진단해줘"
```

---

## 파라미터 가이드

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

---

## curl 테스트

배포 후 서버 상태 확인:

```bash
# 헬스 체크
curl https://<your-url>/health

# MCP 초기화 테스트
curl -X POST https://<your-url>/mcp \
  -H "Content-Type: application/json" \
  -H "x-fred-api-key: your_api_key" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```
