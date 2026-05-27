"""Chat management business logic."""

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Chat, ChatParticipant, User
from app.schemas import CreateChat


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
