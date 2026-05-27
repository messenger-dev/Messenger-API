"""Message payload building utilities."""

from __future__ import annotations

from typing import Any

from app.models import Message


def create_message_payload(message: Message) -> dict[str, Any]:
    """Build message payload for transmission."""
    return {
        "type":            "message",
        "id":               message.id,
        "chat_id":          message.chat_id,
        "sender_id":        message.sender_id,
        "sender_username":  message.sender_username,
        "text":             message.text,
        "reply_to_id":      message.reply_to_id,
        "sent_at":          message.sent_at.isoformat(),
        "is_read":          message.is_read,
    }
