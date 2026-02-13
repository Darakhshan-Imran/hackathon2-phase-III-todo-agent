"""
Local MCP Server for Todo AI Agent.

Runs as a subprocess via stdio transport. Provides all 10 task management
tools that the agent uses. Connects directly to the Neon PostgreSQL database
using DATABASE_URL from environment variables.

Usage (run directly as script):
    python server.py
"""

import os
import re
import ssl as _ssl
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import asyncpg
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Todo MCP Server")

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

_pool: Optional[asyncpg.Pool] = None


async def _get_pool() -> asyncpg.Pool:
    """Get or create an asyncpg connection pool."""
    global _pool
    if _pool is not None:
        return _pool

    raw_url = os.environ["DATABASE_URL"]

    # Strip SQLAlchemy dialect prefix if present (e.g. postgresql+asyncpg://)
    if "+asyncpg" in raw_url:
        raw_url = raw_url.replace("+asyncpg", "", 1)

    # asyncpg doesn't understand libpq query-string params like sslmode,
    # channel_binding, etc. Strip them and configure SSL separately.
    parsed = urlparse(raw_url)
    params = parse_qs(parsed.query)

    use_ssl = any(
        v[0] in ("require", "verify-full", "verify-ca")
        for v in [params.get("sslmode", ["disable"])]
    )

    libpq_only = {"sslmode", "channel_binding", "options"}
    clean_params = {k: v[0] for k, v in params.items() if k not in libpq_only}
    clean_query = urlencode(clean_params) if clean_params else ""
    clean_url = urlunparse(parsed._replace(query=clean_query))

    ssl_ctx = _ssl.create_default_context() if use_ssl else None

    _pool = await asyncpg.create_pool(
        clean_url,
        ssl=ssl_ctx,
        min_size=1,
        max_size=5,
        command_timeout=60,
        server_settings={"application_name": "todo_mcp_server"},
    )
    return _pool


async def _fetch(query: str, *args):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def _fetchrow(query: str, *args):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def _execute(query: str, *args):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


# ---------------------------------------------------------------------------
# Fuzzy search helpers
# ---------------------------------------------------------------------------


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _fuzzy_match(keyword: str, tasks: list, threshold: float = 0.6) -> list:
    keyword_lower = keyword.lower()
    matches = []
    for task in tasks:
        text = f"{task['title']} {task['description'] or ''}".lower()
        words = re.findall(r"\w+", text)
        best = 0.0
        for w in words:
            best = max(best, _similarity(keyword_lower, w))
            if keyword_lower in w or w in keyword_lower:
                best = max(best, 0.8)
        if best >= threshold:
            matches.append((task, best))
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def create_task(
    user_id: int,
    title: str,
    description: str = "",
    due_date: Optional[str] = None,
) -> str:
    """Create a new task for the authenticated user.

    Args:
        user_id: The authenticated user's ID.
        title: The title of the task.
        description: Optional description of the task.
        due_date: Optional due date in ISO format (YYYY-MM-DD).
    """
    parsed_due_date = None
    if due_date:
        try:
            parsed_due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            parsed_due_date = None

    # Get username for created_by field
    user_row = await _fetchrow("SELECT username FROM users WHERE id = $1", user_id)
    created_by = f"task created by '{user_row['username']}'" if user_row else None

    row = await _fetchrow(
        """
        INSERT INTO todos (title, description, status, due_date, user_id, created_by, created_at)
        VALUES ($1, $2, 'pending', $3, $4, $5, NOW())
        RETURNING id
        """,
        title,
        description or None,
        parsed_due_date,
        user_id,
        created_by,
    )
    due_info = f" (due: {parsed_due_date.strftime('%Y-%m-%d')})" if parsed_due_date else ""
    return f"Task #{row['id']} created: '{title}'{due_info}"


