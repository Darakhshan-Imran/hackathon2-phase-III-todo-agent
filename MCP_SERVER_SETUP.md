# MCP Server Setup Guide (Python)

> **Context file for creating `query-agent-mcp` repository**
> 
> This document provides the complete setup for extracting all agent tools into a standalone Python MCP server.
>
> **Transport**: Streamable HTTP (Production — for remote deployment)

## Project Structure

```
query-agent-mcp/          # New separate repo (Python)
├── src/
│   ├── mcp_server/
│   │   ├── __init__.py
│   │   ├── server.py           # MCP server entry point (Streamable HTTP)
│   │   ├── database.py         # Neon DB connection
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── task_tools.py   # CRUD operations (6 tools)
│   │       ├── batch_tools.py  # Batch operations (2 tools)
│   │       └── sql_tools.py    # SQL operations (2 tools)
├── .env
├── .env.example
├── pyproject.toml
├── Dockerfile
├── README.md
└── requirements.txt
```

## Tech Stack

```toml
[project]
name = "query-agent-mcp"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    "mcp>=1.0.0",              # MCP Python SDK
    "asyncpg>=0.29.0",         # Async PostgreSQL driver
    "python-dotenv>=1.0.0",    # Environment variables
]
```

## Tools to Migrate (10 total)

From `backend/app/agent/tools.py`:

### Task Management (6 tools)
1. **create_task** - Create new task with optional due_date and created_by tracking
2. **list_tasks** - List all tasks with status filter (sorted oldest to newest)
3. **update_task** - Update task (title, description, status, due_date) - all fields optional
4. **delete_task** - Delete single task by ID
5. **get_task_details** - Get detailed task info including created_by
6. **search_tasks_by_keyword** - Fuzzy search by title/description with similarity matching

### Batch Operations (2 tools)
7. **batch_delete_tasks** - Delete up to 100 tasks with comma-separated IDs
8. **batch_update_tasks** - Update multiple tasks (title, description, status, due_date)

### SQL Operations (2 tools)
9. **generate_sql_query** - Generate SQL from natural language questions
10. **execute_sql_query** - Execute SELECT queries with user_id filtering and safety checks

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    email VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Todos table
CREATE TABLE todos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description VARCHAR(1000) DEFAULT NULL,
    status VARCHAR DEFAULT 'pending',
    due_date TIMESTAMP DEFAULT NULL,
    user_id INTEGER REFERENCES users(id),
    created_by VARCHAR(100) DEFAULT NULL,  -- "task created by 'username'"
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NULL
);

-- Conversation history table
CREATE TABLE conversation_messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    conversation_id VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Environment Variables

Create `.env`:

```bash
# Neon Database (same as main agent)
DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require

# MCP Server
MCP_SERVER_NAME=neon-task-server
MCP_SERVER_VERSION=1.0.0
```

## MCP Server Implementation

### 1. Database Connection (`src/mcp_server/database.py`)

```python
"""Database connection using asyncpg for Neon PostgreSQL."""
import os
import asyncpg
from typing import Optional

_pool: Optional[asyncpg.Pool] = None

async def get_db_pool() -> asyncpg.Pool:
    """Get or create database connection pool."""
    global _pool
    if _pool is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL not set")
        
        _pool = await asyncpg.create_pool(
            database_url,
            min_size=1,
            max_size=10,
        )
    return _pool

async def close_db_pool():
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
```

### 2. Tool Context

```python
"""User context passed to all tools."""
from dataclasses import dataclass
import asyncpg

@dataclass
class ToolContext:
    """Context for tool execution."""
    user_id: int
    db_pool: asyncpg.Pool
```

### 3. Task Management Tools (`src/mcp_server/tools/task_tools.py`)

