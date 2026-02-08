from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import text
import re
import logging

from app.dependencies import get_db, get_current_user
from app.models import User
from app.schemas import SQLQueryRequest, SQLQueryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sql", tags=["SQL Queries"])

# Strict whitelist of allowed SQL patterns
_DANGEROUS_PATTERN = re.compile(
    r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE|"
    r"GRANT|REVOKE|MERGE|CALL|SET|COPY|LOAD|REPLACE|LOCK|UNLOCK)\b",
    re.IGNORECASE,
)
_SEMICOLON_PATTERN = re.compile(r";")
_COMMENT_PATTERN = re.compile(r"(--|/\*|\*/|#)")
_UNION_PATTERN = re.compile(r"\bUNION\b", re.IGNORECASE)


def _validate_query(query: str) -> None:
    """Validate SQL query is a safe read-only SELECT."""
    stripped = query.strip()

    # Must start with SELECT
    if not stripped.upper().startswith("SELECT"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only SELECT queries are allowed",
        )

    # Block SQL comments (used to bypass filters)
    if _COMMENT_PATTERN.search(stripped):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SQL comments are not allowed",
        )

    # Block semicolons (stacked queries)
    if _SEMICOLON_PATTERN.search(stripped):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple statements are not allowed",
        )

    # Block UNION (union-based injection)
    if _UNION_PATTERN.search(stripped):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UNION queries are not allowed",
        )

    # Block all write/DDL keywords
    match = _DANGEROUS_PATTERN.search(stripped)
    if match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{match.group()}' operations are not allowed",
        )


@router.post("/execute", response_model=SQLQueryResponse)
async def execute_sql(
    request: SQLQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a custom SQL query with safety restrictions.

    Security:
    - Only SELECT queries allowed
    - User ID injected via parameterised binding (not string replacement)
    - No UNION, comments, semicolons, or write operations
    """
    query = request.query.strip()

    _validate_query(query)

    # Replace {user_id} placeholder with a proper SQL parameter
    if "{user_id}" not in query.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must include {user_id} placeholder for data security",
        )

    # Use parameterised binding instead of string interpolation
    parameterised_query = query.replace("{user_id}", ":current_user_id")

    try:
        result = await db.execute(
            text(parameterised_query),
            {"current_user_id": current_user.id},
        )
        rows = result.fetchall()

        if not rows:
            return SQLQueryResponse(
                success=True,
                result="Query executed successfully but returned no results.",
                rows_affected=0,
            )

        # Format results
        columns = list(rows[0]._mapping.keys())
        lines = [f"Columns: {', '.join(columns)}"]
        lines.append("-" * 50)

        for row in rows[:100]:  # Limit to 100 rows
            row_data = " | ".join(str(row._mapping[col]) for col in columns)
            lines.append(row_data)

        if len(rows) > 100:
            lines.append(f"\n... and {len(rows) - 100} more rows")

        return SQLQueryResponse(
            success=True,
            result="\n".join(lines),
            rows_affected=len(rows),
        )

    except Exception as e:
        # Log the real error server-side, return generic message to client
        logger.error(f"SQL execution error for user {current_user.id}: {e}")
        return SQLQueryResponse(
            success=False,
            error="Query failed. Please check your SQL syntax and try again.",
        )


@router.get("/schema")
async def get_schema(current_user: User = Depends(get_current_user)):
    """Get the database schema information."""
    schema = {
        "tables": {
            "users": {
                "columns": {
                    "id": "integer (primary key)",
                    "username": "string (unique)",
                    "email": "string (unique)",
                    "hashed_password": "string",
                    "created_at": "timestamp"
                },
                "description": "User accounts"
            },
            "todos": {
                "columns": {
                    "id": "integer (primary key)",
                    "title": "string",
                    "description": "string (nullable)",
                    "status": "string (pending/completed)",
                    "user_id": "integer (foreign key to users.id)",
                    "created_at": "timestamp",
                    "updated_at": "timestamp (nullable)"
                },
                "description": "User tasks/todos"
            }
        },
        "example_queries": [
            "SELECT COUNT(*) as total FROM todos WHERE user_id = {user_id}",
            "SELECT status, COUNT(*) as count FROM todos WHERE user_id = {user_id} GROUP BY status",
            "SELECT * FROM todos WHERE user_id = {user_id} AND created_at >= CURRENT_DATE - INTERVAL '7 days'",
            "SELECT DATE(created_at) as date, COUNT(*) as tasks_created FROM todos WHERE user_id = {user_id} GROUP BY DATE(created_at)"
        ]
    }
    return schema
