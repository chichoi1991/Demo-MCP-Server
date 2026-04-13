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

1. **get-consumer-demand** - 소비 수요 지표 (주택착공, 내구재 소비 등)
2. **get-cost-pressure** - 원가 압박 지표 (환율, 원자재 PPI 등)
3. **get-macro-environment** - 거시경제 (GDP, CPI, 금리, 실업률)
4. **get-industry-production** - 산업/제조 동향 (생산지수, 수주)
5. **get-ev-energy-market** - EV/에너지 시장 (차량판매, 유가)
6. **search-fred-series** - FRED 시리즈 검색

### 4. 테스트

Copilot Studio 테스트 채팅에서:

```
"미국 주택 착공 건수 최근 3년 추이를 알려줘"
→ get-consumer-demand(indicator="HOUST", period="3y") 호출

"원/달러 환율과 원유 가격 전년대비 변화율을 보여줘"  
→ get-cost-pressure(units="pc1") 호출

"GDP 관련 지표를 검색해줘"
→ search-fred-series(query="GDP") 호출
```

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
