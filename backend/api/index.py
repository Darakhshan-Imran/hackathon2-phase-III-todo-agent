"""
Vercel serverless entry point.

Vercel's @vercel/python runtime looks for an `app` variable in this file.
We add the project root to sys.path so that `from app.xxx import ...`
works the same way it does when running locally with uvicorn.
"""

import sys
import traceback
from pathlib import Path

# Ensure the backend root (parent of this `api/` folder) is on sys.path
# so that `from app.config import ...` etc. resolve correctly.
_backend_root = str(Path(__file__).resolve().parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

try:
    # Re-export the FastAPI instance that Vercel will serve
    from app.main import app  # noqa: E402, F401
except Exception as exc:
    # If the real app fails to import, create a minimal diagnostic app
    # so we can see the actual error instead of a generic 500.
    from fastapi import FastAPI

    app = FastAPI()
    _err = traceback.format_exc()

    @app.get("/{path:path}")
    async def error_handler(path: str = ""):
        return {
            "error": "App failed to start",
            "detail": str(exc),
            "traceback": _err,
            "python_version": sys.version,
        }
