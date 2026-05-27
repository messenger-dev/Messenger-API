"""Error handling middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
from app.core.logging import logger

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handler middleware."""

    async def dispatch(self, request: Request, call_next):
        """Handle requests and catch exceptions."""
        try:
            return await call_next(request)
        except Exception as exc:
            logger.exception("Unhandled exception while processing request: %s %s", request.method, request.url)
            return JSONResponse(
                {"detail": "Internal server error"}, status_code=500
            )