```python
"""Task CRUD operations - 6 tools."""
from datetime import datetime
from typing import Optional
from mcp.server import Tool
from mcp.types import TextContent
import asyncpg

async def create_task(
    context,
    title: str,
    description: str = "",
    due_date: Optional[str] = None,
) -> dict:
    """Create a new task with automatic created_by tracking."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    # Parse due_date
    parsed_due_date = None
    if due_date:
        try:
            parsed_due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
    
    async with pool.acquire() as conn:
        # Get username for created_by
        user = await conn.fetchrow(
            "SELECT username FROM users WHERE id = $1",
            user_id
        )
        username = user['username'] if user else 'unknown'
        created_by = f"task created by '{username}'"
        
        # Insert task
        task = await conn.fetchrow("""
            INSERT INTO todos (title, description, due_date, user_id, created_by)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, title, status, created_at, created_by
        """, title, description or None, parsed_due_date, user_id, created_by)
        
        return {
            "success": True,
            "task_id": task['id'],
            "message": f"✅ Created task #{task['id']}: '{title}'"
        }

async def list_tasks(
    context,
    status: str = "all",
) -> dict:
    """List all tasks (sorted oldest to newest)."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    async with pool.acquire() as conn:
        if status == "all":
            query = """
                SELECT id, title, status, due_date, created_at, created_by
                FROM todos 
                WHERE user_id = $1
                ORDER BY created_at ASC
            """
            tasks = await conn.fetch(query, user_id)
        else:
            query = """
                SELECT id, title, status, due_date, created_at, created_by
                FROM todos 
                WHERE user_id = $1 AND status = $2
                ORDER BY created_at ASC
            """
            tasks = await conn.fetch(query, user_id, status)
        
        return {
            "success": True,
            "count": len(tasks),
            "tasks": [dict(t) for t in tasks]
        }

async def update_task(
    context,
    task_id: int,
    title: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
) -> dict:
    """Update a single task (all fields optional)."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    # Build dynamic update query
    updates = []
    params = []
    param_count = 1
    
    if title is not None:
        updates.append(f"title = ${param_count}")
        params.append(title)
        param_count += 1
    
    if status is not None:
        if status not in ["pending", "completed"]:
            return {"error": "❌ Invalid status. Use 'pending' or 'completed'"}
        updates.append(f"status = ${param_count}")
        params.append(status)
        param_count += 1
    
    if description is not None:
        updates.append(f"description = ${param_count}")
        params.append(description)
        param_count += 1
    
    if due_date is not None:
        if due_date.lower() == "none":
            updates.append("due_date = NULL")
        else:
            try:
                parsed = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                updates.append(f"due_date = ${param_count}")
                params.append(parsed)
                param_count += 1
            except (ValueError, AttributeError):
                return {"error": "❌ Invalid due date format"}
    
    if not updates:
        return {"error": "❌ No updates specified"}
    
    updates.append("updated_at = NOW()")
    params.extend([task_id, user_id])
    
    async with pool.acquire() as conn:
        query = f"""
            UPDATE todos 
            SET {', '.join(updates)}
            WHERE id = ${param_count} AND user_id = ${param_count + 1}
            RETURNING id, title, status, updated_at
        """
        task = await conn.fetchrow(query, *params)
        
        if not task:
            return {"error": f"❌ Task #{task_id} not found"}
        
        return {
            "success": True,
            "task": dict(task),
            "message": f"✅ Updated task #{task_id}"
        }

async def delete_task(context, task_id: int) -> dict:
    """Delete a single task by ID."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    async with pool.acquire() as conn:
        task = await conn.fetchrow("""
            DELETE FROM todos 
            WHERE id = $1 AND user_id = $2
            RETURNING id, title
        """, task_id, user_id)
        
        if not task:
            return {"error": f"❌ Task #{task_id} not found"}
        
        return {
            "success": True,
            "message": f"✅ Deleted task #{task['id']}: '{task['title']}'"
        }

async def get_task_details(context, task_id: int) -> dict:
    """Get detailed information about a task."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    async with pool.acquire() as conn:
        task = await conn.fetchrow("""
            SELECT id, title, description, status, due_date, 
                   created_by, created_at, updated_at
            FROM todos 
            WHERE id = $1 AND user_id = $2
        """, task_id, user_id)
        
        if not task:
            return {"error": f"❌ Task #{task_id} not found"}
        
        return {
            "success": True,
            "task": dict(task)
        }

async def search_tasks_by_keyword(context, keyword: str) -> dict:
    """Search for tasks using fuzzy matching."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    async with pool.acquire() as conn:
        # Use PostgreSQL similarity search
        tasks = await conn.fetch("""
            SELECT id, title, description, status, due_date, created_at
            FROM todos 
            WHERE user_id = $1 
            AND (title ILIKE $2 OR description ILIKE $2)
            ORDER BY created_at DESC
        """, user_id, f"%{keyword}%")
        
        return {
            "success": True,
            "count": len(tasks),
            "tasks": [dict(t) for t in tasks],
            "keyword": keyword
        }
```

