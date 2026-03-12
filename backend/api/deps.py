"""Shared FastAPI dependencies."""

from fastapi import Cookie, HTTPException

from backend.api.auth import verify_token


def require_auth(session: str | None = Cookie(default=None)) -> None:
    """Dependency that rejects requests without a valid session cookie."""
    if not session or not verify_token(session):
        raise HTTPException(status_code=401, detail="Not authenticated")
