from typing import Generic, TypeVar

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Basic repository interface for CRUD operations."""

    def __init__(self, model: type[T]):
        self.model = model

    def get(self, db, id: int) -> T | None:
        return db.get(self.model, id)
