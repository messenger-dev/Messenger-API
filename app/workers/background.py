import asyncio


def start_background_task(coro):
    return asyncio.create_task(coro)
