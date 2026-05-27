"""Protocol definitions for Pub/Sub abstractions."""

from __future__ import annotations

from typing import Any, Callable, Coroutine, Protocol, runtime_checkable


@runtime_checkable
class PubSub(Protocol):
    async def publish(self, channel: str, message: Any) -> None: ...

    async def start_listening(self, handler: Callable[[str, dict], Coroutine]) -> None: ...

    async def stop(self) -> None: ...
