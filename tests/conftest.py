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

    # Reset rate limiter storage between tests to avoid cross-test leakage
    try:
        from app.core import limiter as core_limiter

        if hasattr(core_limiter.limiter, "_storage") and hasattr(core_limiter.limiter._storage, "reset"):
            core_limiter.limiter._storage.reset()
    except Exception:
        pass

    yield


@pytest.fixture()
def client():
    try:
        from app.core.limiter import limiter as _global_limiter

        if hasattr(_global_limiter, "_storage") and hasattr(_global_limiter._storage, "reset"):
            _global_limiter._storage.reset()
    except Exception:
        pass

    with TestClient(app) as client:
        yield client
