# Telecom-DB-mcp-auth

**Entra ID Easy Auth가 적용된** Telecom-DB-mcp 변형. 원본 [Telecom-DB-mcp](../Telecom-DB-mcp)와 코드는 동일하고, 인프라(Bicep)에 Container Apps 내장 인증을 추가하여 Entra ID 토큰이 없으면 모든 요청이 `401`로 반려됩니다.

CSV → **DuckDB (in-memory)** → **REST `/query`** + **MCP `/mcp`** in a single Python container, deployable to Azure Container Apps with `azd up`.

## What it does

- Loads `data/telecom_device_analysis_dummy_data.csv` (1,000 rows, 33 columns) into a DuckDB in-memory table named `devices` at startup.
- Exposes a REST API for ad-hoc SQL queries (`POST /query`) — read-only, `SELECT`/`WITH` only.
- Exposes an MCP Streamable HTTP endpoint (`/mcp`) with 4 tools that any MCP client (Copilot Studio, Claude Desktop, MCP Inspector, …) can call.
- **모든 엔드포인트는 Entra ID 토큰이 있어야 호출 가능** (Container Apps Built-in Auth가 토큰 검증 수행).
- Both interfaces share the same in-memory connection.

## CSV schema

The bundled CSV has columns covering customer device, plan, usage, and channel attributes:

`Customer_ID, Model_Code, Model_Name, Manufacturer, Release_Date, Activation_Date, Months_in_Use, Launch_Price, Network_Type, OS_Version, Storage_Capacity_GB, Battery_Health_Pct, Display_Size_Inch, RAM_GB, Processor, Camera_MP, Wireless_Charging, Biometric_Type, Remaining_Installment, Avg_Data_Usage_GB, Peak_Usage_Time, Wi_Fi_Ratio_Pct, Roaming_Count_1Yr, Tethering_Usage_GB, Top_App_Category, Connected_Devices_Count, Brand_Loyalty_Score, Avg_Replacement_Cycle_Months, Preferred_Channel, Subsidy_Type, Device_Insurance, Trade_in_Program, Bundling_Status, Repair_History_Count`

## REST endpoints

| Method | Path     | Description                                   |
| ------ | -------- | --------------------------------------------- |
| GET    | `/`      | Service metadata                              |
| GET    | `/health` | DB health + row count                        |
| GET    | `/schema` | Table columns + sample rows                  |
| POST   | `/query`  | `{ "sql": "SELECT ...", "params": [], "limit": 10000 }` |
| ANY    | `/mcp`    | MCP Streamable HTTP transport                |

### Query example

```bash
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT Manufacturer, COUNT(*) AS cnt, ROUND(AVG(Battery_Health_Pct),1) AS avg_batt FROM devices GROUP BY 1 ORDER BY cnt DESC"}'
```

Disallowed (returns `400`):

```bash
curl -X POST http://localhost:3000/query -H "Content-Type: application/json" \
  -d '{"sql":"DROP TABLE devices"}'
```

## MCP tools

| Tool name           | Purpose                                                          |
| ------------------- | ---------------------------------------------------------------- |
| `list-devices`      | Filter rows by manufacturer / model / network / OS / battery     |
| `get-device-stats`  | Group-by aggregations (count, avg battery, avg price, …)         |
| `get-table-schema`  | Columns + 5 sample rows (LLM grounding for SQL generation)       |
| `run-sql`           | Safe `SELECT` execution (forbidden keywords blocked, row capped) |

## Local run

### Python (dev mode)

```powershell
pip install -e .
python -m uvicorn src.telecom_db_mcp.http_server:app --host 0.0.0.0 --port 3000
```

### Docker

```powershell
docker build -t telecom-db-mcp .
docker run --rm -p 3000:3000 telecom-db-mcp
```

### MCP Inspector

```powershell
npx @modelcontextprotocol/inspector
# transport = Streamable HTTP, URL = http://localhost:3000/mcp
```

## Azure deployment (Entra ID Easy Auth)

### 사전 준비 — Entra ID App Registration

1. Azure Portal → **Microsoft Entra ID → App registrations → New registration**
   - Name: `Telecom-MCP-API` (예시)
   - Supported account types: 단일 테넌트
   - Redirect URI: 비워둠 (API 모드)
