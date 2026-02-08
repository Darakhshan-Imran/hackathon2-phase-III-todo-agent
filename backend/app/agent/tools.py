from datetime import datetime
from typing import Optional, List, Tuple
import re
from difflib import SequenceMatcher

from agents import function_tool
from agents.tool_context import ToolContext
from sqlmodel import select, text

from app.models import Todo, User
from app.agent.context import AgentContext


def calculate_similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_similar_matches(keyword: str, all_tasks: List[Todo], threshold: float = 0.6) -> List[Tuple[Todo, float]]:
    """Find tasks with similar words using fuzzy matching.
    
    Args:
        keyword: The search term
        all_tasks: All user tasks to search through
        threshold: Minimum similarity score (0.0-1.0), default 0.6
        
    Returns:
        List of (task, similarity_score) tuples, sorted by score
    """
    keyword_lower = keyword.lower()
    matches = []
    
    for task in all_tasks:
        # Check title and description
        text_to_search = f"{task.title} {task.description or ''}".lower()
        
        # Split into words for token-based matching
        words = re.findall(r'\w+', text_to_search)
        
        max_similarity = 0.0
        
        # Check similarity with each word
        for word in words:
            similarity = calculate_similarity(keyword_lower, word)
            max_similarity = max(max_similarity, similarity)
            
            # Also check if keyword is substring of word or vice versa
            if keyword_lower in word or word in keyword_lower:
                max_similarity = max(max_similarity, 0.8)
        
        # If similarity exceeds threshold, add to matches
        if max_similarity >= threshold:
            matches.append((task, max_similarity))
    
    # Sort by similarity score (highest first)
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


@function_tool
async def create_task(
    ctx: ToolContext,
    title: str,
    description: str = "",
    due_date: Optional[str] = None,
) -> str:
    """Create a new task for the authenticated user.

    Args:
        title: The title of the task.
        description: Optional description of the task.
        due_date: Optional due date in ISO format (YYYY-MM-DD) or natural language like '2026-02-10' or 'tomorrow'.
    """
    agent_ctx: AgentContext = ctx.context

    # Parse due_date if provided
    parsed_due_date = None
    if due_date:
        try:
            # Try parsing ISO format
            parsed_due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            # If parsing fails, set to None and continue
            parsed_due_date = None

    # Get username for created_by field
    user_query = select(User).where(User.id == agent_ctx.user_id)
    user_result = await agent_ctx.db_session.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    created_by_text = None
    if user:
        created_by_text = f"task created by '{user.username}'"

    todo = Todo(
        title=title,
        description=description if description else None,
        status="pending",
        due_date=parsed_due_date,
        user_id=agent_ctx.user_id,
        created_by=created_by_text,
    )

    agent_ctx.db_session.add(todo)
    await agent_ctx.db_session.flush()  # Flush to get ID without committing
    await agent_ctx.db_session.refresh(todo)

    due_info = f" (due: {parsed_due_date.strftime('%Y-%m-%d')})" if parsed_due_date else ""
    return f"Task #{todo.id} created: '{title}'{due_info}"


@function_tool
async def list_tasks(
    ctx: ToolContext,
    status: str = "all",
) -> str:
    """List all tasks for the authenticated user, optionally filtered by status.

    Args:
        status: Filter by status - 'all', 'pending', or 'completed'.
    """
    agent_ctx: AgentContext = ctx.context

    query = select(Todo).where(Todo.user_id == agent_ctx.user_id)

    if status != "all":
        query = query.where(Todo.status == status)

    query = query.order_by(Todo.created_at.asc())

    result = await agent_ctx.db_session.execute(query)
    tasks = result.scalars().all()

    if not tasks:
        if status == "all":
            return "No tasks found. Create one by asking me to add a task."
        return f"No {status} tasks found."

    lines = []
    for task in tasks:
        status_icon = "✓" if task.status == "completed" else "○"
        due_info = f" [due: {task.due_date.strftime('%Y-%m-%d')}]" if task.due_date else ""
        lines.append(f"{status_icon} #{task.id} {task.title} ({task.status}){due_info}")

    return "\n".join(lines)


