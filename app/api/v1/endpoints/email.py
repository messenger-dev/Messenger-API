"""Email notification endpoints."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.di import get_current_authenticated_user
from app.core.exceptions import EmailServiceError
from app.core.email import build_email_message, send_email
from app.schemas import EmailSendRequest

email_router = APIRouter(prefix="", tags=["Email"])


@email_router.post("/email/send", status_code=status.HTTP_202_ACCEPTED)
def send_system_email(
    payload: EmailSendRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_authenticated_user),
) -> dict[str, str]:
    """Send email notification."""
    try:
        message = build_email_message(payload.subject, payload.body, payload.recipient)
    except EmailServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    background_tasks.add_task(send_email, message)
    return {"status": "queued"}
