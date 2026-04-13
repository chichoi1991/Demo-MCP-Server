# Copilot Studio에서 ThinQ MCP 서버 연결 방법

## 방식: 커스텀 헤더 인증 (x-thinq-pat-token)

이 MCP 서버는 **커스텀 헤더 `x-thinq-pat-token`**을 통해 PAT Token을 받습니다.

## 설정 단계

### 1️⃣ Copilot Studio에서 MCP 커넥터 추가

1. Copilot Studio 설정 → **모델 컨텍스트 프로토콜 프로토콜 서버 추가**
2. 다음 정보 입력:

| 필드 | 값 |
|------|-----|
| **서버 이름** | ThinQ MCP Server |
| **서버 설명** | LG ThinQ 디바이스 제어 MCP |
| **서버 URL** | `https://<your-azure-app>.azurewebsites.net/mcp` |
| **인증** | API 키 |
| **유형** | 헤더 |
| **헤더 이름** | `x-thinq-pat-token` |

3. **연결(Connection) 생성 시** API 키 값에 PAT Token만 입력합니다:

```
thinqpat_xxxxxxxxxxxxx
```

> ⚠️ `Bearer` 접두사 없이 **토큰 값만** 입력하세요.

### 2️⃣ 인증 흐름

1. Copilot Studio가 MCP 요청을 보낼 때, `x-thinq-pat-token` 헤더가 자동으로 포함됩니다.
2. 서버는 해당 헤더에서 토큰을 추출합니다.
3. 이 토큰을 사용하여 ThinQ API에 `Authorization: Bearer <token>` 형식으로 요청합니다.

## 또 다른 옵션: 환경 변수 사용

헤더 방식 외에도 환경 변수로 설정할 수 있습니다:

```json
{
  "mcpServers": {
    "thinq": {
      "command": "node",
      "args": ["dist/server.js"],
      "cwd": "/path/to/ThinQ-mcp-server",
      "env": {
        "THINQ_PAT_TOKEN": "thinqpat_xxxxxxxxxxxxx"
      }
    }
  }
}
```

### 우선순위:
1. **Authorization 헤더** (가장 높음) - 각 요청별로 다른 토큰 사용 가능
2. **환경 변수** - 모든 요청에 동일한 토큰 사용

## 테스트 방법

### curl로 테스트:
```bash
curl -X POST https://<your-azure-app>.azurewebsites.net/mcp \
  -H "x-thinq-pat-token: thinqpat_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### 서버 로그 확인:
```
Using PAT Token from x-thinq-pat-token header
```

이 메시지가 나타나면 헤더에서 토큰을 정상적으로 받은 것입니다.

## 주의사항

⚠️ **보안:**
- PAT Token을 공유하지 마세요
- 신뢰할 수 있는 환경에서만 사용하세요
- Token이 노출되면 즉시 재발급하세요

## 문제 해결

**"PAT Token이 필요합니다" 에러**
→ 헤더에 `x-thinq-pat-token`이 올바르게 포함되었는지 확인
→ 토큰 값만 입력 (`Bearer` 접두사 불필요)

**"401 Unauthorized" 응답**
→ PAT Token이 유효한지 ThinQ에 확인
→ Token의 유효 기간 확인
