import os
from pathlib import Path

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
    try:
        from app.core import limiter as core_limiter
        core_limiter.limiter.reset()
    except Exception:
        pass

    yield


@pytest.fixture()
def client():
    with TestClient(app) as client:
        yield client
