from contextlib import asynccontextmanager
import re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import init_db
from app.agent.mcp_client import cleanup_mcp_server
from app.config import settings as app_settings
from app.routers.auth_router import router as auth_router
from app.routers.agent_router import router as agent_router
from app.routers.sql_router import router as sql_router


# Rate limiting
limiter = Limiter(key_func=get_remote_address)


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self';"
        return response


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Sanitize user input to prevent injection attacks."""
    if not text:
        return text
    
    # Limit length
    text = text[:max_length]
    
    # Remove control characters except newline and tab
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    
    # Basic prompt injection prevention patterns
    dangerous_patterns = [
        r'ignore\s+previous\s+instructions',
        r'ignore\s+all\s+previous',
        r'disregard\s+previous',
        r'forget\s+everything',
        r'system\s*:',
        r'<\s*script',
    ]
    
    # Don't block but log potential injection attempts
    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            import logging
            logging.warning(f"Potential injection attempt detected: {pattern}")
    
    return text


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup, cleanup MCP on shutdown."""
    await init_db()
    yield
    await cleanup_mcp_server()


# Hide API docs in production to prevent information disclosure
_docs_url = "/docs" if app_settings.ENVIRONMENT == "development" else None
_redoc_url = "/redoc" if app_settings.ENVIRONMENT == "development" else None

app = FastAPI(
    title="AI TODO Agent API",
    description="AI-Powered TODO Management with Natural Language",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware — origins driven by env var, no wildcard with credentials
_default_origins = (
    ["http://localhost:3000", "http://127.0.0.1:3000"]
    if app_settings.ENVIRONMENT == "development"
    else []
)
_allowed_origins = app_settings.cors_origins or _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include routers
app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(sql_router)


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Todo Agent API is running"}


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
