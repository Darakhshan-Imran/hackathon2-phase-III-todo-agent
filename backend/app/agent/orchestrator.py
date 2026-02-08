"""
Multi-Agent Orchestration System with Task Scheduling

This module implements:
1. Task Scheduler - Breaks down complex requests into sequential tasks
2. Coordinator Agent - Delegates tasks to specialized agents
3. Query Executor - Executes database queries one by one
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio

from agents import Agent, Runner, RunConfig
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import AgentContext


class TaskType(Enum):
    """Types of tasks in the orchestration system."""
    CREATE_TASK = "create_task"
    UPDATE_TASK = "update_task"
    DELETE_TASK = "delete_task"
    QUERY_DATABASE = "query_database"
    SEARCH_TASKS = "search_tasks"


@dataclass
class ScheduledTask:
    """Represents a scheduled task in the queue."""
    task_id: int
    task_type: TaskType
    description: str
    parameters: Dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None


class TaskScheduler:
    """
    Schedules and executes tasks one by one in sequence.
    
    This ensures database operations don't conflict and allows
    for proper error handling and rollback.
    """
    
    def __init__(self):
        self.task_queue: List[ScheduledTask] = []
        self.current_task: Optional[ScheduledTask] = None
        self.completed_tasks: List[ScheduledTask] = []
        
    def add_task(
        self, 
        task_type: TaskType, 
        description: str, 
        parameters: Dict[str, Any]
    ) -> ScheduledTask:
        """Add a task to the queue."""
        task_id = len(self.task_queue) + len(self.completed_tasks) + 1
        task = ScheduledTask(
            task_id=task_id,
            task_type=task_type,
            description=description,
            parameters=parameters
        )
        self.task_queue.append(task)
        return task
    
    def get_next_task(self) -> Optional[ScheduledTask]:
        """Get the next pending task from the queue."""
        if self.task_queue:
            return self.task_queue.pop(0)
        return None
    
    def mark_completed(self, task: ScheduledTask, result: str):
        """Mark a task as completed."""
        task.status = "completed"
        task.result = result
        self.completed_tasks.append(task)
        
    def mark_failed(self, task: ScheduledTask, error: str):
        """Mark a task as failed."""
        task.status = "failed"
        task.error = error
        self.completed_tasks.append(task)
    
    def get_summary(self) -> str:
        """Get a summary of all tasks."""
        summary = []
        summary.append(f"Total tasks: {len(self.completed_tasks) + len(self.task_queue)}")
        summary.append(f"Completed: {len([t for t in self.completed_tasks if t.status == 'completed'])}")
        summary.append(f"Failed: {len([t for t in self.completed_tasks if t.status == 'failed'])}")
        summary.append(f"Pending: {len(self.task_queue)}")
        
        if self.completed_tasks:
            summary.append("\nCompleted Tasks:")
            for task in self.completed_tasks:
                status_icon = "✅" if task.status == "completed" else "❌"
                summary.append(f"{status_icon} Task #{task.task_id}: {task.description}")
                if task.result:
                    summary.append(f"   Result: {task.result}")
                if task.error:
                    summary.append(f"   Error: {task.error}")
        
        return "\n".join(summary)


class MultiAgentOrchestrator:
    """
    Coordinates multiple agents to work together on complex tasks.
    
    Features:
    - Breaks down complex requests into subtasks
    - Executes tasks sequentially to avoid conflicts
    - Provides progress updates
    - Handles errors gracefully
    """
    
    def __init__(self, groq_client: AsyncOpenAI, context: AgentContext):
        self.groq_client = groq_client
        self.context = context
        self.scheduler = TaskScheduler()
        
    async def execute_scheduled_tasks(
        self,
        agent: Agent,
        tasks: List[Dict[str, Any]],
        provide_updates: bool = True
    ) -> str:
        """
        Execute a list of tasks one by one.
        
        Args:
            agent: The agent to execute tasks with
            tasks: List of task dictionaries with 'type', 'description', 'parameters'
            provide_updates: Whether to provide progress updates
            
        Returns:
            Summary of all executed tasks
        """
        # Add all tasks to scheduler
        for task_info in tasks:
            self.scheduler.add_task(
                task_type=TaskType(task_info.get("type", "create_task")),
                description=task_info.get("description", ""),
                parameters=task_info.get("parameters", {})
            )
        
        results = []
        
        # Execute tasks one by one
        while True:
            task = self.scheduler.get_next_task()
            if not task:
                break
            
            task.status = "running"
            
            if provide_updates:
                results.append(f"⏳ Executing task #{task.task_id}: {task.description}")
            
            try:
                # Execute the task with the agent
                result = await Runner.run(
                    agent,
                    self._build_task_prompt(task),
                    context=self.context,
                    run_config=RunConfig(tracing_disabled=True)
                )
                
                self.scheduler.mark_completed(task, result.final_output)
                results.append(f"✅ Task #{task.task_id} completed: {result.final_output}")
                
            except Exception as e:
                error_msg = str(e)
                self.scheduler.mark_failed(task, error_msg)
                results.append(f"❌ Task #{task.task_id} failed: {error_msg}")
                
                # Optionally stop on error or continue
                # For now, we continue with remaining tasks
        
        # Add summary
        results.append("\n" + self.scheduler.get_summary())
        
        return "\n".join(results)
    
    def _build_task_prompt(self, task: ScheduledTask) -> str:
        """Build a prompt for the agent based on the scheduled task."""
        if task.task_type == TaskType.CREATE_TASK:
            title = task.parameters.get("title", "")
            description = task.parameters.get("description", "")
            due_date = task.parameters.get("due_date", "")
            
            prompt = f"Create a task with title '{title}'"
            if description:
                prompt += f" and description '{description}'"
            if due_date:
                prompt += f" due on {due_date}"
            return prompt
            
        elif task.task_type == TaskType.UPDATE_TASK:
            task_id = task.parameters.get("task_id")
            updates = task.parameters.get("updates", {})
            
            update_parts = []
            if "status" in updates:
                update_parts.append(f"status to {updates['status']}")
            if "description" in updates:
                update_parts.append(f"description to '{updates['description']}'")
            if "due_date" in updates:
                update_parts.append(f"due date to {updates['due_date']}")
            
            return f"Update task #{task_id}: {', '.join(update_parts)}"
            
        elif task.task_type == TaskType.DELETE_TASK:
            task_id = task.parameters.get("task_id")
            return f"Delete task #{task_id}"
            
        elif task.task_type == TaskType.SEARCH_TASKS:
            keyword = task.parameters.get("keyword", "")
            return f"Search for tasks containing '{keyword}'"
            
        elif task.task_type == TaskType.QUERY_DATABASE:
            query = task.parameters.get("query", "")
            return f"Execute this query: {query}"
        
        return task.description


class SequentialQueryExecutor:
    """
    Executes database queries one by one to avoid connection conflicts.
    
    This is especially useful when the agent needs to run multiple
    SQL queries in sequence.
    """
    
    def __init__(self, db_session: AsyncSession, user_id: int):
        self.db_session = db_session
        self.user_id = user_id
        self.query_queue: List[str] = []
        self.results: List[Dict[str, Any]] = []
    
    def add_query(self, query: str):
        """Add a query to the execution queue."""
        self.query_queue.append(query)
    
    async def execute_all(self) -> List[Dict[str, Any]]:
        """Execute all queued queries sequentially."""
        from app.agent.tools import execute_sql_query
        from app.agent.context import AgentContext
        
        results = []
        
        for i, query in enumerate(self.query_queue, 1):
            try:
                # Add small delay between queries to ensure connection stability
                if i > 1:
                    await asyncio.sleep(0.1)
                
                # Create context for this query
                context = AgentContext(
                    user_id=self.user_id,
                    db_session=self.db_session
                )
                
                # Execute query (this uses the tool's safety checks)
                from agents.tool_context import ToolContext
                tool_ctx = ToolContext(context=context)
                
                result = await execute_sql_query(tool_ctx, query)
                
                results.append({
                    "query_number": i,
                    "query": query,
                    "status": "success",
                    "result": result
                })
                
            except Exception as e:
                results.append({
                    "query_number": i,
                    "query": query,
                    "status": "failed",
                    "error": str(e)
                })
        
        self.results = results
        return results
    
    def get_summary(self) -> str:
        """Get a summary of all executed queries."""
        if not self.results:
            return "No queries executed yet."
        
        summary = []
        summary.append(f"Executed {len(self.results)} queries sequentially:")
        
        for result in self.results:
            status_icon = "✅" if result["status"] == "success" else "❌"
            summary.append(f"\n{status_icon} Query #{result['query_number']}:")
            summary.append(f"   SQL: {result['query'][:100]}...")
            
            if result["status"] == "success":
                summary.append(f"   Result: {result['result'][:200]}...")
            else:
                summary.append(f"   Error: {result['error']}")
        
        return "\n".join(summary)


# Helper function to parse complex requests into scheduled tasks
def parse_bulk_request(request: str) -> List[Dict[str, Any]]:
    """
    Parse a complex request into individual tasks.
    
    Example:
        "Create 3 tasks: Buy milk, Send email, Call John"
        
        Returns:
        [
            {"type": "create_task", "parameters": {"title": "Buy milk"}},
            {"type": "create_task", "parameters": {"title": "Send email"}},
            {"type": "create_task", "parameters": {"title": "Call John"}}
        ]
    """
    # This is a simple parser - can be enhanced with LLM-based parsing
    tasks = []
    
    # Detect patterns like "create 3 tasks" or "add 5 tasks"
    if "create" in request.lower() and "task" in request.lower():
        # Simple implementation - in production, use LLM to parse
        # For now, return empty to let the agent handle it
        pass
    
    return tasks
