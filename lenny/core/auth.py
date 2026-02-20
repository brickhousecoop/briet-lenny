"""Session management for the BRIET lending demo.

Uses itsdangerous signed cookies to store user state.
No database required — all session data lives in the cookie.
"""

import os
import time
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

SECRET_KEY = os.environ.get("LENNY_SECRET", "briet-demo-secret-change-in-production")
SESSION_COOKIE = "lenny_session"
SESSION_MAX_AGE = 86400  # 24 hours

_serializer = URLSafeTimedSerializer(SECRET_KEY)


def create_session(email: str, library: str, borrowed: list[str] | None = None) -> str:
    """Create a signed session token."""
    payload = {
        "email": email,
        "library": library,
        "borrowed": borrowed or [],
    }
    return _serializer.dumps(payload)


def verify_session(token: str) -> dict | None:
    """Verify and decode a session token. Returns None if invalid/expired."""
    try:
        return _serializer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def get_session(request) -> dict | None:
    """Extract session from request cookies."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return verify_session(token)


def update_borrowed(session: dict, book_id: str, action: str) -> str:
    """Update the borrowed list and return a new signed session token.

    action: "borrow" to add, "return" to remove.
    """
    borrowed = list(session.get("borrowed", []))
    if action == "borrow" and book_id not in borrowed:
        borrowed.append(book_id)
    elif action == "return" and book_id in borrowed:
        borrowed.remove(book_id)
    return create_session(session["email"], session["library"], borrowed)
