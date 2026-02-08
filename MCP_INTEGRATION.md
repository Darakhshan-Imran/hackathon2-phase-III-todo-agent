# MCP Integration Guide

> **Configuration guide for the remote MCP server integration in the todo-agent**
>
> This document explains how the agent connects to the external remote MCP server for all tool operations.

## Overview

**Current State (February 2026)**:
- Agent connects to a **remote MCP server** via Streamable HTTP transport (Option B: Production)
- All 10 tools are served by the external MCP server (no local tool implementations)
- The `openai-agents` SDK's `MCPServerStreamableHttp` handles the connection
- Tools: task CRUD, batch operations, SQL queries — all executed remotely

**Architecture**: Remote MCP Server (Production)

## Architecture

```
Agent (FastAPI)                              Remote MCP Server
├── mcp_client.py (MCPServerStreamableHttp)  ──HTTP──>  ├── server.py (MCP Server)
├── factory.py (creates agent with MCP)                 ├── tools/
│                                                       │   ├── task_tools.py (6 tools)
│   No local tools.py                                   │   ├── batch_tools.py (2 tools)
│   No local context.py                                 │   └── sql_tools.py (2 tools)
│   No direct DB access for tools                       └── database.py (Neon DB)
└── agent_router.py (chat endpoint)
```

## Tools Provided by Remote MCP Server (10 total)

### Task Management (6 tools)
1. `create_task(title, description?, due_date?)` — Creates task with created_by tracking
2. `list_tasks(status='all')` — Lists tasks oldest to newest (ASC order)
3. `update_task(task_id, title?, status?, description?, due_date?)` — All fields optional
4. `delete_task(task_id)` — Deletes single task
5. `get_task_details(task_id)` — Shows all fields including created_by
6. `search_tasks_by_keyword(keyword)` — Fuzzy search with similarity matching

### Batch Operations (2 tools)
7. `batch_delete_tasks(task_ids)` — Deletes up to 100 tasks (comma-separated IDs)
8. `batch_update_tasks(task_ids, title?, status?, description?, due_date?)` — Updates multiple tasks

### SQL Operations (2 tools)
9. `generate_sql_query(question)` — Generates SQL from natural language
10. `execute_sql_query(query)` — Executes SELECT queries safely

## Configuration

### Environment Variables

Add to `backend/.env`:

```bash
# MCP Remote Server Configuration (Production)
MCP_SERVER_URL=https://mcp.yourdomain.com/mcp
MCP_API_KEY=your-api-key-here
MCP_SERVER_TIMEOUT=30
MCP_CACHE_TOOLS=true
MCP_MAX_RETRIES=3
```

### Settings (`backend/app/config.py`)

```python
class Settings(BaseSettings):
    # ... existing settings (DATABASE_URL, api_key, SECRET_KEY, etc.)

    # MCP Remote Server Configuration (Production)
    MCP_SERVER_URL: str = "http://localhost:8000/mcp"
    MCP_API_KEY: Optional[str] = None
    MCP_SERVER_TIMEOUT: int = 30
    MCP_CACHE_TOOLS: bool = True
    MCP_MAX_RETRIES: int = 3
```

## Implementation Details

### MCP Client (`backend/app/agent/mcp_client.py`)

Uses `MCPServerStreamableHttp` from `openai-agents` SDK:

```python
from agents.mcp import MCPServerStreamableHttp

mcp_server = MCPServerStreamableHttp(
    name="Neon Task MCP Server",
    params={
        "url": settings.MCP_SERVER_URL,
        "headers": {"Authorization": f"Bearer {settings.MCP_API_KEY}"},
        "timeout": settings.MCP_SERVER_TIMEOUT,
    },
    cache_tools_list=settings.MCP_CACHE_TOOLS,
    max_retry_attempts=settings.MCP_MAX_RETRIES,
)
```

### Agent Factory (`backend/app/agent/factory.py`)

Agent uses `mcp_servers` parameter instead of local `tools`:

```python
def create_todo_agent(groq_client, mcp_server):
    return Agent(
        name="Todo Manager & Data Analyst",
        instructions=AGENT_INSTRUCTIONS,
        model=OpenAIChatCompletionsModel(
            model="openai/gpt-oss-20b",
            openai_client=groq_client,
        ),
        mcp_servers=[mcp_server],  # Remote MCP tools
    )
```

### Agent Router (`backend/app/routers/agent_router.py`)

Chat endpoint connects to MCP server per request:

```python
mcp_server = get_mcp_server()
agent = create_todo_agent(groq_client, mcp_server)

async with mcp_server:
    result = await Runner.run(agent, full_prompt, ...)
```

## Files Changed (from local tools to remote MCP)

### Modified Files
- `backend/app/config.py` — Added MCP server settings
- `backend/app/agent/factory.py` — Uses `mcp_servers=[mcp_server]` instead of `tools=[...]`
- `backend/app/agent/__init__.py` — Exports `get_mcp_server`, `cleanup_mcp_server`
- `backend/app/routers/agent_router.py` — Uses MCP client, no `AgentContext`
- `backend/app/main.py` — Added MCP cleanup on shutdown
- `backend/pyproject.toml` — Added `mcp>=1.0.0` and `httpx>=0.27.0`