@mcp.tool()
async def list_tasks(user_id: int, status: str = "all") -> str:
    """List all tasks for the authenticated user, optionally filtered by status.

    Args:
        user_id: The authenticated user's ID.
        status: Filter by status - 'all', 'pending', or 'completed'.
    """
    if status != "all":
        rows = await _fetch(
            "SELECT * FROM todos WHERE user_id = $1 AND status = $2 ORDER BY created_at ASC",
            user_id,
            status,
        )
    else:
        rows = await _fetch(
            "SELECT * FROM todos WHERE user_id = $1 ORDER BY created_at ASC",
            user_id,
        )

    if not rows:
        if status == "all":
            return "No tasks found. Create one by asking me to add a task."
        return f"No {status} tasks found."

    lines = []
    for t in rows:
        icon = "\u2713" if t["status"] == "completed" else "\u25cb"
        due = f" [due: {t['due_date'].strftime('%Y-%m-%d')}]" if t["due_date"] else ""
        lines.append(f"{icon} #{t['id']} {t['title']} ({t['status']}){due}")
    return "\n".join(lines)


@mcp.tool()
async def update_task(
    user_id: int,
    task_id: int,
    title: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
) -> str:
    """Update a task's title, status, description, or due date.

    Args:
        user_id: The authenticated user's ID.
        task_id: The ID of the task to update.
        title: New title for the task.
        status: New status - 'pending' or 'completed'.
        description: New description for the task.
        due_date: New due date (YYYY-MM-DD) or 'none' to remove.
    """
    row = await _fetchrow(
        "SELECT * FROM todos WHERE id = $1 AND user_id = $2", task_id, user_id
    )
    if not row:
        return f"Task #{task_id} not found or you don't have access to it."

    updates = []
    set_clauses = []
    params = []
    idx = 1

    if title is not None:
        idx += 1
        set_clauses.append(f"title = ${idx}")
        params.append(title)
        updates.append(f"title \u2192 '{title}'")

    if status is not None:
        if status not in ("pending", "completed"):
            return "Invalid status. Use: pending, completed"
        idx += 1
        set_clauses.append(f"status = ${idx}")
        params.append(status)
        updates.append(f"status \u2192 {status}")

    if description is not None:
        idx += 1
        set_clauses.append(f"description = ${idx}")
        params.append(description)
        updates.append("description updated")

    if due_date is not None:
        if due_date.lower() == "none":
            idx += 1
            set_clauses.append(f"due_date = ${idx}")
            params.append(None)
            updates.append("due date removed")
        else:
            try:
                parsed = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                idx += 1
                set_clauses.append(f"due_date = ${idx}")
                params.append(parsed)
                updates.append(f"due date \u2192 {parsed.strftime('%Y-%m-%d')}")
            except (ValueError, AttributeError):
                return "Invalid due date format. Use YYYY-MM-DD format."

    if not updates:
        return "No changes specified."

    idx += 1
    set_clauses.append(f"updated_at = ${idx}")
    params.append(datetime.utcnow())

    query = f"UPDATE todos SET {', '.join(set_clauses)} WHERE id = $1"
    await _execute(query, task_id, *params)
    return f"Task #{task_id} '{row['title']}' updated: {', '.join(updates)}"


@mcp.tool()
async def delete_task(user_id: int, task_id: int) -> str:
    """Delete a task.

    Args:
        user_id: The authenticated user's ID.
        task_id: The ID of the task to delete.
    """
    row = await _fetchrow(
        "SELECT title FROM todos WHERE id = $1 AND user_id = $2", task_id, user_id
    )
    if not row:
        return f"Task #{task_id} not found or you don't have access to it."

    await _execute("DELETE FROM todos WHERE id = $1 AND user_id = $2", task_id, user_id)
    return f"Task #{task_id} '{row['title']}' deleted successfully."


