import pytest
from fastapi import status

from app.api.v1.websockets import ws_manager


def test_direct_chat_lifecycle(client, create_user, auth_headers):
    sender = create_user("ivan", "ivan@example.com", "secret123")
    recipient = create_user("maria", "maria@example.com", "secret456")

    chat_response = client.post(
        "/api/v1/chats",
        json={"participant_ids": [recipient["user_id"]], "is_group": False},
        headers=auth_headers(sender["access_token"]),
    )
    assert chat_response.status_code == status.HTTP_201_CREATED
    chat = chat_response.json()
    assert chat["is_group"] is False
    assert chat["name"] == "ivan & maria"
    chat_id = chat["id"]

    send_response = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"text": "Hello, Maria!"},
        headers=auth_headers(sender["access_token"]),
    )
    assert send_response.status_code == status.HTTP_201_CREATED
    message = send_response.json()
    assert message["chat_id"] == chat_id
    assert message["text"] == "Hello, Maria!"
    assert message["sender_id"] == sender["user_id"]

    preview_response = client.get(
        "/api/v1/chats",
        headers=auth_headers(recipient["access_token"]),
    )
    assert preview_response.status_code == status.HTTP_200_OK
    previews = preview_response.json()
    assert len(previews) == 1
    assert previews[0]["participant_count"] == 2
    assert previews[0]["unread_count"] == 1
    assert previews[0]["last_message"]["text"] == "Hello, Maria!"

    leave_response = client.delete(
        f"/api/v1/chats/{chat_id}",
        headers=auth_headers(sender["access_token"]),
    )
    assert leave_response.status_code == status.HTTP_204_NO_CONTENT

    access_after_leave = client.get(
        f"/api/v1/chats/{chat_id}",
        headers=auth_headers(sender["access_token"]),
    )
    assert access_after_leave.status_code == status.HTTP_403_FORBIDDEN


def test_group_chat_management(client, create_user, auth_headers):
    creator = create_user("alice", "alice@example.com", "pwd12345")
    member = create_user("bob", "bob@example.com", "pwd12345")
    extra = create_user("carla", "carla@example.com", "pwd12345")

    chat_response = client.post(
        "/api/v1/chats",
        json={"name": "Project Team", "participant_ids": [member["user_id"], extra["user_id"]], "is_group": True},
        headers=auth_headers(creator["access_token"]),
    )
    assert chat_response.status_code == status.HTTP_201_CREATED
    chat = chat_response.json()
    chat_id = chat["id"]
    assert chat["is_group"] is True
    assert len(chat["participants"]) == 3

    rename_response = client.patch(
        f"/api/v1/chats/{chat_id}",
        json={"name": "New Project Team"},
        headers=auth_headers(creator["access_token"]),
    )
    assert rename_response.status_code == status.HTTP_200_OK
    assert rename_response.json()["name"] == "New Project Team"

    invalid_rename = client.patch(
        f"/api/v1/chats/{chat_id}",
        json={"name": "Wrong Rename"},
        headers=auth_headers(member["access_token"]),
    )
    assert invalid_rename.status_code == status.HTTP_403_FORBIDDEN

    newcomer = create_user("diana", "diana@example.com", "pwd12345")
    add_response = client.post(
        f"/api/v1/chats/{chat_id}/participants",
        json={"participant_ids": [newcomer["user_id"]]},
        headers=auth_headers(creator["access_token"]),
    )
    assert add_response.status_code == status.HTTP_200_OK
    assert any(p["id"] == newcomer["user_id"] for p in add_response.json()["participants"])

    remove_response = client.delete(
        f"/api/v1/chats/{chat_id}/participants/{member["user_id"]}",
        headers=auth_headers(creator["access_token"]),
    )
    assert remove_response.status_code == status.HTTP_204_NO_CONTENT

    self_remove = client.delete(
        f"/api/v1/chats/{chat_id}/participants/{newcomer["user_id"]}",
        headers=auth_headers(newcomer["access_token"]),
    )
    assert self_remove.status_code == status.HTTP_204_NO_CONTENT

    group_detail = client.get(
        f"/api/v1/chats/{chat_id}",
        headers=auth_headers(creator["access_token"]),
    )
    assert group_detail.status_code == status.HTTP_200_OK
    assert len(group_detail.json()["participants"]) == 2


def test_message_history_before_limit_and_deletion_constraints(client, create_user, auth_headers):
    alice = create_user("alice", "alice@example.com", "pwd12345")
    bob = create_user("bob", "bob@example.com", "pwd12345")

    chat_response = client.post(
        "/api/v1/chats",
        json={"participant_ids": [bob["user_id"]], "is_group": False},
        headers=auth_headers(alice["access_token"]),
    )
    chat_id = chat_response.json()["id"]

    first_message = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"text": "First message"},
        headers=auth_headers(alice["access_token"]),
    ).json()
    second_message = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"text": "Second message"},
        headers=auth_headers(alice["access_token"]),
    ).json()
    third_message = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"text": "Third message"},
        headers=auth_headers(alice["access_token"]),
    ).json()

    history = client.get(
        f"/api/v1/chats/{chat_id}/messages?before={third_message['id']}",
        headers=auth_headers(bob["access_token"]),
    )
    assert history.status_code == status.HTTP_200_OK
    messages = history.json()
    assert [m["id"] for m in messages] == [first_message["id"], second_message["id"]]

    delete_response = client.delete(
        f"/api/v1/messages/{second_message['id']}",
        headers=auth_headers(alice["access_token"]),
    )
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    forbidden_delete = client.delete(
        f"/api/v1/messages/{first_message['id']}",
        headers=auth_headers(bob["access_token"]),
    )
    assert forbidden_delete.status_code == status.HTTP_403_FORBIDDEN
    assert forbidden_delete.json()["detail"] == "Not your message"


def test_mark_chat_read_triggers_read_receipt(client, create_user, auth_headers, monkeypatch):
    alice = create_user("alice", "alice@example.com", "pwd12345")
    bob = create_user("bob", "bob@example.com", "pwd12345")

    chat_response = client.post(
        "/api/v1/chats",
        json={"participant_ids": [bob["user_id"]], "is_group": False},
        headers=auth_headers(alice["access_token"]),
    )
    chat_id = chat_response.json()["id"]

    message = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"text": "Hello Bob"},
        headers=auth_headers(alice["access_token"]),
    ).json()

    captured: dict[str, object] = {}

    async def fake_send_read_receipt(user_id: int, chat_id_arg: int, message_id: int | None = None) -> None:
        captured["user_id"] = user_id
        captured["chat_id"] = chat_id_arg
        captured["message_id"] = message_id

    monkeypatch.setattr(ws_manager, "send_read_receipt", fake_send_read_receipt)

    read_response = client.post(
        f"/api/v1/chats/{chat_id}/read",
        json={"message_id": message["id"]},
        headers=auth_headers(bob["access_token"]),
    )
    assert read_response.status_code == status.HTTP_200_OK
    assert read_response.json() == {"status": "ok"}

    assert captured == {
        "user_id": bob["user_id"],
        "chat_id": chat_id,
        "message_id": message["id"],
    }

    history = client.get(
        f"/api/v1/chats/{chat_id}/messages",
        headers=auth_headers(bob["access_token"]),
    )
    assert history.status_code == status.HTTP_200_OK
    assert history.json()[0]["is_read"] is True
