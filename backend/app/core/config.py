"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent

_DEFAULT_JWT_SECRET = "change-me-in-production"  # noqa: S105 – placeholder only


class Settings(BaseSettings):
    """Runtime settings for the HawkNet-Ai API."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "HawkNet-Ai"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    # SQLite for hackathon; swap DATABASE_URL to Postgres later
    database_url: str = f"sqlite:///{(BACKEND_ROOT / 'db' / 'app.db').as_posix()}"

    # CORS — frontend Vite default
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Auth
    auth_enabled: bool = False
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Rate limiting (per client IP, sliding-window)
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60

    # Alerting — if set, high-risk events POST here; else fall back to .jsonl
    alert_webhook_url: str | None = None
    alert_webhook_timeout_seconds: float = 5.0

    # Call session (DB-backed transcript buffer)
    call_session_ttl_seconds: int = 3600  # 1 hour

    log_level: str = "INFO"

    @model_validator(mode="after")
    def _check_production_secrets(self) -> "Settings":
        """Refuse to start with the default JWT secret in production."""
        if (
            self.environment.lower() == "production"
            and self.jwt_secret == _DEFAULT_JWT_SECRET
        ):
            raise ValueError(
                "FATAL: JWT_SECRET must be set to a strong random value when "
                "ENVIRONMENT=production. Refusing to start with the default placeholder."
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

