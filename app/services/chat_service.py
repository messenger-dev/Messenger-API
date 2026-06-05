"""Chat management business logic."""

from fastapi import HTTPException, status
from sqlmodel import Session, select, delete
from sqlalchemy import desc

from app.models import Chat, ChatParticipant, User, Message
from app.schemas import CreateChat, ChatPreview, ChatDetail


class ChatService:
    """Service for chat operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_chat_or_404(self, chat_id: int) -> Chat:
        """Get chat or raise 404."""
        chat = self.session.get(Chat, chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
            )
        return chat

    def assert_user_in_chat(self, chat_id: int, user_id: int) -> ChatParticipant:
        """Verify user is chat member."""
        participant = self.session.get(ChatParticipant, (chat_id, user_id))
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not in this chat",
            )
        return participant

    def create_chat(self, payload: CreateChat, current_user: User) -> Chat:
        """Create chat with participants."""
        participant_ids = list(dict.fromkeys(payload.participant_ids + [current_user.id]))

        if payload.is_group:
            if len(participant_ids) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Group chat requires at least 2 participants",
                )
        else:
            if len(participant_ids) != 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Direct chat must have exactly 2 participants",
                )

        users = self.session.exec(
            select(User).where(User.id.in_(participant_ids))
        ).all()

        if len(users) != len(participant_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some users not found",
            )

        name = payload.name.strip() if payload.name else None
        if not name:
            if payload.is_group:
                name = "Group chat"
            else:
                other = next(u for u in users if u.id != current_user.id)
                name = f"{current_user.username} & {other.username}"

        chat = Chat(name=name, is_group=payload.is_group, created_by=current_user.id)
        self.session.add(chat)
        self.session.commit()
        self.session.refresh(chat)

        for user_id in participant_ids:
            self.session.add(ChatParticipant(chat_id=chat.id, user_id=user_id))

        self.session.commit()
        return chat

    def rename_chat(self, chat: Chat, name: str, current_user: User) -> Chat:
        """Rename group chat."""
        if not chat.is_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot rename direct chats",
            )
        if chat.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only creator can rename",
            )

        chat.name = name.strip()
        self.session.add(chat)
        self.session.commit()
        self.session.refresh(chat)
        return chat

    def add_participants(
        self, chat: Chat, participant_ids: list[int], current_user: User
    ) -> Chat:
        """Add participants to group chat."""
        if not chat.is_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add to direct chats",
            )
        
        if not self.session.get(ChatParticipant, (chat.id, current_user.id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not in this chat",
            )

        existing_ids = self.session.exec(
            select(ChatParticipant.user_id).where(ChatParticipant.chat_id == chat.id)
        ).all()

        new_ids = [
            uid
            for uid in dict.fromkeys(participant_ids)
            if uid not in existing_ids
        ]

        if not new_ids:
            return chat

        users = self.session.exec(select(User).where(User.id.in_(new_ids))).all()
        if len(users) != len(new_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some users not found",
            )

        for user_id in new_ids:
            self.session.add(ChatParticipant(chat_id=chat.id, user_id=user_id))

        self.session.commit()
        return chat

    def remove_participant(
        self, chat: Chat, participant_id: int, current_user: User
    ) -> None:
        """Remove participant from group chat."""
        if not chat.is_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove from direct chats",
            )
        
        if (
            chat.created_by != current_user.id
            and participant_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only creator can remove others",
            )

        participant = self.session.get(ChatParticipant, (chat.id, participant_id))
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Participant not found",
            )

        self.session.delete(participant)
        self.session.commit()

        remaining = self.session.exec(
            select(ChatParticipant).where(ChatParticipant.chat_id == chat.id)
        ).first()
        
        if not remaining:
            self.session.delete(chat)
            self.session.commit()

    def list_user_chats(self, user: User, limit: int = 50, offset: int = 0) -> list[ChatPreview]:
        """Return chat previews for user."""
        chat_ids = self.session.exec(
            select(ChatParticipant.chat_id)
            .where(ChatParticipant.user_id == user.id)
            .offset(offset)
            .limit(limit)
        ).all()

        if not chat_ids:
            return []

        chats = self.session.exec(select(Chat).where(Chat.id.in_(chat_ids))).all()
        previews: list[ChatPreview] = []

        for chat in chats:
            last_message = self.session.exec(
                select(Message)
                .where(Message.chat_id == chat.id)
                .order_by(desc(Message.sent_at))
                .limit(1)
            ).first()

            unread_count = len(
                self.session.exec(
                    select(Message).where(
                        Message.chat_id == chat.id,
                        Message.is_read == False,
                        Message.sender_id != user.id,
                    )
                ).all()
            )

            participant_count = self.session.exec(
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

    def get_chat_detail(self, chat_id: int) -> ChatDetail:
        """Return chat detail with participants."""
        chat = self.get_chat_or_404(chat_id)
        participants = self.session.exec(
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

    def mark_chat_read(self, chat_id: int, user_id: int, message_id: int | None = None) -> None:
        """Mark messages as read for a chat for messages up to message_id (or all)."""
        query = select(Message).where(Message.chat_id == chat_id, Message.sender_id != user_id)
        if message_id is not None:
            query = query.where(Message.id <= message_id)

        messages = self.session.exec(query).all()
        for message in messages:
            message.is_read = True

        self.session.commit()

    def delete_or_leave_chat(self, chat_id: int, user_id: int) -> None:
        """Leave chat or delete it if user is creator or last participant."""
        chat = self.get_chat_or_404(chat_id)
        participant = self.assert_user_in_chat(chat_id, user_id)

        if chat.is_group:
            if chat.created_by != user_id:
                self.session.delete(participant)
                self.session.commit()
                return

            self.session.exec(delete(Message).where(Message.chat_id == chat_id))
            self.session.exec(delete(ChatParticipant).where(ChatParticipant.chat_id == chat_id))
            self.session.delete(chat)
            self.session.commit()
            return

        self.session.delete(participant)
        self.session.commit()

        remaining = self.session.exec(select(ChatParticipant).where(ChatParticipant.chat_id == chat_id)).first()

        if not remaining:
            self.session.exec(delete(Message).where(Message.chat_id == chat_id))
            self.session.delete(chat)
            self.session.commit()
