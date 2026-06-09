# ThinQ MCP Server - 환경 변수 설정 가이드

## 개요
이 MCP 서버는 **PAT Token만** 환경 변수로 관리합니다. API Key는 고정값으로 유지됩니다.

## 설정 방법

### 1️⃣ 로컬 개발 (`.env` 파일 사용)

1. 프로젝트 루트에 `.env` 파일 생성:
```bash
cp .env.example .env
```

2. `.env` 파일을 편집하여 **PAT Token만 입력**:
```env
THINQ_PAT_TOKEN=your_actual_pat_token_here
```

3. 서버 시작:
```bash
npm install
npm run build
npm start
```

### 2️⃣ Copilot Studio 에이전트에 MCP 추가

Copilot Studio에서 이 MCP 서버를 연결할 때, 세팅에서 PAT Token만 설정:

```json
{
  "mcpServers": {
    "thinq": {
      "command": "npm",
      "args": ["start"],
      "cwd": "/path/to/ThinQ-mcp-server",
      "env": {
        "THINQ_PAT_TOKEN": "your_pat_token"
      }
    }
  }
}
```

### 3️⃣ Docker/배포 환경

Docker 실행:
```bash
docker run \
  -e THINQ_PAT_TOKEN="your_pat_token" \
  -p 3000:3000 \
  thinq-mcp-server
```

### 4️⃣ 사용자별 Token 관리 (Copilot Studio에서)

사용자가 Copilot Studio 에이전트를 사용할 때:
1. 에이전트 설정 → MCP 커넥터 → ThinQ
2. 각 사용자가 자신의 **PAT Token만 입력**
3. API Key는 서버에서 자동으로 적용
4. 에이전트가 해당 Token으로 요청 실행

## 보안 주의사항

⚠️ **중요:**
- `.env` 파일을 절대로 git에 커밋하지 마세요
- `.gitignore`에 `.env` 추가됨
- **PAT Token**은 안전하게 보관하세요
- API Key는 고정값으로 서버에 포함되어 있습니다

## 환경 변수 우선순위

1. `.env` 파일 (로컬 개발)
2. OS 환경 변수
3. 빈 문자열 (기본값) → 서버 시작 실패

## 문제 해결

### "환경 변수가 필요합니다" 에러
→ `.env` 파일을 생성하고 THINQ_PAT_TOKEN을 입력했는지 확인하세요.

### 특정 Tool 실행 시 "401 Unauthorized"
→ THINQ_PAT_TOKEN이 올바른지 확인하세요. (유효 기간 확인)

## 참고: 각 환경별 설정 예시

**로컬 개발:**
```env
THINQ_PAT_TOKEN=thinqpat_xxxxxxxxx
```

**테스트 환경:**
OS 환경 변수로 설정
```bash
export THINQ_PAT_TOKEN=thinqpat_xxxxx
npm start
```

**프로덕션 (Docker):**
Docker secrets 또는 환경 변수 주입 사용
