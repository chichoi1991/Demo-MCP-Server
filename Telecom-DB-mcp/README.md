# Telecom-DB-mcp

CSV → **DuckDB (in-memory)** → **REST `/query`** + **MCP `/mcp`** in a single Python container, deployable to Azure Container Apps with `azd up`.

## What it does

- Loads `data/telecom_device_analysis_dummy_data.csv` (1,000 rows, 33 columns) into a DuckDB in-memory table named `devices` at startup.
- Exposes a REST API for ad-hoc SQL queries (`POST /query`) — read-only, `SELECT`/`WITH` only.
- Exposes an MCP Streamable HTTP endpoint (`/mcp`) with 4 tools that any MCP client (Copilot Studio, Claude Desktop, MCP Inspector, …) can call.
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

## Azure deployment

```powershell
azd auth login
azd init    # only first time; folder name is used as default env
azd up
```

The container image is built remotely by ACR (`remoteBuild: true`), pushed to the provisioned registry, and rolled out to a Container App with min 1 / max 5 replicas. No secrets are required because the dataset is bundled and contains only dummy data.

After `azd up` completes, the FQDN is printed; verify with:

```powershell
$fqdn = azd env get-value AZURE_RESOURCE_TELECOM_DB_MCP_PYTHON_ID  # see Azure Portal for FQDN
curl https://<fqdn>/health
```

Use `https://<fqdn>/mcp` as the MCP server URL inside Copilot Studio / Claude Desktop.

## Safety model

`/query` and the `run-sql` MCP tool both pipe through `db.safe_execute`:

- Single statement only — `;` is rejected after trimming.
- Must start with `SELECT` or `WITH`.
- Forbidden keywords (`INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|ATTACH|COPY|PRAGMA|INSTALL|LOAD|...`) are rejected.
- Hard row cap: default 10,000, max 50,000.
- Comments stripped before validation to prevent bypass.

This is not a substitute for full SQL parsing, but is sufficient against accidental writes and most casual injection attempts in a demo / read-only context.