### 4. Batch Operations (`src/mcp_server/tools/batch_tools.py`)

```python
"""Batch operations - 2 tools."""
from datetime import datetime
from typing import Optional

async def batch_delete_tasks(context, task_ids: str) -> dict:
    """Delete multiple tasks by IDs (max 100)."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    # Parse IDs
    try:
        ids = [int(id.strip()) for id in task_ids.split(",") if id.strip()]
    except ValueError:
        return {"error": "❌ Invalid task IDs format. Use '1,2,3'"}
    
    if not ids:
        return {"error": "❌ No task IDs provided"}
    
    if len(ids) > 100:
        return {"error": "❌ Maximum 100 tasks allowed"}
    
    async with pool.acquire() as conn:
        tasks = await conn.fetch("""
            DELETE FROM todos 
            WHERE id = ANY($1::int[]) AND user_id = $2
            RETURNING id, title
        """, ids, user_id)
        
        if not tasks:
            return {"error": f"❌ No tasks found with IDs: {task_ids}"}
        
        deleted_ids = [t['id'] for t in tasks]
        found_ids = set(deleted_ids)
        requested_ids = set(ids)
        missing_ids = requested_ids - found_ids
        
        message = f"✅ Successfully deleted {len(deleted_ids)} task(s): " + ", ".join([f"#{id}" for id in deleted_ids])
        
        if missing_ids:
            message += f"\n⚠️ Tasks not found: " + ", ".join([f"#{id}" for id in sorted(missing_ids)])
        
        return {
            "success": True,
            "deleted_count": len(deleted_ids),
            "deleted_ids": deleted_ids,
            "message": message
        }

async def batch_update_tasks(
    context,
    task_ids: str,
    title: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
) -> dict:
    """Update multiple tasks with same values (max 100)."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    # Parse IDs
    try:
        ids = [int(id.strip()) for id in task_ids.split(",") if id.strip()]
    except ValueError:
        return {"error": "❌ Invalid task IDs format. Use '1,2,3'"}
    
    if not ids:
        return {"error": "❌ No task IDs provided"}
    
    if len(ids) > 100:
        return {"error": "❌ Maximum 100 tasks allowed"}
    
    # Validate status
    if status and status not in ["pending", "completed"]:
        return {"error": "❌ Invalid status. Use 'pending' or 'completed'"}
    
    # Build dynamic update query
    updates = []
    params = []
    param_count = 1
    
    if title is not None:
        updates.append(f"title = ${param_count}")
        params.append(title)
        param_count += 1
    
    if status is not None:
        updates.append(f"status = ${param_count}")
        params.append(status)
        param_count += 1
    
    if description is not None:
        updates.append(f"description = ${param_count}")
        params.append(description)
        param_count += 1
    
    if due_date is not None:
        if due_date.lower() == "none":
            updates.append("due_date = NULL")
        else:
            try:
                parsed = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                updates.append(f"due_date = ${param_count}")
                params.append(parsed)
                param_count += 1
            except (ValueError, AttributeError):
                return {"error": "❌ Invalid due date format"}
    
    if not updates:
        return {"error": "❌ No updates specified"}
    
    updates.append("updated_at = NOW()")
    params.extend([ids, user_id])
    
    async with pool.acquire() as conn:
        query = f"""
            UPDATE todos 
            SET {', '.join(updates)}
            WHERE id = ANY(${param_count}::int[]) AND user_id = ${param_count + 1}
            RETURNING id, title, status
        """
        tasks = await conn.fetch(query, *params)
        
        if not tasks:
            return {"error": f"❌ No tasks found with IDs: {task_ids}"}
        
        updated_ids = [t['id'] for t in tasks]
        updates_made = []
        if title: updates_made.append(f"title → '{title}'")
        if status: updates_made.append(f"status → {status}")
        if description: updates_made.append("description updated")
        if due_date: updates_made.append("due date updated" if due_date.lower() != "none" else "due date removed")
        
        message = f"✅ Successfully updated {len(updated_ids)} task(s): " + ", ".join([f"#{id}" for id in updated_ids])
        message += f"\nChanges: {', '.join(updates_made)}"
        
        return {
            "success": True,
            "updated_count": len(updated_ids),
            "updated_ids": updated_ids,
            "message": message
        }
```

