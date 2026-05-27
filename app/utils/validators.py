import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def validate_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value))
