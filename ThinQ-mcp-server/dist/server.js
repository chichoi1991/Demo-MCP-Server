import express from "express";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod/v3";
import { randomBytes } from "crypto";
import { AsyncLocalStorage } from "async_hooks";
import dotenv from "dotenv";
dotenv.config();
// 요청별 PAT Token을 저장하기 위한 AsyncLocalStorage
const asyncLocalStorage = new AsyncLocalStorage();
// 환경 변수에서 기본 PAT Token 로드 (없어도 동작 - 커스텀 헤더에서 받을 수 있음)
const DEFAULT_THINQ_PAT_TOKEN = process.env.THINQ_PAT_TOKEN || "";
const THINQ_API_KEY = "v6GFvkweNo7DK7yD3ylIZ9w52aKBU0eJ7wLXkSR3";
const THINQ_BASE_URL = process.env.THINQ_BASE_URL || "https://api-kic.lgthinq.com";
function buildThinQHeaders(country = "KR") {
    // 현재 요청에서 저장된 PAT Token 가져오기 (없으면 환경 변수 사용)
    const store = asyncLocalStorage.getStore();
    const patToken = store?.patToken || DEFAULT_THINQ_PAT_TOKEN;
    if (!patToken) {
        throw new Error("PAT Token이 필요합니다. 요청 헤더에 x-thinq-pat-token: <token> 형식으로 전달하세요.");
    }
    const messageId = randomBytes(16).toString("base64url").slice(0, 22);
    return {
        "Authorization": `Bearer ${patToken}`,
        "x-message-id": messageId,
        "x-country": country,
        "x-client-id": "mcp-thinq-client-001",
        "x-api-key": THINQ_API_KEY,
    };
}
const server = new McpServer({
    name: "mcp-streamable-http",
    version: "1.0.0",
});
// Get Dad joke tool
server.registerTool("get-dad-joke", {
    description: "Get a random dad joke",
}, async () => {
    const response = await fetch("https://icanhazdadjoke.com/", {
        headers: { Accept: "application/json" },
    });
    const data = await response.json();
    return {
        content: [{ type: "text", text: data.joke }],
    };
});
// LG ThinQ: 디바이스 목록 조회
server.registerTool("get-thinq-devices", {
    description: "LG ThinQ 플랫폼에 등록된 디바이스 목록을 조회합니다 (GET /devices). 다른 디바이스 API를 사용하기 전에 반드시 먼저 호출하여 deviceId를 확인해야 합니다. 응답에는 각 디바이스의 deviceId와 deviceInfo(모델명, 디바이스 타입, 별칭 등)가 포함됩니다.",
    inputSchema: {
        country: z.string().optional().describe("서비스 국가 코드. ISO 3166-1 alpha-2 형식 (예: KR, US, GB). 기본값: KR"),
    },
}, async ({ country }) => {
    const response = await fetch(`${THINQ_BASE_URL}/devices`, {
        headers: buildThinQHeaders(country ?? "KR"),
    });
    const data = await response.json();
    if (!response.ok) {
        return {
            content: [{ type: "text", text: `오류 ${response.status}: ${JSON.stringify(data)}` }],
        };
    }
    return {
        content: [{ type: "text", text: JSON.stringify(data.response, null, 2) }],
    };
});
// LG ThinQ: 디바이스 프로파일 조회
server.registerTool("get-thinq-device-profile", {
    description: "LG ThinQ 디바이스의 프로파일을 조회합니다 (GET /devices/{deviceId}/profile). 프로파일에는 디바이스의 속성(property), 제어 가능한 명령(write 가능 속성), 알림(notification) 정보가 포함됩니다. 디바이스를 제어(control-thinq-device)하기 전에 이 API로 write 가능한 속성과 허용값을 반드시 확인하세요.",
    inputSchema: {
        deviceId: z.string().describe("조회할 디바이스의 ID. get-thinq-devices로 먼저 목록을 조회하여 얻은 deviceId 값을 사용하세요. 예: eb8ce6a99e63beb7e2074409bc244f3fd6c534e40ca270b6895371f12b398660"),
        country: z.string().optional().describe("서비스 국가 코드. ISO 3166-1 alpha-2 형식 (예: KR, US, GB). 기본값: KR"),
    },
}, async ({ deviceId, country }) => {
    const response = await fetch(`${THINQ_BASE_URL}/devices/${encodeURIComponent(deviceId)}/profile`, {
        headers: buildThinQHeaders(country ?? "KR"),
    });
    const data = await response.json();
    if (!response.ok) {
        return {
            content: [{ type: "text", text: `오류 ${response.status}: ${JSON.stringify(data)}` }],
        };
    }
    return {
        content: [{ type: "text", text: JSON.stringify(data.response, null, 2) }],
    };
});
// LG ThinQ: 디바이스 상태 조회
server.registerTool("get-thinq-device-state", {
    description: "LG ThinQ 디바이스의 현재 상태를 조회합니다 (GET /devices/{deviceId}/state). 디바이스의 실시간 상태값(온도, 동작 모드, 문 열림 상태, 전력 절약 모드 등)을 반환합니다. 응답 형식은 디바이스 타입에 따라 다르며, 프로파일(get-thinq-device-profile)에 정의된 속성에 대한 현재값이 포함됩니다.",
    inputSchema: {
        deviceId: z.string().describe("조회할 디바이스의 ID. get-thinq-devices로 먼저 목록을 조회하여 얻은 deviceId 값을 사용하세요. 예: eb8ce6a99e63beb7e2074409bc244f3fd6c534e40ca270b6895371f12b398660"),
        country: z.string().optional().describe("서비스 국가 코드. ISO 3166-1 alpha-2 형식 (예: KR, US, GB). 기본값: KR"),
    },
}, async ({ deviceId, country }) => {
    const response = await fetch(`${THINQ_BASE_URL}/devices/${encodeURIComponent(deviceId)}/state`, {
        headers: buildThinQHeaders(country ?? "KR"),
    });
    const data = await response.json();
    if (!response.ok) {
        return {
            content: [{ type: "text", text: `오류 ${response.status}: ${JSON.stringify(data)}` }],
        };
    }
    return {
        content: [{ type: "text", text: JSON.stringify(data.response, null, 2) }],
    };
});
// LG ThinQ: 디바이스 제어
server.registerTool("control-thinq-device", {
    description: "LG ThinQ 디바이스를 제어합니다 (POST /devices/{deviceId}/control). 반드시 get-thinq-device-profile로 프로파일을 먼저 조회하여 write 가능한 속성과 허용값을 확인한 후 호출하세요. 성공 시 빈 객체({})가 반환됩니다. 예시 - 냉장고 온도 설정: {\"temperature\": {\"targetTemperature\": 0, \"locationName\": \"FRIDGE\", \"unit\": \"C\"}}",
    inputSchema: {
        deviceId: z.string().describe("제어할 디바이스의 ID. get-thinq-devices로 먼저 목록을 조회하여 얻은 deviceId 값을 사용하세요."),
        payload: z.record(z.unknown()).describe("제어 명령 페이로드 JSON 객체. get-thinq-device-profile의 응답에서 write 가능한 속성을 기반으로 구성합니다. 예시 - 냉장고 온도: {\"temperature\": {\"targetTemperature\": 0, \"locationName\": \"FRIDGE\", \"unit\": \"C\"}}"),
        country: z.string().optional().describe("서비스 국가 코드. ISO 3166-1 alpha-2 형식 (예: KR, US, GB). 기본값: KR"),
    },
}, async ({ deviceId, payload, country }) => {
    const response = await fetch(`${THINQ_BASE_URL}/devices/${encodeURIComponent(deviceId)}/control`, {
        method: "POST",
        headers: { ...buildThinQHeaders(country ?? "KR"), "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
        return {
            content: [{ type: "text", text: `오류 ${response.status}: ${JSON.stringify(data)}` }],
        };
    }
    return {
        content: [{ type: "text", text: `제어 성공: ${JSON.stringify(data.response, null, 2)}` }],
    };
});
// LG ThinQ: 에너지 데이터 프로파일 조회
server.registerTool("get-thinq-energy-profile", {
    description: "LG ThinQ 디바이스가 제공하는 에너지 데이터의 프로파일을 조회합니다 (GET /devices/energy/{deviceId}/profile). 해당 디바이스가 어떤 에너지 데이터(전력 사용량 등)를 제공하는지 확인할 수 있습니다. get-thinq-energy-usage를 호출하기 전에 이 API로 조회 가능한 에너지 데이터 항목을 먼저 확인하세요.",
    inputSchema: {
        deviceId: z.string().describe("조회할 디바이스의 ID. get-thinq-devices로 먼저 목록을 조회하여 얻은 deviceId 값을 사용하세요."),
        country: z.string().optional().describe("서비스 국가 코드. ISO 3166-1 alpha-2 형식 (예: KR, US, GB). 기본값: KR"),
    },
}, async ({ deviceId, country }) => {
    const response = await fetch(`${THINQ_BASE_URL}/devices/energy/${encodeURIComponent(deviceId)}/profile`, {
        headers: buildThinQHeaders(country ?? "KR"),
    });
    const data = await response.json();
    if (!response.ok) {
        return {
            content: [{ type: "text", text: `오류 ${response.status}: ${JSON.stringify(data)}` }],
        };
    }
    return {
        content: [{ type: "text", text: JSON.stringify(data.response, null, 2) }],
    };
});
// LG ThinQ: 에너지 데이터 조회
server.registerTool("get-thinq-energy-usage", {
    description: "LG ThinQ 디바이스의 에너지 사용량 데이터를 조회합니다 (GET /devices/energy/{deviceId}/usage). 일별(DAILY) 또는 월별(MONTHLY) 집계 데이터를 기간을 지정하여 조회할 수 있습니다. 조회 가능한 에너지 항목은 get-thinq-energy-profile로 먼저 확인하세요.",
    inputSchema: {
        deviceId: z.string().describe("조회할 디바이스의 ID. get-thinq-devices로 먼저 목록을 조회하여 얻은 deviceId 값을 사용하세요."),
        period: z.enum(["DAILY", "MONTHLY"]).describe("에너지 데이터 집계 기간. DAILY: 일별 집계, MONTHLY: 월별 집계"),
        startDate: z.string().describe("조회 시작일. YYYYMMDD 형식의 문자열 (예: 20260301)"),
        endDate: z.string().describe("조회 종료일. YYYYMMDD 형식의 문자열 (예: 20260316). startDate 이후 날짜여야 합니다."),
        country: z.string().optional().describe("서비스 국가 코드. ISO 3166-1 alpha-2 형식 (예: KR, US, GB). 기본값: KR"),
    },
}, async ({ deviceId, period, startDate, endDate, country }) => {
    const params = new URLSearchParams({ period, startDate, endDate });
    const response = await fetch(`${THINQ_BASE_URL}/devices/energy/${encodeURIComponent(deviceId)}/usage?${params.toString()}`, {
        headers: buildThinQHeaders(country ?? "KR"),
    });
    const data = await response.json();
    if (!response.ok) {
        return {
            content: [{ type: "text", text: `오류 ${response.status}: ${JSON.stringify(data)}` }],
        };
    }
    return {
        content: [{ type: "text", text: JSON.stringify(data.response, null, 2) }],
    };
});
const app = express();
app.use(express.json());
app.post("/mcp", async (req, res) => {
    console.log("Received MCP request:", req.body);
    // 커스텀 헤더에서 PAT Token 추출 (x-thinq-pat-token)
    const customToken = req.headers["x-thinq-pat-token"];
    let patToken = DEFAULT_THINQ_PAT_TOKEN;
    if (customToken) {
        patToken = Array.isArray(customToken) ? customToken[0] : customToken;
        console.log("Using PAT Token from x-thinq-pat-token header");
    }
    else if (!DEFAULT_THINQ_PAT_TOKEN) {
        console.warn("No x-thinq-pat-token header and no environment THINQ_PAT_TOKEN set");
    }
    try {
        // 현재 요청의 context에 PAT Token 저장
        await asyncLocalStorage.run({ patToken }, async () => {
            const transport = new StreamableHTTPServerTransport({
                sessionIdGenerator: undefined, // set to undefined for stateless servers
            });
            res.on("close", () => {
                transport.close();
            });
            await server.connect(transport);
            await transport.handleRequest(req, res, req.body);
        });
    }
    catch (error) {
        console.error("Error handling MCP request:", error);
        if (!res.headersSent) {
            res.status(500).json({
                jsonrpc: "2.0",
                error: {
                    code: -32603,
                    message: "Internal server error",
                },
                id: null,
            });
        }
    }
});
app.get("/mcp", async (req, res) => {
    console.log("Received GET MCP request");
    res.writeHead(405).end(JSON.stringify({
        jsonrpc: "2.0",
        error: {
            code: -32000,
            message: "Method not allowed.",
        },
        id: null,
    }));
});
app.delete("/mcp", async (req, res) => {
    console.log("Received DELETE MCP request");
    res.writeHead(405).end(JSON.stringify({
        jsonrpc: "2.0",
        error: {
            code: -32000,
            message: "Method not allowed.",
        },
        id: null,
    }));
});
// Start the server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`MCP Streamable HTTP Server listening on port ${PORT}`);
});
