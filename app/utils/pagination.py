from typing import Iterable


def paginate(items: Iterable, limit: int, offset: int):
    return list(items)[offset : offset + limit]
