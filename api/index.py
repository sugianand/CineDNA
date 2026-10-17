"""Expose the existing FastAPI app as a Vercel ASGI function."""

import sys
from pathlib import Path

# Keep the backend's existing `app.*` imports and local Uvicorn command working.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app  # noqa: E402, F401