### New Files
- `backend/app/agent/mcp_client.py` — MCP server connection via Streamable HTTP

### Archived Files (no longer used by agent, kept for reference)
- `backend/app/agent/tools.py` — Local tool implementations (now on MCP server)
- `backend/app/agent/context.py` — Agent context with DB session (not needed)
- `backend/app/agent/orchestration_tools.py` — Local orchestration (not needed)
- `backend/app/agent/orchestrator.py` — Local orchestrator (not needed)

## Dependencies

```toml
# backend/pyproject.toml
dependencies = [
    "mcp>=1.0.0",           # MCP Python SDK
    "httpx>=0.27.0",        # HTTP client for Streamable HTTP transport
    "openai-agents>=0.7.0", # Agent SDK with MCPServerStreamableHttp
    # ... other existing dependencies
]
```

Install:
```bash
cd backend
uv add mcp httpx
```

## Testing

```bash
# 1. Ensure remote MCP server is running
# (see MCP_SERVER_SETUP.md for deploying the MCP server)

# 2. Set environment variables
export MCP_SERVER_URL=https://mcp.yourdomain.com/mcp
export MCP_API_KEY=your-api-key

# 3. Start backend
cd backend
uv run uvicorn app.main:app --reload

# 4. Test chat endpoint
curl -X POST http://localhost:8000/agent/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a task: Buy milk", "session_id": "test-123"}'
```

## User Context and Multi-Tenancy

The remote MCP server receives user context via the `_meta` field in tool calls.
The `openai-agents` SDK supports a `tool_meta_resolver` for passing per-request metadata:

```python
from agents.mcp import MCPServerStreamableHttp, MCPToolMetaContext

def resolve_meta(context: MCPToolMetaContext) -> dict[str, str] | None:
    run_context_data = context.run_context.context or {}
    user_id = run_context_data.get("user_id")
    if user_id:
        return {"user_id": str(user_id)}
    return None

mcp_server = MCPServerStreamableHttp(
    name="Neon Task MCP Server",
    params={"url": settings.MCP_SERVER_URL, ...},
    tool_meta_resolver=resolve_meta,
)
```

## Performance

| Metric | Local Tools | Remote MCP (HTTP) |
|--------|-------------|-------------------|
| Latency | ~50ms | ~100-150ms |
| Memory | Higher (tools in process) | Lower (tools remote) |
| Scalability | Limited to single process | High (independent scaling) |
| Deployment | Coupled | Independent |
| Tool caching | N/A | Enabled via `cache_tools_list=True` |

## Troubleshooting

### MCP Server Connection Failed

```bash
# Check remote server is accessible
curl -X POST https://mcp.yourdomain.com/mcp \
  -H "Authorization: Bearer $MCP_API_KEY" \
  -H "Content-Type: application/json"

# Check DNS / network connectivity
nslookup mcp.yourdomain.com
```

### Tool Execution Timeout

Increase timeout in `.env`:
```bash
MCP_SERVER_TIMEOUT=60
```

### Authentication Error

Verify API key is correct:
```bash
echo $MCP_API_KEY
# Ensure it matches the key configured on the MCP server
```

### Tools Not Discovered

Clear cached tools by restarting the agent, or set:
```bash
MCP_CACHE_TOOLS=false
```

## Rollback Plan

If remote MCP integration fails, restore local tools from git:

```bash
git checkout backend/app/agent/tools.py
git checkout backend/app/agent/context.py
git checkout backend/app/agent/factory.py
git checkout backend/app/agent/__init__.py
git checkout backend/app/routers/agent_router.py
git checkout backend/app/main.py
git checkout backend/pyproject.toml

# Remove MCP client
rm backend/app/agent/mcp_client.py

# Reinstall dependencies
cd backend && uv sync
```

## Migration Checklist

### Completed
- [x] 10 tools implemented on remote MCP server
- [x] `MCPServerStreamableHttp` client configured
- [x] `factory.py` updated to use `mcp_servers`
- [x] `agent_router.py` uses MCP client (no `AgentContext`)
- [x] `config.py` has MCP settings
- [x] `pyproject.toml` has `mcp` and `httpx` dependencies
- [x] `main.py` cleans up MCP on shutdown

### Verify
- [ ] Deploy MCP server to production
- [ ] Configure DNS and TLS for `mcp.yourdomain.com`
- [ ] Set production `MCP_API_KEY` as a secret
- [ ] Test all 10 tools via remote MCP
- [ ] Verify user_id isolation across all operations
- [ ] Monitor latency and error rates
- [ ] Set up health checks for the remote MCP server

## Next Steps

1. Deploy the MCP server (see `MCP_SERVER_SETUP.md`)
2. Configure DNS and TLS for `mcp.yourdomain.com`
3. Set production `MCP_API_KEY` as a secret
4. Monitor latency and error rates
5. Enable `tool_meta_resolver` for user context passing
6. Set up health checks for the remote MCP server
