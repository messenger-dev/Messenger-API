"""Message endpoints for history, sending, and deletion."""

from sqlalchemy import desc
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request

from app.di import get_db, get_current_authenticated_user, get_chat_service
from app.services.message_relay import create_message_payload
from app.schemas import MessageResponse, SendMessage
from app.services.chat_service import ChatService
from app.api.v1.websockets import ws_manager
from app.core.limiter import limiter
from app.models import Message, User


messages_router = APIRouter(prefix="", tags=["Messages"])

@messages_router.get("/chats/{chat_id}/messages", response_model=list[MessageResponse])
def get_chat_messages(
    chat_id:      int,
    limit:        int = Query(50, le=200),
    before:       int | None = Query(None),
    current_user: User        = Depends(get_current_authenticated_user),
    service:      ChatService = Depends(get_chat_service),
    session:      Session     = Depends(get_db),
) -> list[Message]:
    """Return chat message history."""
    service.assert_user_in_chat(chat_id, current_user.id)

    query = select(Message).where(Message.chat_id == chat_id)
    if before is not None:
        query = query.where(Message.id < before)

    messages = session.exec(
        query.order_by(desc(Message.sent_at)).limit(limit)
    ).all()
    return list(reversed(messages))


@messages_router.post(
    "/chats/{chat_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def send_message_http(
    request:      Request,
    chat_id:      int,
    payload:      SendMessage,
    current_user: User        = Depends(get_current_authenticated_user),
    service:      ChatService = Depends(get_chat_service),
    session:      Session     = Depends(get_db),
) -> Message:
    """Send message to chat."""
    service.assert_user_in_chat(chat_id, current_user.id)

    message = Message(
        chat_id         = chat_id,
        sender_id       = current_user.id,
        sender_username = current_user.username,
        text            = payload.text,
        reply_to_id     = payload.reply_to_id,
    )
    session.add(message)
    session.commit()
    session.refresh(message)

    msg_payload = create_message_payload(message)
    await ws_manager.broadcast_to_chat(chat_id, msg_payload)

    if ws_manager.redis is not None:
        await ws_manager.redis.publish(f"chat:{chat_id}", dict(msg_payload))

    return message


@messages_router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id:   int,
    current_user: User        = Depends(get_current_authenticated_user),
    session:      Session     = Depends(get_db),
) -> None:
    """Delete message (only sender can delete)."""
    message = session.get(Message, message_id)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        )

    if message.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not your message"
        )

    session.delete(message)
    session.commit()
