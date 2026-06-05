"""WebSocket endpoint for real-time chat."""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, Depends

from app.services.token_service import TokenService
from app.core.token import get_token_service
from app.api.v1.websockets import ws_manager

websocket_router = APIRouter(prefix="", tags=["WebSocket"])


@websocket_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    token_service: TokenService = Depends(get_token_service),
) -> None:
    """WebSocket endpoint for real-time messaging."""
    try:
        payload = token_service.verify_token(token)
        if token_service.is_token_revoked(token):
            await websocket.close(code=1008)
            return
    except ValueError:
        await websocket.close(code=1008)
        return

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id.isdigit():
        await websocket.close(code=1008)
        return

    user_id = int(user_id)
    await ws_manager.connect(user_id, websocket)
    await websocket.send_json({"type": "connected", "user_id": user_id})

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except ValueError:
                continue

            if not isinstance(data, dict):
                continue

            event_type = data.get("type")

            if event_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif event_type == "message":
                chat_id     = data.get("chat_id")
                text        = data.get("text")
                reply_to_id = data.get("reply_to_id")

                if (
                    isinstance(chat_id, int)
                    and isinstance(text, str)
                    and text.strip()
                ):
                    await ws_manager.send_chat_message(
                        user_id, chat_id, text.strip(), reply_to_id
                    )

            elif event_type == "typing":
                chat_id   = data.get("chat_id")
                is_typing = data.get("is_typing", False)

                if isinstance(chat_id, int):
                    await ws_manager.send_typing_event(user_id, chat_id, bool(is_typing))

            elif event_type == "read":
                chat_id    = data.get("chat_id")
                message_id = data.get("message_id")

                if isinstance(chat_id, int):
                    await ws_manager.send_read_receipt(user_id, chat_id, message_id)

    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id, websocket)