@mcp.tool()
async def get_task_details(user_id: int, task_id: int) -> str:
    """Get detailed information about a specific task.

    Args:
        user_id: The authenticated user's ID.
        task_id: The ID of the task.
    """
    row = await _fetchrow(
        "SELECT * FROM todos WHERE id = $1 AND user_id = $2", task_id, user_id
    )
    if not row:
        return f"Task #{task_id} not found or you don't have access to it."

    due_str = row["due_date"].strftime("%Y-%m-%d") if row["due_date"] else "No due date"
    created_by_str = row["created_by"] if row["created_by"] else "Unknown"
    return f"""Task #{row['id']}:
  Title: {row['title']}
  Description: {row['description'] or 'No description'}
  Status: {row['status']}
  Due Date: {due_str}
  Created By: {created_by_str}
  Created: {row['created_at'].strftime('%Y-%m-%d %H:%M')}
  Updated: {row['updated_at'].strftime('%Y-%m-%d %H:%M') if row['updated_at'] else 'Never'}"""


@mcp.tool()
async def search_tasks_by_keyword(user_id: int, keyword: str) -> str:
    """Search for tasks containing a keyword in the title or description.
    Uses intelligent fuzzy matching to find similar words.

    Args:
        user_id: The authenticated user's ID.
        keyword: The keyword to search for (uses fuzzy matching).
    """
    rows = await _fetch(
        "SELECT * FROM todos WHERE user_id = $1 ORDER BY created_at DESC", user_id
    )

    if not rows:
        return "You don't have any tasks yet."

    tasks = [dict(r) for r in rows]
    keyword_lower = keyword.lower()

    # Exact substring match first
    exact = [
        t
        for t in tasks
        if keyword_lower in t["title"].lower()
        or (t["description"] and keyword_lower in t["description"].lower())
    ]

    if exact:
        matched_tasks = exact
        match_type = f"'{keyword}'"
    else:
        fuzzy = _fuzzy_match(keyword, tasks)
        if fuzzy:
            matched_tasks = [t for t, _ in fuzzy]
            best = fuzzy[0][1]
            if best >= 0.9:
                match_type = f"'{keyword}' (exact match)"
            elif best >= 0.7:
                match_type = f"'{keyword}' (similar match)"
            else:
                match_type = f"'{keyword}' (fuzzy match)"
        else:
            return f"No tasks found matching '{keyword}' or similar words."

    if len(matched_tasks) == 1:
        t = matched_tasks[0]
        icon = "\u2713" if t["status"] == "completed" else "\u25cb"
        desc = f" - {t['description']}" if t["description"] else ""
        due = f" [due: {t['due_date'].strftime('%Y-%m-%d')}]" if t["due_date"] else ""
        return f"Found 1 task matching {match_type}:\n{icon} #{t['id']} {t['title']} ({t['status']}){due}{desc}"

    lines = [f"Found {len(matched_tasks)} tasks matching {match_type}:"]
    for t in matched_tasks[:10]:
        icon = "\u2713" if t["status"] == "completed" else "\u25cb"
        desc_text = t["description"] or ""
        desc = f" - {desc_text[:50]}..." if len(desc_text) > 50 else (f" - {desc_text}" if desc_text else "")
        due = f" [due: {t['due_date'].strftime('%Y-%m-%d')}]" if t["due_date"] else ""
        lines.append(f"{icon} #{t['id']} {t['title']} ({t['status']}){due}{desc}")
    if len(matched_tasks) > 10:
        lines.append(f"... and {len(matched_tasks) - 10} more")
    return "\n".join(lines)


@mcp.tool()
async def batch_delete_tasks(user_id: int, task_ids: str) -> str:
    """Delete multiple tasks in one command.

    Args:
        user_id: The authenticated user's ID.
        task_ids: Comma-separated task IDs (e.g., "1,2,3").
    """
    try:
        ids = [int(i.strip()) for i in task_ids.split(",") if i.strip()]
    except ValueError:
        return "Invalid task IDs format. Use comma-separated numbers like '1,2,3'."

    if not ids:
        return "No task IDs provided."
    if len(ids) > 100:
        return "Too many tasks. Maximum 100 tasks can be deleted at once."

    rows = await _fetch(
        "SELECT id, title FROM todos WHERE id = ANY($1) AND user_id = $2",
        ids,
        user_id,
    )

    if not rows:
        return f"No tasks found with IDs: {task_ids}"

    found_ids = [r["id"] for r in rows]
    await _execute(
        "DELETE FROM todos WHERE id = ANY($1) AND user_id = $2", found_ids, user_id
    )

    missing = set(ids) - set(found_ids)
    result = f"Successfully deleted {len(found_ids)} task(s): " + ", ".join(
        f"#{i}" for i in found_ids
    )
    if missing:
        result += f"\n\u26a0\ufe0f Tasks not found or no access: " + ", ".join(
            f"#{i}" for i in sorted(missing)
        )
    return result


