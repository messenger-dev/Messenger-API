def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_user_registration_and_login(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "ivan", "email": "ivan@example.com", "password": "secret123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["user_id"] == 1
    assert "access_token" in data

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "ivan@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["user_id"] == 1
    assert "access_token" in login_data

    profile_response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers(login_data["access_token"]),
    )
    assert profile_response.status_code == 200
    profile_data = profile_response.json()
    assert profile_data["email"] == "ivan@example.com"
    assert profile_data["username"] == "ivan"

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers=auth_headers(login_data["access_token"]),
    )
    assert logout_response.status_code == 204

    revoked_response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers(login_data["access_token"]),
    )
    assert revoked_response.status_code == 401
    assert revoked_response.json()["detail"] == "Token revoked"
