# Network Config MCP Server

Model Context Protocol (MCP) server that returns the **full standard operational configuration** of a network device along with a list of **vendor documentation reference links**, for use in Copilot Studio (or any MCP-capable) agents.

The current build ships with the IOS XR 26.1.x operational baseline for the **Cisco ASR 9000 Series Aggregation Services Router** (single end-to-end config covering system, AAA, management, physical interfaces, IS-IS / OSPF / BGP, MPLS LDP, QoS, security ACL, and SNMP).

## Scenario

```
User → Copilot Studio agent → MCP (this server)
            ↓                        ↓
      Vendor + Model        Full standard config + reference URL list
            ↓
     Compare against user-uploaded configuration
            ↓
     Generate change-guide document
```

This server only handles the **retrieval** step. Comparison and document generation stay in the agent.

## Tool

### `get_standard_config(query)`

Free-text query matched against vendor and/or model aliases. Returns the **entire** standard operational config in a single string plus a list of reference URLs.

| Query | Result |
| --- | --- |
| `cisco asr 9000` | Full ASR 9000 baseline + 11 reference URLs |
| `cisco asr9k` | Same as above |
| `시스코 asr9000` | Same as above (Korean alias) |
| `juniper mx` | No-match message + supported devices list |

**Response shape (truncated):**

```json
{
  "query": "cisco asr 9000",
  "match_count": 1,
  "matches": [
    {
      "vendor": "cisco",
      "model": "asr9000",
      "model_display_name": "Cisco ASR 9000 Series Aggregation Services Router",
      "os": "IOS XR",
      "os_release": "26.1.x",
      "description": "운영 환경 기준 Cisco ASR 9000 ...",
      "full_config": "!\n! Cisco ASR 9000 Series — Standard Operational Baseline\n...\nend\n",
      "references": [
        { "title": "ASR 9000 — Configuration Guides Index", "url": "https://..." },
        { "title": "System Management Configuration Guide",  "url": "https://..." },
        ...
      ],
      "score": 3
    }
  ]
}
```

## Adding more devices

Drop a new JSON file into [data/](data/) using the same schema as [data/cisco_asr9000.json](data/cisco_asr9000.json). No code changes required — `loader.py` picks up every `*.json` file at startup.

## Run locally

### stdio mode (MCP Inspector / CLI debug)

```powershell
pip install -e .
python -m network_config_mcp
```

### HTTP mode (production-equivalent)

```powershell
pip install -e .
python -m uvicorn src.network_config_mcp.http_server:app --host 0.0.0.0 --port 3000
```

Then call:

```powershell
curl -X POST http://localhost:3000/mcp `
  -H "Content-Type: application/json" `
  -H "Accept: application/json, text/event-stream" `
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'

curl -X POST http://localhost:3000/mcp `
  -H "Content-Type: application/json" `
  -H "Accept: application/json, text/event-stream" `
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_standard_config","arguments":{"query":"cisco asr 9000"}},"id":2}'
```

Health check: `GET http://localhost:3000/health`

## Deploy to Azure Container Apps

Prereqs: `azd`, Azure subscription, logged in.

```powershell
cd GitHub_Repo\Network-config-mcp
azd auth login
azd up
```

`azure.yaml` uses `remoteBuild: true`, so the Docker image is built on Azure Container Registry — local Docker is not required.

After deployment, `azd` prints the Container App FQDN. The MCP endpoint is `https://<fqdn>/mcp`.

## Project layout

```
Network-config-mcp/
├── azure.yaml                    # azd configuration (Container Apps)
├── Dockerfile                    # multi-stage Python 3.12-slim
├── pyproject.toml                # MCP / Starlette / uvicorn deps
├── data/
│   └── cisco_asr9000.json        # full standard config + reference URLs
├── infra/                        # Bicep + AVM modules
│   ├── main.bicep
│   ├── main.parameters.json
│   ├── resources.bicep
│   ├── abbreviations.json
│   └── modules/
│       └── fetch-container-image.bicep
└── src/network_config_mcp/
    ├── __init__.py               # stdio entrypoint
    ├── __main__.py               # `python -m network_config_mcp`
    ├── loader.py                 # catalog loader + query matcher
    ├── server.py                 # MCP tool definitions (stdio)
    └── http_server.py            # Streamable HTTP wrapper (Starlette)
```

## Notes

- **Authentication**: none (PoC). To add Entra ID Easy Auth, copy the bicep parameters from [Telecom-DB-mcp-auth/infra/main.bicep](../Telecom-DB-mcp-auth/infra/main.bicep).
- **Data source disclaimer**: shipped configs are reference templates derived from Cisco IOS XR 26.1.x documentation. Always validate against the release-specific guide for your device.
