from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column, Text


class User(SQLModel, table=True):
    """User model for authentication."""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    email: str = Field(unique=True, max_length=100)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Todo(SQLModel, table=True):
    """Todo model for task management."""

    __tablename__ = "todos"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: str = Field(default="pending")  # pending, completed
    due_date: Optional[datetime] = Field(default=None)
    user_id: int = Field(foreign_key="users.id", index=True)
    created_by: Optional[str] = Field(default=None, max_length=100)  # "task created by 'username'"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notified: bool = Field(default=False)  # True once a 12h reminder has been created
    updated_at: Optional[datetime] = Field(default=None)


class Notification(SQLModel, table=True):
    """In-app reminder notifications for upcoming due dates."""

    __tablename__ = "notifications"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    task_id: int = Field(foreign_key="todos.id", index=True)
    message: str = Field(max_length=500)
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationMessage(SQLModel, table=True):
    """Store conversation history for stateful agent interactions."""

    __tablename__ = "conversation_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, max_length=100)  # UUID for conversation session
    user_id: int = Field(foreign_key="users.id", index=True)
    role: str = Field(max_length=20)  # 'user' or 'assistant'
    content: str = Field(sa_column=Column(Text))  # Message content
    created_at: datetime = Field(default_factory=datetime.utcnow)
