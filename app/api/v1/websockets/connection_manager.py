"""WebSocket connection manager for real-time messaging."""

from __future__ import annotations

import uuid
import asyncio
from typing import Any
from collections import defaultdict

from fastapi import WebSocket
from sqlmodel import Session, select

from app.db.engine import engine
from app.core.redis import get_redis_pubsub
from app.models import ChatParticipant, Message, User


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts."""

    def __init__(self) -> None:
        self.connections: dict[int, set[WebSocket]] = defaultdict(set)
        self.lock = asyncio.Lock()
        self.instance_id = uuid.uuid4().hex
        self.redis = get_redis_pubsub()

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        """Register WebSocket connection."""
        await websocket.accept()
        async with self.lock:
            self.connections[user_id].add(websocket)

    async def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        """Unregister WebSocket connection."""
        async with self.lock:
            if websocket in self.connections.get(user_id, set()):
                self.connections[user_id].remove(websocket)
                if not self.connections[user_id]:
                    del self.connections[user_id]

    async def _safe_send(self, websocket: WebSocket, payload: Any) -> None:
        """Send JSON safely, ignore errors."""
        try:
            await websocket.send_json(payload)
        except Exception:
            pass

    async def broadcast(self, user_ids: list[int], payload: Any) -> None:
        """Broadcast to specific users."""
        tasks = []
        async with self.lock:
            for user_id in set(user_ids):
                for websocket in list(self.connections.get(user_id, [])):
                    tasks.append(self._safe_send(websocket, payload))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_to_chat(self, chat_id: int, payload: Any) -> None:
        """Broadcast to all chat participants."""
        with Session(engine) as session:
            user_ids = session.exec(
                select(ChatParticipant.user_id).where(ChatParticipant.chat_id == chat_id)
            ).all()
        await self.broadcast(user_ids, payload)

    async def send_chat_message(
        self,
        sender_id: int,
        chat_id: int,
        text: str,
        reply_to_id: int | None = None,
    ) -> None:
        """Persist and broadcast chat message."""
        with Session(engine) as session:
            participant = session.get(ChatParticipant, (chat_id, sender_id))
            if not participant:
                return

            sender = session.get(User, sender_id)
            message = Message(
                chat_id=chat_id,
                sender_id=sender_id,
                sender_username=sender.username if sender else "unknown",
                text=text,
                reply_to_id=reply_to_id,
            )
            session.add(message)
            session.commit()
            session.refresh(message)

            payload = {
                "type": "message",
                "id": message.id,
                "chat_id": message.chat_id,
                "sender_id": message.sender_id,
                "sender_username": message.sender_username,
                "text": message.text,
                "reply_to_id": message.reply_to_id,
                "sent_at": message.sent_at.isoformat(),
                "is_read": message.is_read,
            }

        await self.broadcast_to_chat(chat_id, payload)

        if self.redis is not None:
            payload_with_origin = dict(payload)
            payload_with_origin["origin"] = self.instance_id
            await self.redis.publish(f"chat:{chat_id}", payload_with_origin)

    async def send_typing_event(self, user_id: int, chat_id: int, is_typing: bool) -> None:
        """Broadcast typing indicator."""
        with Session(engine) as session:
            participant = session.get(ChatParticipant, (chat_id, user_id))
            if not participant:
                return

            user_ids = session.exec(
                select(ChatParticipant.user_id)
                .where(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id != user_id)
            ).all()

        await self.broadcast(
            user_ids,
            {
                "type": "typing",
                "chat_id": chat_id,
                "user_id": user_id,
                "is_typing": is_typing,
            },
        )

    async def send_read_receipt(
        self, user_id: int, chat_id: int, message_id: int | None = None
    ) -> None:
        """Broadcast read receipt."""
        with Session(engine) as session:
            participant = session.get(ChatParticipant, (chat_id, user_id))
            if not participant:
                return

            user_ids = session.exec(
                select(ChatParticipant.user_id)
                .where(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id != user_id)
            ).all()

        await self.broadcast(
            user_ids,
            {
                "type": "read",
                "chat_id": chat_id,
                "user_id": user_id,
                "message_id": message_id,
            },
        )

    async def handle_redis_message(
        self, channel: str, payload: dict
    ) -> None:
        """Handle Redis Pub/Sub messages."""
        if payload.get("origin") == self.instance_id:
            return

        try:
            _, chat_id_str = channel.split(":", 1)
            chat_id = int(chat_id_str)
        except Exception:
            return

        await self.broadcast_to_chat(chat_id, payload)


ws_manager = ConnectionManager()
