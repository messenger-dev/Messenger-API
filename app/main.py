"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import router as api_router
from app.api.v1.websockets import ws_manager
from app.core.config import settings
from app.db.init_db import create_db_and_tables
from app.core.limiter import limiter
from app.core.redis import get_redis_pubsub


async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=429, content={"detail": "Rate limit exceeded"}
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    create_db_and_tables()

    redis = get_redis_pubsub()
    if redis is not None:
        await redis.start_listening(ws_manager.handle_redis_message)

    yield

    if redis is not None:
        await redis.stop()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "message": "Messenger API is running. Use /api/v1/docs for OpenAPI UI."
    }
