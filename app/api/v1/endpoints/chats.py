"""Chat management endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session, select

from app.schemas import ChatDetail, ChatPreview, CreateChat, UpdateChat, UpdateChatParticipants
from app.di import get_db, get_current_authenticated_user, get_chat_service
from app.models import Chat, ChatParticipant, User
from app.services.chat_service import ChatService
from app.api.v1.websockets import ws_manager

chats_router = APIRouter(prefix="", tags=["Chats"])
def _build_chat_detail(session: Session, chat: Chat) -> ChatDetail:
    """Build ChatDetail response."""
    participants = session.exec(
        select(User).join(ChatParticipant).where(ChatParticipant.chat_id == chat.id)
    ).all()
    return ChatDetail(
        id           = chat.id,
        name         = chat.name,
        is_group     = chat.is_group,
        participants = participants,
        created_at   = chat.created_at,
        created_by   = chat.created_by,
    )


@chats_router.get("/chats", response_model=list[ChatPreview])
def list_chats(
    limit:        int = Query(50),
    offset:       int = Query(0),
    current_user: User = Depends(get_current_authenticated_user),
    service:      ChatService = Depends(get_chat_service),
) -> list[ChatPreview]:
    """Return user's chats with recent messages."""
    return service.list_user_chats(current_user, limit=limit, offset=offset)


@chats_router.post("/chats", response_model=ChatDetail, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload:      CreateChat,
    current_user: User        = Depends(get_current_authenticated_user),
    service:      ChatService = Depends(get_chat_service),
    session:      Session     = Depends(get_db),
) -> ChatDetail:
    """Create a new chat."""
    chat = service.create_chat(payload, current_user)
    return _build_chat_detail(session, chat)


@chats_router.patch("/chats/{chat_id}", response_model=ChatDetail)
def rename_chat(
    chat_id:      int,
    payload:      UpdateChat,
    current_user: User        = Depends(get_current_authenticated_user),
    service:      ChatService = Depends(get_chat_service),
    session:      Session     = Depends(get_db),
) -> ChatDetail:
    """Rename group chat."""
    chat = service.get_chat_or_404(chat_id)
    service.assert_user_in_chat(chat_id, current_user.id)

    chat = service.rename_chat(chat, payload.name, current_user)
    return _build_chat_detail(session, chat)
    

@chats_router.post("/chats/{chat_id}/participants", response_model=ChatDetail)
def add_participants(
    chat_id:      int,
    payload:      UpdateChatParticipants,
    current_user: User        = Depends(get_current_authenticated_user),
    service:      ChatService = Depends(get_chat_service),
    session:      Session     = Depends(get_db),
) -> ChatDetail:
    """Add participants to group chat."""
    chat = service.get_chat_or_404(chat_id)
    service.assert_user_in_chat(chat_id, current_user.id)

    chat = service.add_participants(chat, payload.participant_ids, current_user)
    return _build_chat_detail(session, chat)


@chats_router.delete("/chats/{chat_id}/participants/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_participant(
    chat_id:        int,
    participant_id: int,
    current_user     = Depends(get_current_authenticated_user),
    service: ChatService = Depends(get_chat_service),
    session: Session = Depends(get_db),
) -> None:
    chat = service.get_chat_or_404(chat_id)
    service.assert_user_in_chat(chat_id, current_user.id)
    service.remove_participant(chat, participant_id, current_user)


@chats_router.get("/chats/{chat_id}", response_model=ChatDetail)
def get_chat_detail(
    chat_id: int,
    current_user     = Depends(get_current_authenticated_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatDetail:
    """Return chat details and participants."""
    service.assert_user_in_chat(chat_id, current_user.id)
    return service.get_chat_detail(chat_id)


@chats_router.delete("/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: int,
    current_user     = Depends(get_current_authenticated_user),
    service: ChatService = Depends(get_chat_service),
) -> None:
    """Leave or delete a chat depending on permissions."""
    service.delete_or_leave_chat(chat_id, current_user.id)


@chats_router.post("/chats/{chat_id}/read")
async def mark_chat_read(
    chat_id:      int,
    payload:      dict | None = None,
    current_user: User        = Depends(get_current_authenticated_user),
    service:      ChatService = Depends(get_chat_service),
) -> dict[str, str]:
    """Mark messages as read and notify other chat participants."""
    service.assert_user_in_chat(chat_id, current_user.id)

    message_id = payload.get("message_id") if payload else None
    service.mark_chat_read(chat_id, current_user.id, message_id)

    await ws_manager.send_read_receipt(current_user.id, chat_id, message_id)
    return {"status": "ok"}