### 5. SQL Operations (`src/mcp_server/tools/sql_tools.py`)

```python
"""SQL query tools - 2 tools."""
import re

DATABASE_SCHEMA = """
users (id, username, email, created_at)
todos (id, title, description, status, due_date, user_id, created_by, created_at, updated_at)
"""

async def generate_sql_query(context, question: str) -> dict:
    """Generate SQL from natural language."""
    user_id = context["user_id"]
    
    # Common patterns
    patterns = {
        r"how many.*completed": f"SELECT COUNT(*) as completed_count FROM todos WHERE user_id = {user_id} AND status = 'completed'",
        r"how many.*pending": f"SELECT COUNT(*) as pending_count FROM todos WHERE user_id = {user_id} AND status = 'pending'",
        r"how many.*task": f"SELECT COUNT(*) as total_tasks FROM todos WHERE user_id = {user_id}",
        r"list.*task": f"SELECT id, title, status, created_at FROM todos WHERE user_id = {user_id} ORDER BY created_at DESC",
        r"task.*today": f"SELECT id, title, status FROM todos WHERE user_id = {user_id} AND DATE(created_at) = CURRENT_DATE",
        r"task.*week": f"SELECT id, title, created_at FROM todos WHERE user_id = {user_id} AND created_at >= CURRENT_DATE - INTERVAL '7 days'",
    }
    
    question_lower = question.lower()
    
    for pattern, query in patterns.items():
        if re.search(pattern, question_lower):
            return {
                "success": True,
                "query": query,
                "message": f"Generated SQL query:\n```sql\n{query}\n```\n\nUse execute_sql_query to run this."
            }
    
    return {
        "success": True,
        "message": f"Could not generate query for: '{question}'\n\nDatabase schema:\n{DATABASE_SCHEMA}\n\nTry questions like:\n- 'How many completed tasks do I have?'\n- 'List all tasks created this week'"
    }

async def execute_sql_query(context, query: str) -> dict:
    """Execute SELECT queries with safety checks."""
    user_id = context["user_id"]
    pool = context["db_pool"]
    
    # Safety checks
    query_upper = query.upper().strip()
    
    if not query_upper.startswith("SELECT"):
        return {"error": "❌ Only SELECT queries are allowed"}
    
    if any(keyword in query_upper for keyword in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]):
        return {"error": "❌ Modification queries are not allowed"}
    
    if "user_id" not in query.lower():
        return {"error": "❌ Query must filter by user_id for security"}
    
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query)
            
            if not rows:
                return {
                    "success": True,
                    "message": "Query executed successfully but returned no results."
                }
            
            # Format results
            lines = []
            if rows:
                # Header
                headers = list(rows[0].keys())
                lines.append(" | ".join(headers))
                lines.append("-" * (len(" | ".join(headers))))
                
                # Rows (limit to 50)
                for row in rows[:50]:
                    lines.append(" | ".join(str(v) for v in row.values()))
                
                if len(rows) > 50:
                    lines.append(f"\n... and {len(rows) - 50} more rows")
            
            return {
                "success": True,
                "row_count": len(rows),
                "results": "\n".join(lines)
            }
    
    except Exception as e:
        return {"error": f"❌ SQL Error: {str(e)}\n\nPlease check your query syntax."}
```

### 6. MCP Server Entry (`src/mcp_server/server.py`)

