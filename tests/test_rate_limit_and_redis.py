import json
from fastapi import status

from app.api.v1.websockets import ws_manager


def test_login_rate_limit(client, create_user):
    create_user("rateuser", "rate@example.com", "secret123")

    for _ in range(10):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "rate@example.com", "password": "secret123"},
        )
        assert response.status_code == status.HTTP_200_OK

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "rate@example.com", "password": "secret123"},
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json()["detail"] == "Rate limit exceeded"


def test_register_rate_limit(client):
    for i in range(5):
        response = client.post(
            "/api/v1/auth/register",
            json={"username": f"u{i}", "email": f"u{i}@example.com", "password": "pwd12345"},
        )
        assert response.status_code == status.HTTP_201_CREATED

    response = client.post(
        "/api/v1/auth/register",
        json={"username": "uX", "email": "uX@example.com", "password": "pwd12345"},
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json()["detail"] == "Rate limit exceeded"


def test_send_message_rate_limit(client, create_user, auth_headers):
    sender = create_user("rateuser", "rate@example.com", "secret123")
    receiver = create_user("friend", "friend@example.com", "secret123")

    chat_response = client.post(
        "/api/v1/chats",
        json={"participant_ids": [receiver["user_id"]], "is_group": False},
        headers=auth_headers(sender["access_token"]),
    )
    assert chat_response.status_code == status.HTTP_201_CREATED
    chat_id = chat_response.json()["id"]

    for _ in range(30):
        response = client.post(
            f"/api/v1/chats/{chat_id}/messages",
            json={"text": "Quick message"},
            headers=auth_headers(sender["access_token"]),
        )
        assert response.status_code == status.HTTP_201_CREATED

    response = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"text": "Extra message"},
        headers=auth_headers(sender["access_token"]),
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json()["detail"] == "Rate limit exceeded"


def test_message_publishes_to_redis(monkeypatch, client, create_user, auth_headers):
    u1 = create_user("ruser1", "r1@example.com", "pwd1")
    u2 = create_user("ruser2", "r2@example.com", "pwd2")

    response = client.post(
        "/api/v1/chats",
        json={"name": "RedisChat", "participant_ids": [u2["user_id"]], "is_group": False},
        headers=auth_headers(u1["access_token"]),
    )
    assert response.status_code == status.HTTP_201_CREATED
    chat_id = response.json()["id"]

    published: dict[str, object] = {}

    class DummyRedis:
        async def publish(self, channel, message):
            published["channel"] = channel
            published["message"] = message

    monkeypatch.setattr(ws_manager, "redis", DummyRedis())

    send_response = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"text": "Hello via HTTP"},
        headers=auth_headers(u1["access_token"]),
    )
    assert send_response.status_code == status.HTTP_201_CREATED

    assert published.get("channel") == f"chat:{chat_id}"
    msg = published.get("message")
    if isinstance(msg, str):
        msg = json.loads(msg)
    assert msg.get("text") == "Hello via HTTP"