@mcp.tool()
async def batch_update_tasks(
    user_id: int,
    task_ids: str,
    title: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
) -> str:
    """Update multiple tasks at once with the same values.

    Args:
        user_id: The authenticated user's ID.
        task_ids: Comma-separated task IDs (e.g., "1,2,3").
        title: New title to set for all tasks.
        status: New status - 'pending' or 'completed'.
        description: New description to set for all tasks.
        due_date: New due date (YYYY-MM-DD) or 'none' to remove.
    """
    try:
        ids = [int(i.strip()) for i in task_ids.split(",") if i.strip()]
    except ValueError:
        return "Invalid task IDs format. Use comma-separated numbers like '1,2,3'."

    if not ids:
        return "No task IDs provided."
    if len(ids) > 100:
        return "Too many tasks. Maximum 100 tasks can be updated at once."

    if status is not None and status not in ("pending", "completed"):
        return "Invalid status. Use: pending, completed"

    parsed_due_date = None
    remove_due_date = False
    if due_date is not None:
        if due_date.lower() == "none":
            remove_due_date = True
        else:
            try:
                parsed_due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return "Invalid due date format. Use YYYY-MM-DD format or 'none'."

    if not any([title, status, description, due_date]):
        return "No updates specified. Provide at least one field to update."

    # Build dynamic UPDATE
    set_clauses = []
    params = []
    idx = 0

    if title is not None:
        idx += 1
        set_clauses.append(f"title = ${idx}")
        params.append(title)
    if status is not None:
        idx += 1
        set_clauses.append(f"status = ${idx}")
        params.append(status)
    if description is not None:
        idx += 1
        set_clauses.append(f"description = ${idx}")
        params.append(description)
    if remove_due_date:
        idx += 1
        set_clauses.append(f"due_date = ${idx}")
        params.append(None)
    elif parsed_due_date is not None:
        idx += 1
        set_clauses.append(f"due_date = ${idx}")
        params.append(parsed_due_date)

    idx += 1
    set_clauses.append(f"updated_at = ${idx}")
    params.append(datetime.utcnow())

    idx += 1
    ids_param = idx
    idx += 1
    uid_param = idx

    query = f"UPDATE todos SET {', '.join(set_clauses)} WHERE id = ANY(${ids_param}) AND user_id = ${uid_param} RETURNING id"
    updated_rows = await _fetch(query, *params, ids, user_id)
    updated_ids = [r["id"] for r in updated_rows]

    if not updated_ids:
        return f"No tasks found with IDs: {task_ids}"

    updates_made = []
    if title:
        updates_made.append(f"title \u2192 '{title}'")
    if status:
        updates_made.append(f"status \u2192 {status}")
    if description:
        updates_made.append("description updated")
    if remove_due_date:
        updates_made.append("due date removed")
    elif parsed_due_date:
        updates_made.append(f"due date \u2192 {parsed_due_date.strftime('%Y-%m-%d')}")

    missing = set(ids) - set(updated_ids)
    result = f"Successfully updated {len(updated_ids)} task(s): " + ", ".join(
        f"#{i}" for i in updated_ids
    )
    result += f"\nChanges: {', '.join(updates_made)}"
    if missing:
        result += f"\n\u26a0\ufe0f Tasks not found or no access: " + ", ".join(
            f"#{i}" for i in sorted(missing)
        )
    return result


