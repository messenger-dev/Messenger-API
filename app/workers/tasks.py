from app.core.logging import logger
import asyncio


async def send_push(notification: dict) -> None:
    """Send push notifications. Currently best-effort: log and return."""
    try:
        logger.info("send_push: %s", notification)
        await asyncio.sleep(0)
    except Exception:
        logger.exception("Failed to send push notification")


async def generate_thumbnail(attachment_path: str) -> str:
    """Generate a thumbnail for an attachment. Returns thumbnail path or empty string."""
    try:
        logger.info("generate_thumbnail for %s", attachment_path)
        await asyncio.sleep(0)
        return "" 
    except Exception:
        logger.exception("Failed to generate thumbnail for %s", attachment_path)
        return ""