@function_tool
async def update_task(
    ctx: ToolContext,
    task_id: int,
    title: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
) -> str:
    """Update a task's title, status, description, or due date. At least one field must be provided.

    Args:
        task_id: The ID of the task to update (required).
        title: (Optional) New title for the task (rename).
        status: (Optional) New status - 'pending' or 'completed'.
        description: (Optional) New description for the task.
        due_date: (Optional) New due date in ISO format (YYYY-MM-DD) or 'none' to remove due date.
    """
    agent_ctx: AgentContext = ctx.context

    query = select(Todo).where(
        Todo.id == task_id,
        Todo.user_id == agent_ctx.user_id,
    )
    result = await agent_ctx.db_session.execute(query)
    todo = result.scalar_one_or_none()

    if not todo:
        return f"Task #{task_id} not found or you don't have access to it."

    updates = []

    if title is not None:
        todo.title = title
        updates.append(f"title → '{title}'")

    if status is not None:
        valid_statuses = ["pending", "completed"]
        if status not in valid_statuses:
            return f"Invalid status. Use: {', '.join(valid_statuses)}"
        todo.status = status
        updates.append(f"status → {status}")

    if description is not None:
        todo.description = description
        updates.append("description updated")

    if due_date is not None:
        if due_date.lower() == "none":
            todo.due_date = None
            updates.append("due date removed")
        else:
            try:
                parsed_due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                todo.due_date = parsed_due_date
                updates.append(f"due date → {parsed_due_date.strftime('%Y-%m-%d')}")
            except (ValueError, AttributeError):
                return f"Invalid due date format. Use YYYY-MM-DD format."

    if not updates:
        return "No changes specified."

    todo.updated_at = datetime.utcnow()
    await agent_ctx.db_session.flush()  # Flush changes without committing

    return f"Task #{task_id} '{todo.title}' updated: {', '.join(updates)}"


@function_tool
async def delete_task(
    ctx: ToolContext,
    task_id: int,
) -> str:
    """Delete a task.

    Args:
        task_id: The ID of the task to delete.
    """
    agent_ctx: AgentContext = ctx.context

    query = select(Todo).where(
        Todo.id == task_id,
        Todo.user_id == agent_ctx.user_id,
    )
    result = await agent_ctx.db_session.execute(query)
    todo = result.scalar_one_or_none()

    if not todo:
        return f"Task #{task_id} not found or you don't have access to it."

    title = todo.title
    await agent_ctx.db_session.delete(todo)
    await agent_ctx.db_session.flush()  # Flush deletion without committing

    return f"Task #{task_id} '{title}' deleted successfully."


@function_tool
async def batch_delete_tasks(
    ctx: ToolContext,
    task_ids: str,
) -> str:
    """Delete multiple tasks in one command.

    Args:
        task_ids: Comma-separated task IDs (e.g., "1,2,3" or "5, 8, 12").
    """
    agent_ctx: AgentContext = ctx.context

    # Parse task IDs
    try:
        ids = [int(id.strip()) for id in task_ids.split(",") if id.strip()]
    except ValueError:
        return "Invalid task IDs format. Use comma-separated numbers like '1,2,3'."

    if not ids:
        return "No task IDs provided."

    if len(ids) > 100:
        return "Too many tasks. Maximum 100 tasks can be deleted at once."

    # Fetch tasks that belong to the user
    query = select(Todo).where(
        Todo.id.in_(ids),
        Todo.user_id == agent_ctx.user_id,
    )
    result = await agent_ctx.db_session.execute(query)
    tasks = result.scalars().all()

    if not tasks:
        return f"No tasks found with IDs: {task_ids}"

    # Track deleted task info
    deleted_titles = []
    deleted_ids = []

    for task in tasks:
        deleted_titles.append(task.title)
        deleted_ids.append(task.id)
        await agent_ctx.db_session.delete(task)

    await agent_ctx.db_session.flush()

    # Find missing IDs (tasks that weren't found)
    found_ids = set(deleted_ids)
    requested_ids = set(ids)
    missing_ids = requested_ids - found_ids

    result_msg = f"Successfully deleted {len(deleted_ids)} task(s): " + ", ".join([f"#{id}" for id in deleted_ids])

    if missing_ids:
        result_msg += f"\n⚠️ Tasks not found or no access: " + ", ".join([f"#{id}" for id in sorted(missing_ids)])

    return result_msg


