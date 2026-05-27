"""Chat management endpoints."""

from sqlalchemy import desc
from sqlmodel import Session, select

from fastapi import APIRouter, Depends, Query, status

from app.di import get_db, get_current_authenticated_user
from app.schemas import ChatDetail, ChatPreview, CreateChat, UpdateChat, UpdateChatParticipants
from app.models import Chat, ChatParticipant, Message, User
from app.services.chat_service import ChatService
from app.api.v1.websockets import ws_manager

chats_router = APIRouter(prefix="", tags=["Chats"])


def get_chat_service(session: Session = Depends(get_db)) -> ChatService:
    """Provide ChatService dependency."""
    return ChatService(session)


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
    limit: int = Query(50),
    offset: int = Query(0),
    current_user: User = Depends(get_current_authenticated_user),
    session: Session = Depends(get_db),
) -> list[ChatPreview]:
    """Return user's chats with recent messages."""
    chat_ids = session.exec(
        select(ChatParticipant.chat_id)
        .where(ChatParticipant.user_id == current_user.id)
        .offset(offset)
        .limit(limit)
    ).all()

    if not chat_ids:
        return []

    chats = session.exec(select(Chat).where(Chat.id.in_(chat_ids))).all()
    previews: list[ChatPreview] = []

    for chat in chats:
        last_message = session.exec(
            select(Message)
            .where(Message.chat_id == chat.id)
            .order_by(desc(Message.sent_at))
            .limit(1)
        ).first()

        unread_count = len(
            session.exec(
                select(Message).where(
                    Message.chat_id == chat.id,
                    Message.is_read == False,
                    Message.sender_id != current_user.id,
                )
            ).all()
        )

        participant_count = session.exec(
            select(ChatParticipant).where(ChatParticipant.chat_id == chat.id)
        ).all()

        previews.append(
            ChatPreview(
                id                = chat.id,
                name              = chat.name,
                is_group          = chat.is_group,
                participant_count = len(participant_count),
                last_message=(
                    None
                    if not last_message
                    else {
                        "text": last_message.text,
                        "sent_at": last_message.sent_at,
                        "sender_username": last_message.sender_username,
                    }
                ),
                unread_count=unread_count,
                updated_at=last_message.sent_at if last_message else chat.created_at,
            )
        )

    return previews


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
    session: Session = Depends(get_db),
) -> None:
    chat = get_chat_or_404(session, chat_id)
    assert_user_in_chat(session, chat_id, current_user.id)
    remove_chat_participant(session, chat, participant_id, current_user)


@chats_router.get("/chats/{chat_id}", response_model=ChatDetail)
def get_chat_detail(
    chat_id: int,
    current_user     = Depends(get_current_authenticated_user),
    session: Session = Depends(get_db),
) -> ChatDetail:
    """Return chat details and participants."""
    chat = get_chat_or_404(session, chat_id)
    assert_user_in_chat(session, chat_id, current_user.id)

    participants = session.exec(
        select(User).join(ChatParticipant).where(ChatParticipant.chat_id == chat_id)
    ).all()

    return ChatDetail(
        id           = chat.id,
        name         = chat.name,
        is_group     = chat.is_group,
        participants = participants,
        created_at   = chat.created_at,
        created_by   = chat.created_by,
    )


@chats_router.delete("/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: int,
    current_user     = Depends(get_current_authenticated_user),
    session: Session = Depends(get_db),
) -> None:
    """Leave or delete a chat depending on permissions."""
    chat = get_chat_or_404(session, chat_id)
    participant = assert_user_in_chat(session, chat_id, current_user.id)

    if chat.is_group:
        if chat.created_by != current_user.id:
            session.delete(participant)
            session.commit()
            return

        session.exec(delete(Message).where(Message.chat_id == chat_id))
        session.exec(delete(ChatParticipant).where(ChatParticipant.chat_id == chat_id))
        session.delete(chat)
        session.commit()
        return

    session.delete(participant)
    session.commit()

    remaining = session.exec(select(ChatParticipant).where(ChatParticipant.chat_id == chat_id)).first()

    if not remaining:
        session.exec(delete(Message).where(Message.chat_id == chat_id))
        session.delete(chat)
        session.commit()


@chats_router.post("/chats/{chat_id}/read")
async def mark_chat_read(
    chat_id:      int,
    payload:      dict | None = None,
    current_user: User        = Depends(get_current_authenticated_user),
    session:      Session     = Depends(get_db),
) -> dict[str, str]:
    """Mark messages as read and notify other chat participants."""
    chat = get_chat_or_404(session, chat_id)
    assert_user_in_chat(session, chat_id, current_user.id)

    query = select(Message).where(Message.chat_id == chat_id, Message.sender_id != current_user.id)
    
    if payload and payload.get("message_id") is not None:
        query = query.where(Message.id <= payload["message_id"])

    messages = session.exec(query).all()

    for message in messages:
        message.is_read = True

    session.commit()

    await ws_manager.send_read_receipt(chat_id, current_user.id, payload.get("message_id") if payload else None)
    return {"status": "ok"}
