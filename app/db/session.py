from sqlmodel import Session
from app.db.engine import engine


def get_session():
    """Yield a database session for request lifecycle."""
    with Session(engine) as session:
        yield session