@function_tool
async def batch_update_tasks(
    ctx: ToolContext,
    task_ids: str,
    title: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
) -> str:
    """Update multiple tasks at once with the same values.

    Args:
        task_ids: Comma-separated task IDs (e.g., "1,2,3" or "5, 8, 12").
        title: New title to set for all tasks.
        status: New status - 'pending' or 'completed'.
        description: New description to set for all tasks.
        due_date: New due date in ISO format (YYYY-MM-DD) or 'none' to remove due date.
    """
    agent_ctx: AgentContext = ctx.context

    # Parse task IDs
    try:
        ids = [int(id.strip()) for id in task_ids.split(",") if id.strip()]
    except ValueError:
        return "Invalid task IDs format. Use comma-separated numbers like '1,2,3'."

    if not ids:
        return "No task IDs provided."

    if len(ids) > 100:
        return "Too many tasks. Maximum 100 tasks can be updated at once."

    # Validate status if provided
    if status is not None:
        valid_statuses = ["pending", "completed"]
        if status not in valid_statuses:
            return f"Invalid status. Use: {', '.join(valid_statuses)}"

    # Parse due date if provided
    parsed_due_date = None
    remove_due_date = False
    if due_date is not None:
        if due_date.lower() == "none":
            remove_due_date = True
        else:
            try:
                parsed_due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return f"Invalid due date format. Use YYYY-MM-DD format or 'none'."

    # Check if any update field is provided
    if not any([title, status, description, due_date]):
        return "No updates specified. Provide at least one field to update."

    # Fetch tasks that belong to the user
    query = select(Todo).where(
        Todo.id.in_(ids),
        Todo.user_id == agent_ctx.user_id,
    )
    result = await agent_ctx.db_session.execute(query)
    tasks = result.scalars().all()

    if not tasks:
        return f"No tasks found with IDs: {task_ids}"

    # Track updates
    updated_ids = []
    updates_made = []

    # Apply updates to all tasks
    for task in tasks:
        if title is not None:
            task.title = title
        if status is not None:
            task.status = status
        if description is not None:
            task.description = description
        if remove_due_date:
            task.due_date = None
        elif parsed_due_date is not None:
            task.due_date = parsed_due_date

        task.updated_at = datetime.utcnow()
        updated_ids.append(task.id)

    await agent_ctx.db_session.flush()

    # Build update summary
    if title:
        updates_made.append(f"title → '{title}'")
    if status:
        updates_made.append(f"status → {status}")
    if description:
        updates_made.append("description updated")
    if remove_due_date:
        updates_made.append("due date removed")
    elif parsed_due_date:
        updates_made.append(f"due date → {parsed_due_date.strftime('%Y-%m-%d')}")

    # Find missing IDs
    found_ids = set(updated_ids)
    requested_ids = set(ids)
    missing_ids = requested_ids - found_ids

    result_msg = f"Successfully updated {len(updated_ids)} task(s): " + ", ".join([f"#{id}" for id in updated_ids])
    result_msg += f"\nChanges: {', '.join(updates_made)}"

    if missing_ids:
        result_msg += f"\n⚠️ Tasks not found or no access: " + ", ".join([f"#{id}" for id in sorted(missing_ids)])

    return result_msg


