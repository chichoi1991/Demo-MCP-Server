# Demo MCP Servers

AI 에이전트(Copilot Studio, VS Code Copilot 등)에서 활용할 수 있는 **MCP(Model Context Protocol) 서버 3종** 데모 프로젝트입니다.  
각 서버는 독립적으로 Azure Container Apps에 배포하거나 VS Code 로컬 MCP로 실행할 수 있습니다.

---

## 프로젝트 구성

```
Demo-MCP-Server/
├── ThinQ-mcp-server/   # LG ThinQ IoT 디바이스 제어
├── News-api-mcp/       # News API 뉴스 검색
└── Fred-mcp/           # FRED 미국 경제 데이터
```

---

## 1. ThinQ MCP Server (TypeScript)

LG ThinQ API를 통해 IoT 가전기기(에어컨, 세탁기, 냉장고 등)를 조회하고 제어하는 MCP 서버입니다.

| 항목 | 내용 |
|------|------|
| **언어** | TypeScript / Node.js |
| **전송 방식** | Streamable HTTP |
| **인증** | PAT Token (`x-thinq-pat-token` 헤더) |
| **배포** | `azd up` → Azure Container Apps |

📄 상세: [ThinQ-mcp-server/ENVIRONMENT_SETUP.md](ThinQ-mcp-server/ENVIRONMENT_SETUP.md)

---

## 2. News API MCP Server (Python)

[NewsAPI.org](https://newsapi.org/)를 통해 전 세계 뉴스를 검색하고 헤드라인을 조회하는 MCP 서버입니다.

| 항목 | 내용 |
|------|------|
| **언어** | Python 3.12 |
| **전송 방식** | stdio + Streamable HTTP |
| **인증** | News API Key (`x-news-api-key` 헤더) |
| **배포** | `azd up` → Azure Container Apps |

### 도구

| 도구명 | 설명 |
|--------|------|
| `search-news` | 키워드로 뉴스 기사 검색 |
| `get-top-headlines` | 국가/카테고리별 톱 헤드라인 |
| `get-news-sources` | 뉴스 소스 목록 조회 |

📄 상세: [News-api-mcp/README.md](News-api-mcp/README.md)

---

## 3. FRED Economic Data MCP Server (Python)

[FRED (Federal Reserve Economic Data)](https://fred.stlouisfed.org/) API를 통해 미국 경제 지표를 테마별로 조회하는 MCP 서버입니다.  
소비 수요, 원자재/환율, 거시경제, 산업 생산, EV/에너지 시장 등 비즈니스 의사결정에 필요한 데이터를 제공합니다.

| 항목 | 내용 |
|------|------|
| **언어** | Python 3.12 |
| **전송 방식** | stdio + Streamable HTTP |
| **인증** | FRED API Key (`x-fred-api-key` 헤더) |
| **배포** | `azd up` → Azure Container Apps |

### 도구

| 도구명 | 설명 |
|--------|------|
| `get-consumer-demand` | 소비 수요 지표 (내구재 소비, 주택착공, 소비자심리) |
| `get-cost-pressure` | 원가/마진 압박 지표 (환율, 유가, 구리·철강·플라스틱 PPI) |
| `get-macro-environment` | 거시경제 환경 (GDP, CPI, 금리, 실업률) |
| `get-industry-production` | 산업/제조 동향 (생산지수, 수주) |
| `get-ev-energy-market` | EV/에너지 시장 (차량판매, 유가, 자동차생산) |
| `search-fred-series` | FRED 시리즈 키워드 검색 |

📄 상세: [Fred-mcp/README.md](Fred-mcp/README.md)

---

## 공통 아키텍처

세 프로젝트 모두 동일한 배포 패턴을 따릅니다:

```
클라이언트 (Copilot Studio / VS Code)
  │
  ▼ HTTP POST /mcp (API Key 헤더)
  │
Azure Container Apps
  │
  ▼ MCP Streamable HTTP Transport
  │
MCP Server (도구 라우팅)
  │
  ▼ 외부 API 호출
  │
External API (ThinQ / NewsAPI / FRED)
```

### 각 프로젝트별 Azure 배포

```bash
# 각 프로젝트 폴더에서 개별 배포
cd ThinQ-mcp-server && azd up
cd News-api-mcp && azd up
cd Fred-mcp && azd up
```

### 인증 방식 비교

| 서버 | 헤더명 | API Key 발급처 |
|------|--------|---------------|
| ThinQ | `x-thinq-pat-token` | LG ThinQ 개발자 포털 |
| News API | `x-news-api-key` | [newsapi.org](https://newsapi.org/register) |
| FRED | `x-fred-api-key` | [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) |

---

## VS Code 로컬 MCP 실행

각 프로젝트를 VS Code에서 로컬 MCP 서버로 즉시 실행할 수 있습니다.

### Python 프로젝트 (News API, FRED)

```bash
cd News-api-mcp && pip install -e .   # 또는 Fred-mcp
```

각 프로젝트의 `.vscode/mcp.json`이 자동으로 VS Code MCP 서버를 등록합니다.

### TypeScript 프로젝트 (ThinQ)

```bash
cd ThinQ-mcp-server && npm install && npm run build
```

---

## 디렉토리 구조 요약

```
Demo-MCP-Server/
│
├── ThinQ-mcp-server/           🏠 LG ThinQ IoT 디바이스 제어
│   ├── dist/                   # 컴파일된 서버
│   ├── infra/                  # Azure Bicep IaC
│   ├── Dockerfile
│   ├── azure.yaml
│   ├── package.json
│   ├── ENVIRONMENT_SETUP.md
│   └── COPILOT_STUDIO_SETUP.md
│
├── News-api-mcp/               📰 뉴스 검색 및 헤드라인
│   ├── src/news_api_mcp/       # Python 소스
│   ├── infra/                  # Azure Bicep IaC
│   ├── Dockerfile
│   ├── azure.yaml
│   ├── pyproject.toml
│   ├── README.md
│   ├── ENVIRONMENT_SETUP.md
│   └── COPILOT_STUDIO_SETUP.md
│
└── Fred-mcp/                   📊 미국 경제 데이터
    ├── src/fred_mcp/           # Python 소스
    ├── infra/                  # Azure Bicep IaC
    ├── Dockerfile
    ├── azure.yaml
    ├── pyproject.toml
    ├── README.md
    ├── ENVIRONMENT_SETUP.md
    └── COPILOT_STUDIO_SETUP.md
```

---

## 라이선스

MIT
