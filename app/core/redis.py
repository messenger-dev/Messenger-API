"""Redis client and Pub/Sub support."""

from __future__ import annotations

import json
import asyncio
from contextlib import suppress
from typing import Any, Callable, Coroutine

import redis
import redis.asyncio as redis_async

from app.core.config import settings
from app.core.logging import logger
from app.interfaces.pubsub import PubSub


class RedisClient:
    """Simple synchronous Redis client wrapper."""

    def __init__(self, url: str) -> None:
        self.client = redis.Redis.from_url(url, decode_responses=True)

    def setex(self, key: str, ttl: int, value: str) -> bool:
        return bool(self.client.setex(key, ttl, value))

    def exists(self, key: str) -> int:
        return self.client.exists(key)

    def get(self, key: str) -> str | None:
        return self.client.get(key)

    def delete(self, *keys: str) -> int:
        return self.client.delete(*keys)

    def close(self) -> None:
        self.client.close()


def get_redis_client() -> RedisClient | None:
    if settings.REDIS_URL:
        return RedisClient(settings.REDIS_URL)
    return None


class RedisPubSub:
    """Redis Pub/Sub helper for broadcasting chat events across workers (async)."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.redis:  redis_async.Redis = redis_async.Redis.from_url(url, decode_responses=True)
        self.pubsub: redis_async.client.PubSub | None = None
        self._task:  asyncio.Task | None = None

    async def publish(self, channel: str, message: Any) -> None:
        payload = json.dumps(message, default=str)
        await self.redis.publish(channel, payload)

    async def start_listening(self, handler: Callable[[str, dict], Coroutine]) -> None:
        if self.pubsub is not None:
            return

        self.pubsub = self.redis.pubsub()
        await self.pubsub.psubscribe("chat:*")

        async def _reader() -> None:
            try:
                async for item in self.pubsub.listen():
                    if not item:
                        continue

                    mtype = item.get("type")
                    if mtype not in ("pmessage", "message"):
                        continue

                    data = item.get("data")
                    if isinstance(data, (bytes, bytearray)):
                        try:
                            data = data.decode()
                        except UnicodeDecodeError as e:
                            logger.warning("Failed decoding pubsub message: %s", e)
                            continue

                    try:
                        payload = json.loads(data)
                    except (TypeError, json.JSONDecodeError) as e:
                        logger.warning("Invalid JSON in pubsub message: %s", e)
                        continue

                    channel = item.get("channel") or item.get("pattern")
                    if isinstance(channel, (bytes, bytearray)):
                        try:
                            channel = channel.decode()
                        except UnicodeDecodeError:
                            channel = None

                    if channel is None:
                        continue

                    await handler(channel, payload)
            except asyncio.CancelledError:
                return

        self._task = asyncio.create_task(_reader())

    async def stop(self) -> None:
        if self.pubsub is not None:
            with suppress(Exception):
                await self.pubsub.close()
            self.pubsub = None

        if self._task is not None:
            self._task.cancel()
            with suppress(Exception):
                await self._task
            self._task = None

        if self.redis is not None:
            with suppress(Exception):
                await self.redis.close()


_redis_pubsub: RedisPubSub | None = None


def get_redis_pubsub() -> PubSub | None:
    """Get or create a RedisPubSub singleton if `REDIS_URL` is configured."""
    global _redis_pubsub
    if _redis_pubsub is None and settings.REDIS_URL:
        _redis_pubsub = RedisPubSub(settings.REDIS_URL)
    return _redis_pubsub

