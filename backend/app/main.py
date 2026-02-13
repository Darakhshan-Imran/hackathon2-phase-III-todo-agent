from contextlib import asynccontextmanager
import logging
import re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.database import init_db
from app.config import settings as app_settings
from app.scheduler import start_scheduler, stop_scheduler
from app.routers.auth_router import router as auth_router
from app.routers.agent_router import router as agent_router
from app.routers.sql_router import router as sql_router
from app.routers.notification_router import router as notification_router

logger = logging.getLogger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)


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
            logger.warning(f"Potential injection attempt detected: {pattern}")

    return text


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and scheduler on startup, clean up on shutdown."""
    logger.info(f"CORS origins configured: {_allowed_origins}")
    await init_db()
    start_scheduler()
    yield
    stop_scheduler()


# Hide API docs in production to prevent information disclosure
_docs_url = "/docs" if app_settings.ENVIRONMENT == "development" else None
_redoc_url = "/redoc" if app_settings.ENVIRONMENT == "development" else None

# CORS origins — directly from config
_allowed_origins = app_settings.cors_origins_list

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

# CORS must be the ONLY middleware that touches preflight requests.
# Do NOT use BaseHTTPMiddleware (it wraps responses and can strip CORS headers).
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers — skip CORS preflight so we don't interfere."""
    response: Response = await call_next(request)
    if request.method != "OPTIONS":
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Include routers
app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(sql_router)
app.include_router(notification_router)


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Todo Agent API is running"}


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "cors_origins": _allowed_origins,
        "environment": app_settings.ENVIRONMENT,
    }
