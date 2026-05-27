from jose import JWTError, jwt
from app.core.config import settings
from app.core.exceptions import InvalidWebSocketTokenError


def verify_ws_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as error:
        raise InvalidWebSocketTokenError("Invalid websocket token") from error
