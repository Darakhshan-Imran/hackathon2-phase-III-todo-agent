from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str
    api_key: str  # Groq API key
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour - reduced from 15 hours for security

    # Deployment / CORS
    ENVIRONMENT: str = "production"  # "development" or "production"
    ALLOWED_ORIGINS: List[str] = []  # e.g. ["https://myapp.vercel.app"]

    # MCP Remote Server Configuration (Production)
    MCP_SERVER_URL: str  # Remote MCP server endpoint (no default — must be set)
    MCP_API_KEY: Optional[str] = None  # API key for authenticating with the MCP server
    MCP_SERVER_TIMEOUT: int = 30  # Timeout in seconds for MCP server requests
    MCP_CACHE_TOOLS: bool = True  # Cache the tools list from MCP server
    MCP_MAX_RETRIES: int = 3  # Max retry attempts for MCP server connections

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
