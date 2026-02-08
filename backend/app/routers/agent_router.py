from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from openai import AsyncOpenAI
from agents import Runner, RunConfig, ModelSettings
from slowapi import Limiter
from slowapi.util import get_remote_address
import uuid
from datetime import datetime
from typing import List

from app.dependencies import get_db, get_current_user, get_groq_client
from app.models import User, ConversationMessage
from app.schemas import ChatRequest, ChatResponse, AgentLog
from app.agent.factory import create_todo_agent
from app.agent.mcp_client import get_mcp_server

router = APIRouter(prefix="/agent", tags=["Agent"])
limiter = Limiter(key_func=get_remote_address)


def sanitize_message(message: str) -> str:
    """Sanitize user message to prevent injection attacks."""
    import re
    
    # Limit length
    max_length = 5000
    message = message[:max_length]
    
    # Remove control characters except newline and tab
    message = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', message)
    
    return message


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")  # Prevent abuse of AI endpoint
async def chat(
    request: Request,
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    groq_client: AsyncOpenAI = Depends(get_groq_client),
):
    """Chat with the AI agent to manage tasks using natural language.
    
    Maintains conversation history per session for stateful interactions.
    """
    # Sanitize user input
    sanitized_message = sanitize_message(chat_request.message)
    
    # Get or create session_id
    session_id = chat_request.session_id or str(uuid.uuid4())
    
    # Retrieve conversation history for this session
    history_query = select(ConversationMessage).where(
        ConversationMessage.session_id == session_id,
        ConversationMessage.user_id == current_user.id
    ).order_by(ConversationMessage.created_at)
    
    result = await db.execute(history_query)
    history = result.scalars().all()
    
    # Build conversation context for the agent
    conversation_history = []
    for msg in history:
        conversation_history.append(f"{msg.role}: {msg.content}")
    
    # Add current user message to context
    full_prompt = sanitized_message
    if conversation_history:
        context_str = "\\n".join(conversation_history)
        full_prompt = f"Previous conversation:\\n{context_str}\\n\\nUser: {sanitized_message}"
    
    # Get the remote MCP server instance
    mcp_server = get_mcp_server()

    # Create agent with MCP tools (no local tools or DB context needed for tools)
    agent = create_todo_agent(groq_client, mcp_server)

    try:
        # Connect to the remote MCP server and run the agent
        async with mcp_server:
            # Run agent - MCP server handles all tool execution remotely
            # max_turns=30 allows for complex multi-task operations
            # parallel_tool_calls=True enables the agent to call multiple independent tools simultaneously
            result = await Runner.run(
                agent,
                full_prompt,
                run_config=RunConfig(
                    tracing_disabled=False,  # Enable tracing to capture logs
                    model_settings=ModelSettings(
                        parallel_tool_calls=True,  # Enable parallel tool execution
                    ),
                ),
                max_turns=30,
            )

        response_text = result.final_output
        
        # Extract real agent execution logs from new_items
        agent_logs: List[AgentLog] = []
        step = 1
        
        # The openai-agents library stores execution details in result.new_items
        if hasattr(result, 'new_items') and result.new_items:
            for item in result.new_items:
                item_type = type(item).__name__
                
                # Log assistant messages/reasoning
                if hasattr(item, 'content') and item.content and item_type == 'AssistantItem':
                    agent_logs.append(AgentLog(
                        step=step,
                        action="reasoning",
                        details=str(item.content)[:150],
                        timestamp=datetime.utcnow().isoformat()
                    ))
                    step += 1
                
                # Log tool calls
                elif hasattr(item, 'name') and hasattr(item, 'arguments'):
                    tool_name = getattr(item, 'name', 'unknown_tool')
                    tool_args = getattr(item, 'arguments', '')
                    agent_logs.append(AgentLog(
                        step=step,
                        action="tool_call",
                        details=f"🔧 {tool_name}({tool_args})",
                        timestamp=datetime.utcnow().isoformat()
                    ))
                    step += 1
                
                # Log tool results/outputs
                elif hasattr(item, 'output'):
                    output = getattr(item, 'output', '')
                    agent_logs.append(AgentLog(
                        step=step,
                        action="tool_result",
                        details=f"✓ {str(output)[:150]}",
                        timestamp=datetime.utcnow().isoformat()
                    ))
                    step += 1
        
        # Save user message to history
        user_message = ConversationMessage(
            session_id=session_id,
            user_id=current_user.id,
            role="user",
            content=sanitized_message  # Save sanitized version
        )
        db.add(user_message)
        
        # Save assistant response to history
        assistant_message = ConversationMessage(
            session_id=session_id,
            user_id=current_user.id,
            role="assistant",
            content=response_text
        )
        db.add(assistant_message)
        
        await db.commit()

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            agent_logs=agent_logs if agent_logs else None
        )

    except Exception as e:
        await db.rollback()
        
        # Determine error type and provide detailed message
        error_type = type(e).__name__
        error_details = str(e)
        
        # Extract more specific error information
        if "database" in error_details.lower() or "sql" in error_details.lower():
            error_message = "Database Error: Unable to complete the operation."
            detailed_error = error_details
        elif "timeout" in error_details.lower():
            error_message = "Timeout Error: The request took too long to complete. Please try again with a simpler query."
            detailed_error = error_details
        elif "connection" in error_details.lower():
            error_message = "Connection Error: Unable to connect to required services."
            detailed_error = error_details
        elif "groq" in error_details.lower() or "api" in error_details.lower():
            error_message = "AI Model Error: The AI service encountered an issue."
            detailed_error = error_details
        else:
            error_message = f"Agent Error: {error_type}"
            detailed_error = error_details
        
        # Log the full error for debugging (server-side only)
        import logging
        logging.error(f"[Agent Error] {error_type}: {error_details}")
        
        # Try to save the error in conversation history for user reference
        try:
            user_message = ConversationMessage(
                session_id=session_id,
                user_id=current_user.id,
                role="user",
                content=sanitized_message
            )
            db.add(user_message)
            
            error_response = ConversationMessage(
                session_id=session_id,
                user_id=current_user.id,
                role="assistant",
                content=f"❌ {error_message}"
            )
            db.add(error_response)
            await db.commit()
        except:
            pass  # If saving fails, just continue to raise the error
        
        # Return user-friendly error without internal details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message,
        )


@router.delete("/chat/session/{session_id}")
async def clear_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear conversation history for a specific session."""
    # Validate session_id format (UUID)
    import re
    if not re.match(r'^[a-f0-9\-]{36}$', session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    # Delete all messages for this session
    query = select(ConversationMessage).where(
        ConversationMessage.session_id == session_id,
        ConversationMessage.user_id == current_user.id
    )
    result = await db.execute(query)
    messages = result.scalars().all()
    
    for msg in messages:
        await db.delete(msg)
    
    await db.commit()
    
    return {"message": f"Cleared {len(messages)} messages from session {session_id}"}
