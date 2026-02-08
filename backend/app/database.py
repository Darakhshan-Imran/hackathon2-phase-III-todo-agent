import ssl as _ssl
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from app.config import settings

# For serverless deployments (Vercel), use NullPool to avoid connection
# exhaustion across ephemeral instances.  For long-running servers a
# bounded pool is fine.
_is_serverless = settings.ENVIRONMENT == "production"

_pool_kwargs = (
    {"poolclass": NullPool}
    if _is_serverless
    else {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 1800,
    }
)

# asyncpg does NOT understand libpq query-string parameters like sslmode,
# channel_binding, etc.  Parse the URL, detect SSL intent, then strip all
# parameters that asyncpg cannot handle.
_db_url = settings.DATABASE_URL
_parsed = urlparse(_db_url)
_params = parse_qs(_parsed.query)

_use_ssl = any(
    v[0] in ("require", "verify-full", "verify-ca")
    for v in [_params.get("sslmode", ["disable"])]
)

# Remove libpq-only parameters that asyncpg doesn't understand
_libpq_only = {"sslmode", "channel_binding", "options"}
_clean_params = {k: v[0] for k, v in _params.items() if k not in _libpq_only}
_clean_query = urlencode(_clean_params) if _clean_params else ""
_db_url = urlunparse(_parsed._replace(query=_clean_query))

_connect_args: dict = {
    "server_settings": {"application_name": "todo_agent"},
    "command_timeout": 60,
}
if _use_ssl:
    _connect_args["ssl"] = _ssl.create_default_context()

# Create async engine for Neon PostgreSQL
engine = create_async_engine(
    _db_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args=_connect_args,
    **_pool_kwargs,
)

# Async session factory
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session():
    """Dependency to get async database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
