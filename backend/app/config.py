from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str
    api_key: str  # Groq API key
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Deployment / CORS
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000,https://hackathon2-phase-iii-todo-agent.vercel.app"

    @property
    def cors_origins_list(self) -> List[str]:
        """Split comma-separated CORS_ORIGINS string into a list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
