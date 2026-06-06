import pytest
from fastapi import status

from app.core.config import settings
from app.api.v1.endpoints import email as email_module


def test_search_users_returns_matching_user(client, create_user, auth_headers):
    create_user("alice", "alice@example.com", "pwd12345")
    bob = create_user("bob", "bob@example.com", "pwd12345")

    response = client.get(
        "/api/v1/users?q=ali",
        headers=auth_headers(bob["access_token"]),
    )
    assert response.status_code == status.HTTP_200_OK
    users = response.json()
    assert len(users) == 1
    assert users[0]["username"] == "alice"


def test_search_users_requires_minimum_query_length(client, create_user, auth_headers):
    user = create_user("alice", "alice@example.com", "pwd12345")

    response = client.get(
        "/api/v1/users?q=a",
        headers=auth_headers(user["access_token"]),
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["type"] == "string_too_short"


def test_search_users_requires_authentication(client):
    response = client.get("/api/v1/users?q=alice")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_email_send_queued_when_service_configured(client, create_user, auth_headers, monkeypatch):
    sender = create_user("alice", "alice@example.com", "pwd12345")

    sent_messages: list[object] = []

    def fake_send_email(message):
        sent_messages.append(message)

    monkeypatch.setattr(email_module, "send_email", fake_send_email)
    monkeypatch.setattr(settings, "EMAIL_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "EMAIL_FROM", "no-reply@example.com")

    response = client.post(
        "/api/v1/email/send",
        json={
            "recipient": "recipient@example.com",
            "subject": "Welcome",
            "body": "Hello from Messenger",
        },
        headers=auth_headers(sender["access_token"]),
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {"status": "queued"}
    assert len(sent_messages) == 1
    assert sent_messages[0]["To"] == "recipient@example.com"
    assert sent_messages[0]["From"] == "no-reply@example.com"
    assert sent_messages[0]["Subject"] == "Welcome"


def test_email_service_not_configured_returns_503(client, create_user, auth_headers, monkeypatch):
    sender = create_user("alice", "alice@example.com", "pwd12345")

    monkeypatch.setattr(settings, "EMAIL_SMTP_HOST", None)
    monkeypatch.setattr(settings, "EMAIL_FROM", None)

    response = client.post(
        "/api/v1/email/send",
        json={
            "recipient": "recipient@example.com",
            "subject": "Broken service",
            "body": "This will fail",
        },
        headers=auth_headers(sender["access_token"]),
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["detail"] == "Email service is not configured"
