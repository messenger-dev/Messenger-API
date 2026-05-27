from fastapi import APIRouter

from app.api.v1.endpoints.auth import auth_router
from app.api.v1.endpoints.users import users_router
from app.api.v1.endpoints.chats import chats_router
from app.api.v1.endpoints.email import email_router
from app.api.v1.endpoints.messages import messages_router
from app.api.v1.websockets.chat_ws import websocket_router
from app.api.v1.endpoints.attachments import attachments_router


router = APIRouter()
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(chats_router)
router.include_router(email_router)
router.include_router(messages_router)
router.include_router(websocket_router)
router.include_router(attachments_router)