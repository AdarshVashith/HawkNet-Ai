"""Auth stub — JWT scaffolding for later hardening.

For the hackathon, auth is disabled by default (AUTH_ENABLED=false).
When enabled, clients must send Authorization: Bearer <token>.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)

_auth_warning_logged = False


def log_auth_status_warning(settings: Settings) -> None:
    """Log a SECURITY WARNING once if AUTH_ENABLED is false.

    Call this from the application lifespan so it's visible in server logs.
    """
    global _auth_warning_logged
    if not settings.auth_enabled and not _auth_warning_logged:
        logger.warning(
            "[SECURITY WARNING] AUTH_ENABLED=false — all API endpoints are publicly "
            "accessible without authentication. Set AUTH_ENABLED=true and supply a "
            "strong JWT_SECRET before any public or production deployment."
        )
        _auth_warning_logged = True



def create_access_token(
    subject: str,
    settings: Settings | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token (stub implementation)."""
    settings = settings or get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    settings = settings or get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security)
    ] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Dependency that optionally enforces Bearer auth.

    When AUTH_ENABLED is false, returns an anonymous stub user.
    """
    settings = settings or get_settings()

    if not settings.auth_enabled:
        return {"sub": "anonymous", "roles": ["public"], "auth_enabled": False}

    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials, settings)
    except JWTError as exc:
        logger.warning("Invalid token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return {"sub": payload.get("sub"), "roles": payload.get("roles", []), "auth_enabled": True}