2. 등록 후 **Overview**에서 다음 값을 메모:
   - `Application (client) ID` → `ENTRA_CLIENT_ID`
   - `Directory (tenant) ID` → `ENTRA_TENANT_ID`
3. **Expose an API**:
   - `Application ID URI` 설정 (기본값 `api://<client-id>` 그대로 사용 권장)
   - `Add a scope`로 예: `Devices.Read` 추가 (선택)
4. **App roles** 정의 (선택, RBAC 시):
   - `TelecomReader`, `TelecomAdmin` 등
5. **Enterprise Application → Properties → Assignment required = Yes**
   - **Users and groups**에서 호출을 허용할 사용자/그룹/앱만 명시적으로 할당
   - 이 단계가 “MCP 도구 사용 가능 사용자 제한”의 핵심

### `azd up`

```powershell
cd Telecom-DB-mcp-auth
azd auth login
azd init    # 처음 한 번
azd env set ENTRA_TENANT_ID  <tenant-guid>
azd env set ENTRA_CLIENT_ID  <client-guid>
# (선택) 사용자 정의 audience를 쓸 때만:
# azd env set ENTRA_ALLOWED_AUDIENCES '["api://telecom-mcp"]'
# (선택) 디버깅 시 인증을 끄고 배포:
# azd env set ENTRA_EASY_AUTH_ENABLED false
azd up
```

배포 후 검증:

```powershell
$fqdn = "<container-app-fqdn>"  # azd 출력 또는 Azure Portal 확인

# 토큰 없이 호출 → 401 반환 (인증 적용 확인)
curl -i "https://$fqdn/health"

# Entra 토큰 발급 후 호출
$token = (az account get-access-token --resource "api://<client-id>").accessToken
curl -i "https://$fqdn/health" -H "Authorization: Bearer $token"
```

### Copilot Studio 연결

Copilot Studio에서 MCP 커넥터 등록 시:
- URL: `https://<fqdn>/mcp`
- Authentication: **OAuth 2.0 (Microsoft Entra ID)**
- Client ID / Tenant ID: 위에서 만든 App Registration 값
- Scope: `api://<client-id>/.default`

Copilot Studio가 사용자 컨텍스트로 Entra 토큰을 받아 자동으로 `Authorization: Bearer ...`을 첨부합니다. Enterprise Application의 user assignment에 포함되지 않은 사용자는 토큰 발급 단계에서 차단됩니다.

### 파라미터 요약

| 파라미터                       | 환경변수                      | 기본값 | 설명                                    |
| ------------------------------ | ----------------------------- | ------ | --------------------------------------- |
| `entraTenantId`                | `ENTRA_TENANT_ID`             | (필수) | 테넌트 GUID                             |
| `entraClientId`                | `ENTRA_CLIENT_ID`             | (필수) | API App Registration의 client ID        |
| `entraAllowedAudiences`        | `ENTRA_ALLOWED_AUDIENCES`     | `[api://<clientId>]` | 허용 audience 배열       |
| `entraEasyAuthEnabled`         | `ENTRA_EASY_AUTH_ENABLED`     | `true` | `false`로 설정 시 인증 미적용 (디버깅용)|

### 코드 수정 0줄

이 변형은 [src/](src/) 코드를 전혀 손대지 않습니다. 토큰 검증·발급 흐름은 모두 Container Apps의 인증 평면이 처리하며, 인증된 요청에는 `X-MS-CLIENT-PRINCIPAL` / `X-MS-CLIENT-PRINCIPAL-ID` 헤더가 자동 첨부되어 앱 안에서 사용자 식별이 필요할 때 활용할 수 있습니다.

## Safety model

`/query` and the `run-sql` MCP tool both pipe through `db.safe_execute`:

- Single statement only — `;` is rejected after trimming.
- Must start with `SELECT` or `WITH`.
- Forbidden keywords (`INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|ATTACH|COPY|PRAGMA|INSTALL|LOAD|...`) are rejected.
- Hard row cap: default 10,000, max 50,000.
- Comments stripped before validation to prevent bypass.

This is not a substitute for full SQL parsing, but is sufficient against accidental writes and most casual injection attempts in a demo / read-only context.
