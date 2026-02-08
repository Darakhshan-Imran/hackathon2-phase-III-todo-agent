from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class AgentContext:
    """Context object passed to agent tools for database operations.

    This context is automatically injected into tools that have ToolContext
    as their first parameter when using Runner.run(context=...).
    """

    user_id: int
    db_session: AsyncSession