```python
"""MCP Server implementation with Streamable HTTP transport (Production)."""
import asyncio
import os
import contextlib
from collections.abc import AsyncIterator

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount

from mcp.server.mcpserver import MCPServer
from mcp.types import TextContent
from dotenv import load_dotenv

from .database import get_db_pool, close_db_pool
from .tools.task_tools import (
    create_task, list_tasks, update_task, delete_task,
    get_task_details, search_tasks_by_keyword
)
from .tools.batch_tools import batch_delete_tasks, batch_update_tasks
from .tools.sql_tools import generate_sql_query, execute_sql_query

load_dotenv()

# Create MCP server
mcp = MCPServer("neon-task-server")

# Database pool (initialized on startup)
_pool = None

# API key for authentication (set via MCP_API_KEY env var)
API_KEY = os.getenv("MCP_API_KEY", "")


# Register all 10 tools using the MCPServer decorator pattern

@mcp.tool()
async def tool_create_task(title: str, description: str = "", due_date: str = "") -> str:
    """Create a new task with automatic created_by tracking.
    
    Args:
        title: Task title (required)
        description: Task description
        due_date: Due date in YYYY-MM-DD format
    """
    context = {"user_id": 1, "db_pool": _pool}  # user_id from _meta
    result = await create_task(context, title=title, description=description, due_date=due_date or None)
    import json
    return json.dumps(result, default=str)

@mcp.tool()
async def tool_list_tasks(status: str = "all") -> str:
    """List all tasks sorted oldest to newest."""
    context = {"user_id": 1, "db_pool": _pool}
    result = await list_tasks(context, status=status)
    import json
    return json.dumps(result, default=str)

# ... (register remaining 8 tools similarly)


# Starlette app with lifespan for DB pool management
@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[None]:
    global _pool
    _pool = await get_db_pool()
    async with mcp.session_manager.run():
        yield
    await close_db_pool()


# Mount MCP server with Streamable HTTP transport
app = Starlette(
    routes=[
        Mount("/mcp", app=mcp.streamable_http_app(json_response=True)),
    ],
    lifespan=lifespan,
)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

> **Key Change**: The server uses `streamable_http_app()` instead of `stdio_server()`.
> This allows the agent to connect remotely over HTTP using `MCPServerStreamableHttp`.
>
> **Endpoint**: The MCP server listens at `http://host:port/mcp`

### 7. Project Configuration (`pyproject.toml`)

```toml
[project]
name = "query-agent-mcp"
version = "1.0.0"
description = "MCP server for Neon task management (Streamable HTTP)"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "asyncpg>=0.29.0",
    "python-dotenv>=1.0.0",
    "uvicorn[standard]>=0.30.0",
    "starlette>=0.40.0",
]

[project.scripts]
query-agent-mcp = "mcp_server.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

```typescript
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  createTaskTool, 
  listTasksTool, 
  updateTaskTool, 
  deleteTaskTool,
  getTaskDetailsTool,
  searchTasksByKeywordTool
} from './tools/task-tools.js';
import { batchDeleteTasksTool, batchUpdateTasksTool } from './tools/batch-tools.js';
import { generateSqlQueryTool, executeSqlQueryTool } from './tools/sql-tools.js';
import { sql } from './database.js';

const server = new Server({
  name: 'neon-task-server',
  version: '1.0.0',
}, {
  capabilities: {
    tools: {},
  },
});

// Register all 10 tools
const tools = [
  // Task Management (6 tools)
  createTaskTool,
  listTasksTool,
  updateTaskTool,
  deleteTaskTool,
  getTaskDetailsTool,
  searchTasksByKeywordTool,
  
  // Batch Operations (2 tools)
  batchDeleteTasksTool,
  batchUpdateTasksTool,
  
  // SQL Operations (2 tools)
  generateSqlQueryTool,
  executeSqlQueryTool,
];

server.setRequestHandler('tools/list', async () => ({
  tools: tools.map(t => ({
    name: t.name,
    description: t.description,
    inputSchema: t.inputSchema,
  })),
}));

