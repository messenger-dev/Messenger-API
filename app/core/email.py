"""Minimal email sender using SMTP for notification delivery."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage as StdEmailMessage

from app.core.config import settings
from app.core.exceptions import EmailServiceError


def build_email_message(subject: str, body: str, recipient: str, sender: str | None = None) -> StdEmailMessage:
    if not settings.EMAIL_SMTP_HOST or not settings.EMAIL_FROM:
        raise EmailServiceError("Email service is not configured")

    message = StdEmailMessage()
    message["Subject"] = subject.strip()
    message["From"] = sender or settings.EMAIL_FROM
    message["To"] = recipient
    message.set_content(body.strip())
    return message


def send_email(message: StdEmailMessage) -> None:
    if not settings.EMAIL_SMTP_HOST or not settings.EMAIL_FROM:
        raise EmailServiceError("Email service is not configured")

    smtp_kwargs: dict[str, object] = {
        "host": settings.EMAIL_SMTP_HOST,
        "port": settings.EMAIL_SMTP_PORT,
        "timeout": 10,
    }

    smtp = smtplib.SMTP_SSL(**smtp_kwargs) if settings.EMAIL_SMTP_USE_SSL else smtplib.SMTP(**smtp_kwargs)
    try:
        if settings.EMAIL_SMTP_STARTTLS and not settings.EMAIL_SMTP_USE_SSL:
            smtp.starttls()
        if settings.EMAIL_SMTP_USER and settings.EMAIL_SMTP_PASSWORD:
            smtp.login(settings.EMAIL_SMTP_USER, settings.EMAIL_SMTP_PASSWORD)
        smtp.send_message(message)
    finally:
        smtp.quit()
