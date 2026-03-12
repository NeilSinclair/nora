"""Auth endpoint: verifies PASSWORD and issues a signed JWT HttpOnly cookie."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Response
from jose import jwt
from pydantic import BaseModel

from backend.config import settings

router = APIRouter()

_ALGORITHM = "HS256"
_TOKEN_EXPIRE_DAYS = 30


class LoginRequest(BaseModel):
    password: str


def create_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"exp": expire}, settings.JWT_SECRET, algorithm=_ALGORITHM)


def verify_token(token: str) -> bool:
    try:
        jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALGORITHM])
        return True
    except Exception:
        return False


@router.post("/auth")
async def login(request: LoginRequest, response: Response):
    if request.password != settings.PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_token()
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="strict",
        max_age=_TOKEN_EXPIRE_DAYS * 86400,
    )
    return {"ok": True}


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}