@function_tool
async def search_tasks_by_keyword(
    ctx: ToolContext,
    keyword: str,
) -> str:
    """Search for tasks containing a keyword in the title or description.
    
    Uses intelligent fuzzy matching to find similar words (e.g., 'plane' matches 'aeroplane', 
    'planes' matches 'plane', 'folding' matches 'fold'). 
    
    Perfect for when users don't know exact task names. Searches across all task statuses.

    Args:
        keyword: The keyword to search for (uses fuzzy matching for similar words).
    """
    agent_ctx: AgentContext = ctx.context

    # Build base query to get all user tasks (for fuzzy matching)
    query = select(Todo).where(Todo.user_id == agent_ctx.user_id)
    query = query.order_by(Todo.created_at.desc())
    
    result = await agent_ctx.db_session.execute(query)
    all_tasks = result.scalars().all()
    
    if not all_tasks:
        return "You don't have any tasks yet."
    
    # Try exact substring match first (fast path)
    keyword_lower = keyword.lower()
    exact_matches = [
        task for task in all_tasks 
        if keyword_lower in task.title.lower() or 
           (task.description and keyword_lower in task.description.lower())
    ]
    
    # If exact matches found, use them
    if exact_matches:
        tasks = exact_matches
        match_type = f"'{keyword}'"
    else:
        # Use fuzzy matching to find similar words
        # Threshold 0.6 means 60% similarity required
        fuzzy_matches = find_similar_matches(keyword, all_tasks, threshold=0.6)
        
        if fuzzy_matches:
            # Take top matches (similarity >= 0.6)
            tasks = [task for task, score in fuzzy_matches]
            # Show what we matched on
            best_score = fuzzy_matches[0][1]
            if best_score >= 0.9:
                match_type = f"'{keyword}' (exact match)"
            elif best_score >= 0.7:
                match_type = f"'{keyword}' (similar match)"
            else:
                match_type = f"'{keyword}' (fuzzy match)"
        else:
            return f"No tasks found matching '{keyword}' or similar words."
    
    # Format results
    if len(tasks) == 1:
        task = tasks[0]
        status_icon = "✓" if task.status == "completed" else "○"
        desc = f" - {task.description}" if task.description else ""
        due_info = f" [due: {task.due_date.strftime('%Y-%m-%d')}]" if task.due_date else ""
        return (
            f"Found 1 task matching {match_type}:\n"
            f"{status_icon} #{task.id} {task.title} ({task.status}){due_info}{desc}"
        )

    # Multiple tasks found
    lines = [f"Found {len(tasks)} tasks matching {match_type}:"]
    for task in tasks[:10]:  # Limit to top 10 results
        status_icon = "✓" if task.status == "completed" else "○"
        desc = f" - {task.description[:50]}..." if task.description and len(task.description) > 50 else (f" - {task.description}" if task.description else "")
        due_info = f" [due: {task.due_date.strftime('%Y-%m-%d')}]" if task.due_date else ""
        lines.append(f"{status_icon} #{task.id} {task.title} ({task.status}){due_info}{desc}")
    
    if len(tasks) > 10:
        lines.append(f"... and {len(tasks) - 10} more")
    
    return "\n".join(lines)


@function_tool
async def get_task_details(
    ctx: ToolContext,
    task_id: int,
) -> str:
    """Get detailed information about a specific task.

    Args:
        task_id: The ID of the task.
    """
    agent_ctx: AgentContext = ctx.context

    query = select(Todo).where(
        Todo.id == task_id,
        Todo.user_id == agent_ctx.user_id,
    )
    result = await agent_ctx.db_session.execute(query)
    todo = result.scalar_one_or_none()

    if not todo:
        return f"Task #{task_id} not found or you don't have access to it."

    due_str = todo.due_date.strftime('%Y-%m-%d') if todo.due_date else 'No due date'
    created_by_str = todo.created_by if todo.created_by else 'Unknown'
    return f"""Task #{todo.id}:
  Title: {todo.title}
  Description: {todo.description or 'No description'}
  Status: {todo.status}
  Due Date: {due_str}
  Created By: {created_by_str}
  Created: {todo.created_at.strftime('%Y-%m-%d %H:%M')}
  Updated: {todo.updated_at.strftime('%Y-%m-%d %H:%M') if todo.updated_at else 'Never'}"""


# Database Schema Information
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
   - created_at (timestamp)
   - updated_at (timestamp, nullable)
