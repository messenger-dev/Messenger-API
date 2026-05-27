import json

from app.core.config import settings
from app.api.v1.websockets import ws_manager


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_user(client, username: str, email: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert response.status_code == 201
    return response.json()


def test_login_rate_limit(client):
    # create a user
    create_user(client, "rateuser", "rate@example.com", "secret123")

    # perform allowed number of logins
    for i in range(10):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "rate@example.com", "password": "secret123"},
        )
        assert resp.status_code == 200

    # the next request should be rate-limited
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "rate@example.com", "password": "secret123"},
    )
    assert resp.status_code == 429


def test_register_rate_limit(client):
    # register up to limit with distinct emails
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": f"u{i}", "email": f"u{i}@example.com", "password": "pwd12345"},
        )
        assert resp.status_code == 201

    # next registration should be rate-limited
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "uX", "email": "uX@example.com", "password": "pwd12345"},
    )
    assert resp.status_code == 429


def test_message_publishes_to_redis(monkeypatch, client):
    # create two users and a chat
    u1 = create_user(client, "ruser1", "r1@example.com", "pwd1")
    u2 = create_user(client, "ruser2", "r2@example.com", "pwd2")

    resp = client.post(
        "/api/v1/chats",
        json={"name": "RedisChat", "participant_ids": [u2["user_id"]], "is_group": False},
        headers=auth_headers(u1["access_token"]),
    )
    assert resp.status_code == 201
    chat = resp.json()
    chat_id = chat["id"]

    # Monkeypatch ws_manager.redis to capture publish calls
    published = {}

    class DummyRedis:
        async def publish(self, channel, message):
            published["channel"] = channel
            # message might be dict or json-string
            published["message"] = message

    monkeypatch.setattr(ws_manager, "redis", DummyRedis())

    send_resp = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"text": "Hello via HTTP"},
        headers=auth_headers(u1["access_token"]),
    )
    assert send_resp.status_code == 201

    # Ensure redis.publish was called
    assert published.get("channel") == f"chat:{chat_id}"
    msg = published.get("message")
    # if message was serialized, convert
    if isinstance(msg, str):
        msg = json.loads(msg)
    assert msg.get("text") == "Hello via HTTP"
