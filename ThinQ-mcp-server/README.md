# ThinQ MCP Server

LG ThinQ IoT 플랫폼에 등록된 스마트 가전기기를 AI 에이전트에서 조회하고 제어할 수 있는 MCP(Model Context Protocol) 서버입니다.  
[ThinQ API](https://connect-pat.lgthinq.com)를 통해 디바이스 목록 조회, 상태 확인, 원격 제어, 에너지 사용량 분석 기능을 제공합니다.

---

## 프로젝트 구조

```
ThinQ-mcp-server/
├── dist/
│   └── server.js               # 컴파일된 MCP 서버 (Express + MCP SDK)
├── infra/                      # Azure Bicep IaC
│   ├── main.bicep
│   ├── main.parameters.json
│   ├── resources.bicep
│   └── modules/
├── Dockerfile
├── azure.yaml
├── package.json
├── .env.example
├── ENVIRONMENT_SETUP.md
└── COPILOT_STUDIO_SETUP.md
```

### 데이터 흐름

```
클라이언트 (Copilot Studio / VS Code)
  → HTTP POST /mcp (x-thinq-pat-token 헤더)
    → server.js (PAT Token 추출 → MCP Transport)
      → 도구 라우팅
        → https://connect-pat.lgthinq.com/v1/devices/...
```

---

## 도구 상세 (7개)

### Tool 1: `get-dad-joke` (아재 개그)

랜덤 아재 개그를 반환합니다. (데모/테스트용)

---

### Tool 2: `get-thinq-devices` (디바이스 목록 조회)

ThinQ 플랫폼에 등록된 전체 디바이스 목록을 조회합니다.  
**다른 도구를 사용하기 전에 반드시 먼저 호출**하여 `deviceId`를 확인해야 합니다.

| 파라미터 | 필수 | 설명 |
|---------|:----:|------|
| `country` | | 서비스 국가 코드 (ISO 3166-1 alpha-2, 기본값: `KR`) |

```json
{ "country": "KR" }
```

→ 각 디바이스의 `deviceId`, 모델명, 디바이스 타입, 별칭 등을 반환

---

### Tool 3: `get-thinq-device-profile` (디바이스 프로파일 조회)

특정 디바이스의 속성, 제어 가능한 명령(write 가능 속성), 알림 정보를 조회합니다.  
**디바이스 제어(`control-thinq-device`) 전에 반드시 호출**하여 허용값을 확인하세요.

| 파라미터 | 필수 | 설명 |
|---------|:----:|------|
| `deviceId` | ✅ | 디바이스 ID (`get-thinq-devices`로 확인) |
| `country` | | 서비스 국가 코드 (기본값: `KR`) |

---

### Tool 4: `get-thinq-device-state` (디바이스 상태 조회)

디바이스의 실시간 상태값(온도, 동작 모드, 문 열림 상태, 전력 절약 모드 등)을 조회합니다.

| 파라미터 | 필수 | 설명 |
|---------|:----:|------|
| `deviceId` | ✅ | 디바이스 ID |
| `country` | | 서비스 국가 코드 (기본값: `KR`) |

→ 프로파일에 정의된 속성에 대한 현재값을 반환

---

### Tool 5: `control-thinq-device` (디바이스 제어)

디바이스를 원격 제어합니다.  
**반드시 `get-thinq-device-profile`로 write 가능한 속성과 허용값을 먼저 확인 후 호출하세요.**

| 파라미터 | 필수 | 설명 |
|---------|:----:|------|
| `deviceId` | ✅ | 제어할 디바이스 ID |
| `payload` | ✅ | 제어 명령 JSON 객체 |
| `country` | | 서비스 국가 코드 (기본값: `KR`) |

```json
{
  "deviceId": "eb8ce6a9...",
  "payload": {
    "temperature": {
      "targetTemperature": 0,
      "locationName": "FRIDGE",
      "unit": "C"
    }
  }
}
```

---

### Tool 6: `get-thinq-energy-profile` (에너지 프로파일 조회)

디바이스가 제공하는 에너지 데이터 항목(전력 사용량 등)을 확인합니다.  
`get-thinq-energy-usage` 호출 전에 조회 가능한 항목을 먼저 확인하세요.

| 파라미터 | 필수 | 설명 |
|---------|:----:|------|
| `deviceId` | ✅ | 디바이스 ID |
| `country` | | 서비스 국가 코드 (기본값: `KR`) |

---

### Tool 7: `get-thinq-energy-usage` (에너지 사용량 조회)

디바이스의 에너지 사용량 데이터를 일별 또는 월별로 조회합니다.

| 파라미터 | 필수 | 설명 |
|---------|:----:|------|
| `deviceId` | ✅ | 디바이스 ID |
| `period` | ✅ | 집계 기간: `DAILY` (일별) 또는 `MONTHLY` (월별) |
| `startDate` | ✅ | 조회 시작일 (`YYYYMMDD`, 예: `20260301`) |
| `endDate` | ✅ | 조회 종료일 (`YYYYMMDD`, 예: `20260316`) |
| `country` | | 서비스 국가 코드 (기본값: `KR`) |

```json
{
  "deviceId": "eb8ce6a9...",
  "period": "DAILY",
  "startDate": "20260401",
  "endDate": "20260413"
}
```

---

## 활용 시나리오

| 질문 예시 | 도구 호출 흐름 |
|----------|--------------|
| "집에 등록된 가전 목록 보여줘" | `get-thinq-devices` |
| "냉장고 온도가 몇 도야?" | `get-thinq-devices` → `get-thinq-device-state` |
| "에어컨 온도 24도로 설정해줘" | `get-thinq-devices` → `get-thinq-device-profile` → `control-thinq-device` |
| "세탁기 이번 달 전기 사용량 알려줘" | `get-thinq-devices` → `get-thinq-energy-usage` |
| "냉장고에서 뭘 제어할 수 있어?" | `get-thinq-devices` → `get-thinq-device-profile` |

> 모든 디바이스 관련 도구는 `get-thinq-devices`를 **먼저 호출**하여 `deviceId`를 확인해야 합니다.

---

## 빠른 시작

### 1. PAT Token 발급

LG ThinQ 개발자 포털에서 PAT(Personal Access Token)을 발급받습니다.

### 2. Docker 빌드 및 실행

```bash
docker build -t thinq-mcp .
docker run -p 3000:3000 -e THINQ_PAT_TOKEN=your_pat_token thinq-mcp
```

### 3. Azure Container Apps 배포

```bash
azd auth login
azd init
azd up
```

배포 후 PAT Token은 요청 헤더 `x-thinq-pat-token`으로 전달합니다.

---

## 인증 방법

| 방법 | 우선순위 | 설명 |
|------|:-------:|------|
| `x-thinq-pat-token` 헤더 | 1 | HTTP 요청 헤더에 PAT Token 포함 (Copilot Studio 권장) |
| `THINQ_PAT_TOKEN` 환경 변수 | 2 | 서버 환경 변수 (Docker/Azure 설정) |

> API Key(`THINQ_API_KEY`)는 서버에 고정값으로 내장되어 있어 별도 설정 불필요

---

## 보안 주의사항

- PAT Token을 절대로 git에 커밋하지 마세요
- Token이 노출되면 즉시 재발급하세요
- `.env` 파일은 `.gitignore`에 포함되어 있습니다

---

## 라이선스

MIT
