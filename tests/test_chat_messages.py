def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_user(client, username: str, email: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert response.status_code == 201
    return response.json()


def test_chat_creation_and_message_flow(client):
    user1 = create_user(client, "ivan", "ivan@example.com", "secret123")
    user2 = create_user(client, "maria", "maria@example.com", "secret456")

    response = client.post(
        "/api/v1/chats",
        json={"name": "Direct chat", "participant_ids": [user2["user_id"]], "is_group": False},
        headers=auth_headers(user1["access_token"]),
    )
    assert response.status_code == 201
    chat_data = response.json()
    chat_id = chat_data["id"]
    assert chat_data["name"] == "Direct chat"

    send_response = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"text": "Hello, Maria!"},
        headers=auth_headers(user1["access_token"]),
    )
    assert send_response.status_code == 201
    message_data = send_response.json()
    assert message_data["chat_id"] == chat_id
    assert message_data["text"] == "Hello, Maria!"

    history_response = client.get(
        f"/api/v1/chats/{chat_id}/messages",
        headers=auth_headers(user2["access_token"]),
    )
    assert history_response.status_code == 200
    messages = history_response.json()
    assert len(messages) == 1
    assert messages[0]["text"] == "Hello, Maria!"
