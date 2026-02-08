"""
Orchestration tools for the agent to coordinate complex multi-step tasks.
"""

from typing import List
from pydantic import BaseModel, Field
from agents import function_tool
from agents.tool_context import ToolContext

from app.agent.context import AgentContext
from app.agent.orchestrator import TaskScheduler, TaskType


# Pydantic models for strict schema compliance
class TaskCreateInput(BaseModel):
    """Input for creating a single task."""
    title: str = Field(..., description="Task title")
    description: str = Field(default="", description="Task description")
    due_date: str = Field(default="", description="Due date in YYYY-MM-DD format")


class TaskUpdateInput(BaseModel):
    """Input for updating a single task."""
    task_id: int = Field(..., description="ID of the task to update")
    status: str = Field(default="", description="New status: pending or completed")
    description: str = Field(default="", description="New description")
    due_date: str = Field(default="", description="New due date in YYYY-MM-DD format")


# Global task scheduler (in production, use Redis or database)
_task_schedulers: dict[int, TaskScheduler] = {}


def get_scheduler(user_id: int) -> TaskScheduler:
    """Get or create a task scheduler for a user."""
    if user_id not in _task_schedulers:
        _task_schedulers[user_id] = TaskScheduler()
    return _task_schedulers[user_id]


@function_tool
async def schedule_bulk_create(
    ctx: ToolContext,
    task1_title: str,
    task1_description: str = "",
    task1_due_date: str = "",
    task2_title: str = "",
    task2_description: str = "",
    task2_due_date: str = "",
    task3_title: str = "",
    task3_description: str = "",
    task3_due_date: str = "",
) -> str:
    """
    Create up to 3 tasks sequentially (one by one) to avoid database conflicts.
    
    Use this when the user wants to create multiple tasks at once.
    All tasks are created sequentially to prevent connection errors.
    
    Args:
        task1_title: Title of the first task (required).
        task1_description: Description of the first task.
        task1_due_date: Due date of the first task (YYYY-MM-DD).
        task2_title: Title of the second task (optional).
        task2_description: Description of the second task.
        task2_due_date: Due date of the second task (YYYY-MM-DD).
        task3_title: Title of the third task (optional).
        task3_description: Description of the third task.
        task3_due_date: Due date of the third task (YYYY-MM-DD).
    
    Returns:
        Summary of all created tasks.
    """
    agent_ctx: AgentContext = ctx.context
    
    from app.agent.tools import create_task
    results = []
    
    # Create tasks one by one
    tasks_to_create = [
        (task1_title, task1_description, task1_due_date),
    ]
    
    if task2_title:
        tasks_to_create.append((task2_title, task2_description, task2_due_date))
    if task3_title:
        tasks_to_create.append((task3_title, task3_description, task3_due_date))
    
    for i, (title, desc, due) in enumerate(tasks_to_create, 1):
        try:
            result = await create_task(ctx, title=title, description=desc, due_date=due or None)
            results.append(f"✅ Task {i}: {result}")
        except Exception as e:
            results.append(f"❌ Task {i} failed: {str(e)}")
    
    return "\n".join(results)


@function_tool
async def schedule_bulk_update(
    ctx: ToolContext,
    task_id_1: int,
    status_1: str = "",
    task_id_2: int = 0,
    status_2: str = "",
    task_id_3: int = 0,
    status_3: str = "",
) -> str:
    """
    Update multiple tasks sequentially (one by one) to avoid database conflicts.
    
    Use this when the user wants to update multiple tasks at once.
    
    Args:
        task_id_1: ID of the first task to update (required).
        status_1: New status for the first task (pending or completed).
        task_id_2: ID of the second task to update (optional).
        status_2: New status for the second task.
        task_id_3: ID of the third task to update (optional).
        status_3: New status for the third task.
    
    Returns:
        Summary of all updates.
    """
    agent_ctx: AgentContext = ctx.context
    
    from app.agent.tools import update_task
    results = []
    
    # Update tasks one by one
    updates = [(task_id_1, status_1)]
    if task_id_2 > 0:
        updates.append((task_id_2, status_2))
    if task_id_3 > 0:
        updates.append((task_id_3, status_3))
    
    for i, (task_id, status) in enumerate(updates, 1):
        try:
            result = await update_task(
                ctx,
                task_id=task_id,
                status=status if status else None,
            )
            results.append(f"✅ Update {i}: {result}")
        except Exception as e:
            results.append(f"❌ Update {i} failed: {str(e)}")
    
    return "\n".join(results)


@function_tool
async def schedule_bulk_queries(
    ctx: ToolContext,
    query1: str,
    query2: str = "",
    query3: str = "",
) -> str:
    """
    Execute multiple SQL queries sequentially, one by one.
    
    Use this when the user wants to run multiple database queries.
    Queries are executed in order to avoid connection conflicts.
    
    Args:
        query1: First SQL SELECT query to execute (required).
        query2: Second SQL SELECT query to execute (optional).
        query3: Third SQL SELECT query to execute (optional).
    
    Returns:
        Combined results from all queries.
    """
    agent_ctx: AgentContext = ctx.context
    
    from app.agent.tools import execute_sql_query
    results = []
    
    queries = [query1]
    if query2:
        queries.append(query2)
    if query3:
        queries.append(query3)
    
    for i, query in enumerate(queries, 1):
        try:
            result = await execute_sql_query(ctx, query)
            results.append(f"Query #{i} Result:\n{result}\n")
        except Exception as e:
            results.append(f"Query #{i} Failed: {str(e)}\n")
    
    return "\n".join(results)