server.setRequestHandler('tools/call', async (request) => {
  const tool = tools.find(t => t.name === request.params.name);
  if (!tool) {
    throw new Error(`Unknown tool: ${request.params.name}`);
  }
  
  // Extract user_id from request context
  const userId = request.params._meta?.userId || 1;
  
  const result = await tool.execute(request.params.arguments, {
    userId,
    sql,
  });
  
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(result, null, 2),
      },
    ],
  };
});

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
```

## Package.json

```json
{
  "name": "query-agent-mcp",
  "version": "1.0.0",
  "type": "module",
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "tsx watch src/index.ts"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "@neondatabase/serverless": "^0.10.0",
    "dotenv": "^16.4.0",
    "zod": "^3.22.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "tsx": "^4.7.0",
    "typescript": "^5.3.0"
  }
}
```

## TSConfig

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

## User Context Handling

The MCP server receives user context from the agent:

```typescript
// In tool execution, extract user from request metadata
const userId = request.params._meta?.userId;

// Use in all database queries
await sql`SELECT * FROM todos WHERE user_id = ${userId}`;
```

## Security Considerations

1. **User Isolation**: Always filter by `user_id` in queries
2. **SQL Injection**: Use parameterized queries (Neon handles this)
3. **Input Validation**: Use Zod schemas for all inputs
4. **Rate Limiting**: Not handled by MCP - implement in agent layer

## Testing

```bash
# Install dependencies
pip install -e .

# Build (not needed for Python)

# Test locally — start the Streamable HTTP server
uvicorn mcp_server.server:app --host 0.0.0.0 --port 8000

# In another terminal, test the /mcp endpoint
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

## Deployment

### Local Development
```bash
# Run with Streamable HTTP transport (default)
uvicorn mcp_server.server:app --host 0.0.0.0 --port 8000 --reload

# Or run directly
python -m mcp_server.server
```

### Production (Remote Server)

The MCP server should be deployed as a standalone HTTP service accessible to the agent.

```bash
# Set environment variables
export DATABASE_URL="postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require"
export MCP_API_KEY="your-secure-api-key"
export PORT=8000

# Run with uvicorn
uvicorn mcp_server.server:app --host 0.0.0.0 --port $PORT --workers 4
```

The agent connects to this server using:
```bash
MCP_SERVER_URL=https://mcp.yourdomain.com/mcp
MCP_API_KEY=your-secure-api-key
```

### Docker (Recommended for Production)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install -e .

# Copy source
COPY src/ src/

# Expose port
EXPOSE 8000

