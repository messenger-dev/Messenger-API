import os
from pathlib import Path
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

os.environ["DATABASE_URL"] = f"sqlite:///{Path(__file__).parent / 'test_messenger.db'}"

import sys
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.db.engine import engine
from app.core import limiter as core_limiter

TEST_DB = Path(__file__).parent / "test_messenger.db"


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    if TEST_DB.exists():
        TEST_DB.unlink()
    SQLModel.metadata.create_all(engine)
    yield
    if TEST_DB.exists():
        TEST_DB.unlink()


@pytest.fixture(autouse=True)
def clean_database():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    core_limiter.limiter.reset()
    yield


@pytest.fixture()
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_headers() -> Callable[[str], dict[str, str]]:
    return lambda token: {"Authorization": f"Bearer {token}"}


@pytest.fixture
def create_user(client) -> Callable[[str, str, str], dict[str, Any]]:
    def _create_user(username: str, email: str, password: str) -> dict[str, Any]:
        response = client.post(
            "/api/v1/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _create_user


@pytest.fixture
def create_chat(client, auth_headers) -> Callable[[str, list[int], str | None, bool], dict[str, Any]]:
    def _create_chat(
        access_token: str,
        participant_ids: list[int],
        name: str | None = None,
        is_group: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "participant_ids": participant_ids,
            "is_group": is_group,
        }
        if name is not None:
            payload["name"] = name

        response = client.post(
            "/api/v1/chats",
            json=payload,
            headers=auth_headers(access_token),
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _create_chat
