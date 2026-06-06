import pytest
from fastapi import status


def test_user_registration_login_logout_and_profile(client, create_user, auth_headers):
    user = create_user("ivan", "ivan@example.com", "secret123")
    assert user["token_type"] == "bearer"
    assert user["user_id"] == 1
    assert "access_token" in user

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "ivan@example.com", "password": "secret123"},
    )
    assert login_response.status_code == status.HTTP_200_OK
    login_data = login_response.json()
    assert login_data["user_id"] == user["user_id"]
    assert "access_token" in login_data

    profile_response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers(login_data["access_token"]),
    )
    assert profile_response.status_code == status.HTTP_200_OK
    profile_data = profile_response.json()
    assert profile_data["email"] == "ivan@example.com"
    assert profile_data["username"] == "ivan"

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers=auth_headers(login_data["access_token"]),
    )
    assert logout_response.status_code == status.HTTP_204_NO_CONTENT

    revoked_response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers(login_data["access_token"]),
    )
    assert revoked_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert revoked_response.json()["detail"] == "Token revoked"


def test_protected_route_rejects_invalid_token(client, auth_headers):
    response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers("invalid.token.value"),
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Token revoked"


def test_register_fails_for_duplicate_username_or_email(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "ivan", "email": "ivan@example.com", "password": "secret123"},
    )
    assert response.status_code == status.HTTP_201_CREATED

    duplicate_username = client.post(
        "/api/v1/auth/register",
        json={"username": "ivan", "email": "ivan2@example.com", "password": "secret123"},
    )
    assert duplicate_username.status_code == status.HTTP_400_BAD_REQUEST
    assert duplicate_username.json()["detail"] == "Email or username already exists"

    duplicate_email = client.post(
        "/api/v1/auth/register",
        json={"username": "ivan2", "email": "ivan@example.com", "password": "secret123"},
    )
    assert duplicate_email.status_code == status.HTTP_400_BAD_REQUEST
    assert duplicate_email.json()["detail"] == "Email or username already exists"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "ivan@example.com", "password": "wrong"},
        {"email": "missing@example.com", "password": "secret123"},
    ],
)
def test_login_fails_with_invalid_credentials(client, payload):
    client.post(
        "/api/v1/auth/register",
        json={"username": "ivan", "email": "ivan@example.com", "password": "secret123"},
    )

    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid credentials"


def test_protected_route_rejects_invalid_token(client, auth_headers):
    response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers("invalid.token.value"),
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Token revoked"