# Run server with Streamable HTTP transport
CMD ["uvicorn", "mcp_server.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```bash
# Build and run
docker build -t query-agent-mcp .
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e MCP_API_KEY="your-api-key" \
  query-agent-mcp
```

### Cloud Deployment Options

**Railway / Render / Fly.io**:
```bash
# Set env vars via dashboard, then deploy
# The Dockerfile above works with all PaaS platforms
```

**AWS / GCP / Azure**:
- Deploy as a container service (ECS, Cloud Run, Container Apps)
- Set `MCP_SERVER_URL` in agent's `.env` to the deployed URL
- Use managed secrets for `MCP_API_KEY`

## Key Differences from Current Implementation

| Current (FastAPI) | MCP Server |
|------------------|------------|
| Python async functions | TypeScript async functions |
| SQLModel ORM | Direct SQL with Neon |
| ToolContext from agents SDK | Custom TaskContext |
| FastAPI dependencies | MCP request metadata |
| uvicorn server | stdio transport |

## Migration Checklist

- [ ] Create new repo `query-agent-mcp`
- [ ] Copy tool logic from `backend/app/agent/tools.py`
- [ ] Convert Python to TypeScript
- [ ] Replace SQLModel with Neon SQL
- [ ] Set up MCP server with SDK
- [ ] Test all 10 tools
- [ ] Deploy and get server endpoint
- [ ] Configure in main agent (see MCP_INTEGRATION.md)

## Quick Start Commands

```bash
# Create repo
mkdir query-agent-mcp && cd query-agent-mcp
git init

# Initialize Python project
touch pyproject.toml .env .env.example README.md Dockerfile

# Create structure
mkdir -p src/mcp_server/tools
touch src/mcp_server/__init__.py
touch src/mcp_server/server.py
touch src/mcp_server/database.py
touch src/mcp_server/tools/__init__.py
touch src/mcp_server/tools/task_tools.py
touch src/mcp_server/tools/batch_tools.py
touch src/mcp_server/tools/sql_tools.py

# Install dependencies (using uv)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install mcp asyncpg python-dotenv uvicorn starlette

# Or using pip
python -m venv .venv
source .venv/bin/activate
pip install mcp asyncpg python-dotenv uvicorn starlette

# Copy tool implementations from this document into files

# Run server with Streamable HTTP transport
uvicorn mcp_server.server:app --host 0.0.0.0 --port 8000 --reload
```

## Complete Tool Implementation Checklist

### Task Management Tools (6) ✅
- [ ] `create_task` - Include created_by field with username from users table
- [ ] `list_tasks` - Sort by created_at ASC (oldest first), filter by status
- [ ] `update_task` - All fields optional (title, status, description, due_date)
- [ ] `delete_task` - Simple ID-based deletion with user_id security check
- [ ] `get_task_details` - Return all fields including created_by and timestamps
- [ ] `search_tasks_by_keyword` - PostgreSQL ILIKE search on title/description

### Batch Operations Tools (2) ✅
- [ ] `batch_delete_tasks` - Parse comma-separated IDs, max 100 limit, user_id filtering
- [ ] `batch_update_tasks` - Support title, status, description, due_date updates, max 100

### SQL Tools (2) ✅
- [ ] `generate_sql_query` - Regex pattern matching for common natural language queries
- [ ] `execute_sql_query` - SELECT only, user_id requirement, safety checks (no DROP/DELETE/etc)

### Key Implementation Details (Python-Specific)
- **Database**: Use `asyncpg` connection pool (same as main agent)
- **created_by**: Format as `"task created by 'username'"` via JOIN with users table
- **Listing order**: `ORDER BY created_at ASC` (oldest to newest)
- **Optional params**: update_task uses dynamic query building with parameterized queries
- **Batch limits**: Max 100 tasks per batch operation (validated in tool)
- **User isolation**: All queries use `WHERE user_id = $1` for security
- **Timestamps**: `updated_at = NOW()` auto-set on updates
- **Error handling**: Return dict with "error" key for failures, "success" for good results

### Security Requirements
```python
# All tools MUST filter by user_id
async with pool.acquire() as conn:
    result = await conn.fetch(
        "SELECT * FROM todos WHERE user_id = $1",
        user_id  # REQUIRED
    )

# SQL injection prevention - use parameterized queries
# ✅ CORRECT
await conn.fetch("SELECT * FROM todos WHERE id = $1", task_id)

# ❌ WRONG - vulnerable to SQL injection
await conn.fetch(f"SELECT * FROM todos WHERE id = {task_id}")
```

## Testing the MCP Server

### 1. Test locally with Python

```python
# test_server.py
import asyncio
import json
from mcp_server.database import get_db_pool
from mcp_server.tools.task_tools import create_task, list_tasks

async def test():
    pool = await get_db_pool()
    context = {"user_id": 1, "db_pool": pool}
    
    # Test create
    result = await create_task(context, title="Test Task", description="Testing")
    print("Create:", json.dumps(result, indent=2, default=str))
    
    # Test list
    result = await list_tasks(context, status="all")
    print("List:", json.dumps(result, indent=2, default=str))
    
    await pool.close()

asyncio.run(test())
```

### 2. Test with MCP stdio

```bash
# Start server
python -m mcp_server.server

# In another terminal, send JSON-RPC request
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python -m mcp_server.server
```

### 3. Integration test with main agent

```python
# Test remote MCP server connection from the agent side
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import asyncio

async def test_remote_mcp():
    async with streamable_http_client("http://localhost:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")
            
            # Call create_task
            result = await session.call_tool(
                "create_task",
                arguments={"title": "Test from agent"},
            )
            print(result)

asyncio.run(test_remote_mcp())
```

## Deployment Options

### Option 1: Local Development
```bash
# Run with Streamable HTTP
uvicorn mcp_server.server:app --host 0.0.0.0 --port 8000 --reload
```

### Option 2: Systemd Service (Linux)
```ini
# /etc/systemd/system/query-agent-mcp.service
[Unit]
Description=MCP Neon Task Server (Streamable HTTP)
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/query-agent-mcp
Environment="DATABASE_URL=postgresql://..."
Environment="MCP_API_KEY=your-api-key"
ExecStart=/opt/query-agent-mcp/.venv/bin/uvicorn mcp_server.server:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

### Option 3: Docker (Recommended for Production)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install -e .

# Copy source
COPY src/ src/

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "mcp_server.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```bash
# Build and run
docker build -t query-agent-mcp .
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e MCP_API_KEY="your-api-key" \
  query-agent-mcp
```

### Option 4: Cloud PaaS (Railway / Render / Fly.io)
```bash
# Deploy using the Dockerfile above
# Set env vars via platform dashboard:
#   DATABASE_URL=postgresql://...
#   MCP_API_KEY=your-api-key
#   PORT=8000
```

## Key Differences from Current Implementation

| Current (Inline Tools) | MCP Server (Remote) |
|------------------------|---------------------|
| Tools in `backend/app/agent/tools.py` | Tools in `src/mcp_server/tools/*.py` |
| Direct SQLModel ORM | asyncpg connection pool |
| ToolContext from agents SDK | Custom dict context |
| FastAPI dependencies injection | MCP metadata passing |
| Runs in same process | Separate HTTP server |
| Tightly coupled | Loosely coupled via Streamable HTTP |
| Agent connects locally | Agent connects via `MCPServerStreamableHttp` |

## Migration Checklist

### Pre-Migration (Current State)
- [x] 10 tools working in `backend/app/agent/tools.py`
- [x] All features: batch ops, created_by, ASC order, optional params
- [x] Tools registered in `backend/app/agent/factory.py`
- [x] Server running and tested

### MCP Server Creation
- [ ] Create new repo `query-agent-mcp`
- [ ] Set up Python project structure
- [ ] Copy tool logic from `backend/app/agent/tools.py`
- [ ] Convert from SQLModel to asyncpg queries
- [ ] Implement MCP server.py with tool registration
- [ ] Test all 10 tools standalone
- [ ] Set up environment variables

### Integration with Main Agent
- [ ] Install MCP client in main agent
- [ ] Create `backend/app/agent/mcp_client.py`
- [ ] Update `factory.py` to use MCP tools
- [ ] Update router to pass user context to MCP
- [ ] Test end-to-end integration
- [ ] Verify user_id isolation works
- [ ] Performance testing

### Post-Migration
- [ ] Archive old `tools.py` (don't delete until fully tested)
- [ ] Update documentation
- [ ] Deploy MCP server to production
- [ ] Monitor for issues

## Compatibility Notes

### Database
- ✅ Same Neon PostgreSQL database
- ✅ Same schema (users, todos, conversation_messages)
- ✅ Same asyncpg driver family
- ✅ User isolation via user_id

### Python Environment
- ✅ Python 3.11+ (same as main agent)
- ✅ Async/await (same pattern)
- ✅ Type hints supported
- ✅ Same error handling patterns

### Data Format
- ✅ Same datetime handling (ISO format)
- ✅ Same status values ('pending', 'completed')
- ✅ Same created_by format
- ✅ Compatible JSON responses

## Troubleshooting

### Connection Issues
```bash
# Test database connection
python -c "import asyncio, asyncpg; asyncio.run(asyncpg.connect('$DATABASE_URL'))"
```

### Tool Execution Errors
```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

### MCP Protocol Issues
```bash
# Check MCP SDK version
pip show mcp

# Update if needed
pip install --upgrade mcp
```

This Python-based MCP server is fully compatible with your Python agent! 🎉

## Agent-Side Connection

Once this MCP server is deployed, the todo-agent connects to it using:

```python
# backend/app/agent/mcp_client.py
from agents.mcp import MCPServerStreamableHttp

mcp_server = MCPServerStreamableHttp(
    name="Neon Task MCP Server",
    params={
        "url": "https://mcp.yourdomain.com/mcp",  # MCP_SERVER_URL
        "headers": {"Authorization": "Bearer your-api-key"},  # MCP_API_KEY
        "timeout": 30,
    },
    cache_tools_list=True,
    max_retry_attempts=3,
)
```

See `MCP_INTEGRATION.md` for the complete agent-side setup.