"""


@function_tool
async def execute_sql_query(
    ctx: ToolContext,
    query: str,
) -> str:
    """Execute a custom SQL query on the database. Use this for complex queries or data analysis.
    
    IMPORTANT SAFETY RULES:
    - Only SELECT queries are allowed for safety
    - Query must filter by user_id to show only current user's data
    - No DROP, DELETE, UPDATE, INSERT, or other modifying queries
    
    Database Schema:
    {schema}
    
    Args:
        query: The SQL SELECT query to execute (must include WHERE user_id = current_user)
    
    Example queries:
    - "SELECT COUNT(*) as total FROM todos WHERE user_id = {user_id} AND status = 'completed'"
    - "SELECT DATE(created_at) as date, COUNT(*) as count FROM todos WHERE user_id = {user_id} GROUP BY DATE(created_at)"
    - "SELECT title, created_at FROM todos WHERE user_id = {user_id} ORDER BY created_at DESC LIMIT 5"
    """.format(schema=DATABASE_SCHEMA, user_id="{user_id}")
    
    agent_ctx: AgentContext = ctx.context
    
    # Security validation: Only allow SELECT queries
    query_clean = query.strip().upper()
    if not query_clean.startswith('SELECT'):
        return "❌ Error: Only SELECT queries are allowed for safety. No INSERT, UPDATE, DELETE, DROP, etc."
    
    # Enhanced dangerous keyword detection (including comment attempts)
    dangerous_keywords = [
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE', 
        'GRANT', 'REVOKE', 'EXECUTE', 'EXEC', '--', '/*', '*/', ';--', 'xp_'
    ]
    for keyword in dangerous_keywords:
        if keyword in query_clean:
            return f"❌ Error: '{keyword}' operations are not allowed for safety."
    
    # Ensure user_id filtering is present (strict check)
    if 'user_id' not in query.lower() and 'users' not in query.lower():
        return "❌ Error: Query must include user_id filtering to ensure data isolation. Add 'WHERE user_id = {user_id}' or join with users table."
    
    # Validate {user_id} placeholder exists if user_id mentioned
    if 'user_id' in query.lower() and '{user_id}' not in query:
        return "❌ Error: Use {user_id} placeholder for user filtering (e.g., WHERE user_id = {user_id})."
    
    # Replace {user_id} placeholder with actual user_id
    query = query.replace('{user_id}', str(agent_ctx.user_id))
    
    try:
        # Execute the query
        result = await agent_ctx.db_session.execute(text(query))
        rows = result.fetchall()
        
        if not rows:
            return "Query executed successfully but returned no results."
        
        # Format results
        if len(rows) > 0:
            # Get column names
            columns = list(rows[0]._mapping.keys())
            
            # Build result string
            lines = []
            lines.append(f"Query returned {len(rows)} row(s):\n")
            
            # Add header
            header = " | ".join(columns)
            lines.append(header)
            lines.append("-" * len(header))
            
            # Add rows (limit to 50 for readability)
            for i, row in enumerate(rows[:50]):
                row_data = " | ".join(str(row._mapping[col]) for col in columns)
                lines.append(row_data)
            
            if len(rows) > 50:
                lines.append(f"\n... and {len(rows) - 50} more rows")
            
            return "\n".join(lines)
        
        return "Query executed successfully but returned no results."
        
    except Exception as e:
        return f"❌ SQL Error: {str(e)}\n\nPlease check your query syntax and try again."


@function_tool
async def generate_sql_query(
    ctx: ToolContext,
    question: str,
) -> str:
    """Generate a SQL query from a natural language question about the user's data.
    
    This tool helps translate natural language questions into SQL queries.
    After generating the query, you should use execute_sql_query to run it.
    
    Database Schema:
    {schema}
    
    Args:
        question: Natural language question about the data
        
    Example questions:
    - "How many completed tasks do I have?"
    - "Show me my tasks created this week"
    - "What's the average number of tasks I create per day?"
    - "List all my pending tasks with their descriptions"
    """.format(schema=DATABASE_SCHEMA)
    
    agent_ctx: AgentContext = ctx.context
    
    # Common query patterns
    patterns = {
        r"how many.*completed": "SELECT COUNT(*) as completed_count FROM todos WHERE user_id = {user_id} AND status = 'completed'",
        r"how many.*pending": "SELECT COUNT(*) as pending_count FROM todos WHERE user_id = {user_id} AND status = 'pending'",
        r"how many.*task": "SELECT COUNT(*) as total_tasks FROM todos WHERE user_id = {user_id}",
        r"list.*task": "SELECT id, title, status, created_at FROM todos WHERE user_id = {user_id} ORDER BY created_at DESC",
        r"show.*task.*today": "SELECT id, title, status FROM todos WHERE user_id = {user_id} AND DATE(created_at) = CURRENT_DATE",
        r"task.*created.*week": "SELECT id, title, created_at FROM todos WHERE user_id = {user_id} AND created_at >= CURRENT_DATE - INTERVAL '7 days'",
    }
    
    question_lower = question.lower()
    
    # Try to match patterns
    for pattern, query_template in patterns.items():
        if re.search(pattern, question_lower):
            query = query_template.format(user_id=agent_ctx.user_id)
            return f"Generated SQL query:\n```sql\n{query}\n```\n\nUse execute_sql_query to run this query."
    
    # Provide general guidance if no pattern matches
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
