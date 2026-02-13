from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# Auth Schemas
class UserCreate(BaseModel):
    """Schema for user registration."""

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str
    password: str


class UserResponse(BaseModel):
    """Schema for user response."""

    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# Agent Schemas
class AgentLog(BaseModel):
    """Schema for agent execution log entry."""
    
    step: int
    action: str  # 'tool_call', 'tool_result', 'thinking', 'error'
    details: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    """Schema for agent chat request."""

    message: str = Field(min_length=1, max_length=5000)
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")


class ChatResponse(BaseModel):
    """Schema for agent chat response."""

    response: str
    session_id: str = Field(..., description="Session ID for this conversation")
    tasks_affected: Optional[List[int]] = None
    agent_logs: Optional[List['AgentLog']] = Field(default=None, description="Real agent execution logs")
    error_details: Optional[str] = Field(default=None, description="Detailed error information if agent failed")


class SQLQueryRequest(BaseModel):
    """Schema for direct SQL query execution."""
    
    query: str = Field(min_length=1, description="SQL SELECT query to execute")
    
    
class SQLQueryResponse(BaseModel):
    """Schema for SQL query response."""
    
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    rows_affected: Optional[int] = None


# Todo Schemas (for optional direct CRUD endpoints)
class TodoCreate(BaseModel):
    """Schema for creating a todo."""

    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)


class TodoUpdate(BaseModel):
    """Schema for updating a todo."""

    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[str] = Field(default=None, pattern="^(pending|completed)$")


class TodoResponse(BaseModel):
    """Schema for todo response."""

    id: int
    title: str
    description: Optional[str]
    status: str
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Notification Schemas
class NotificationResponse(BaseModel):
    """Schema for a notification."""

    id: int
    user_id: int
    task_id: int
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Schema for list of notifications with unread count."""

    notifications: List[NotificationResponse]
    unread_count: int