# ---------------------------------------------------------------------------
# SQL tools
# ---------------------------------------------------------------------------

DATABASE_SCHEMA = """
Available Tables:
1. users:
   - id (integer, primary key)
   - username (string, unique)
   - email (string, unique)
   - hashed_password (string)
   - created_at (timestamp)

2. todos:
   - id (integer, primary key)
   - title (string)
   - description (string, nullable)
   - status (string: 'pending' or 'completed')
   - user_id (integer, foreign key to users.id)
   - created_by (string, nullable)
   - created_at (timestamp)
   - updated_at (timestamp, nullable)
"""


@mcp.tool()
async def execute_sql_query(user_id: int, query: str) -> str:
    """Execute a custom SQL SELECT query on the database.

    SAFETY: Only SELECT queries allowed. Must include user_id filtering.
    Use {user_id} placeholder which will be replaced with the actual user ID.

    Args:
        user_id: The authenticated user's ID.
        query: The SQL SELECT query to execute.
    """
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT"):
        return "\u274c Error: Only SELECT queries are allowed."

    dangerous = [
        "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE",
        "GRANT", "REVOKE", "EXECUTE", "EXEC", "--", "/*", "*/", ";--", "xp_",
    ]
    for kw in dangerous:
        if kw in query_upper:
            return f"\u274c Error: '{kw}' operations are not allowed."

    if "user_id" not in query.lower() and "users" not in query.lower():
        return "\u274c Error: Query must include user_id filtering."

    if "user_id" in query.lower() and "{user_id}" not in query:
        return "\u274c Error: Use {user_id} placeholder for user filtering."

    query = query.replace("{user_id}", str(user_id))

    try:
        rows = await _fetch(query)
        if not rows:
            return "Query executed successfully but returned no results."

        columns = list(rows[0].keys())
        lines = [f"Query returned {len(rows)} row(s):\n"]
        header = " | ".join(columns)
        lines.append(header)
        lines.append("-" * len(header))
        for row in rows[:50]:
            lines.append(" | ".join(str(row[c]) for c in columns))
        if len(rows) > 50:
            lines.append(f"\n... and {len(rows) - 50} more rows")
        return "\n".join(lines)
    except Exception as e:
        return f"\u274c SQL Error: {e}\n\nPlease check your query syntax and try again."


@mcp.tool()
async def generate_sql_query(user_id: int, question: str) -> str:
    """Generate a SQL query from a natural language question about the user's data.

    Args:
        user_id: The authenticated user's ID.
        question: Natural language question about the data.
    """
    patterns = {
        r"how many.*completed": f"SELECT COUNT(*) as completed_count FROM todos WHERE user_id = {user_id} AND status = 'completed'",
        r"how many.*pending": f"SELECT COUNT(*) as pending_count FROM todos WHERE user_id = {user_id} AND status = 'pending'",
        r"how many.*task": f"SELECT COUNT(*) as total_tasks FROM todos WHERE user_id = {user_id}",
        r"list.*task": f"SELECT id, title, status, created_at FROM todos WHERE user_id = {user_id} ORDER BY created_at DESC",
        r"show.*task.*today": f"SELECT id, title, status FROM todos WHERE user_id = {user_id} AND DATE(created_at) = CURRENT_DATE",
        r"task.*created.*week": f"SELECT id, title, created_at FROM todos WHERE user_id = {user_id} AND created_at >= CURRENT_DATE - INTERVAL '7 days'",
    }

    question_lower = question.lower()
    for pattern, sql in patterns.items():
        if re.search(pattern, question_lower):
            return f"Generated SQL query:\n```sql\n{sql}\n```\n\nUse execute_sql_query to run this query."

    return f"""I can help generate SQL queries for questions about your todos and user data.

Database Schema:
{DATABASE_SCHEMA}

Your question: "{question}"

Try asking questions like:
- "How many completed tasks do I have?"
- "Show me tasks created this week"
- "List all my pending tasks"
- "What tasks did I create today?"

Or provide a more specific SQL query pattern you'd like to use."""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
