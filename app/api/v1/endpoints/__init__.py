from .auth import auth_router
from .attachments import attachments_router
from .users import users_router
from .chats import chats_router
from .messages import messages_router
from .email import email_router

__all__ = [
    "auth_router",
    "attachments_router",
    "users_router",
    "chats_router",
    "messages_router",
    "email_router",
]
