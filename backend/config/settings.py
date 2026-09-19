"""
SetuAI — Application Settings

Scaffolding only (Slice 1 prep). Reads configuration from environment variables /
a repo-root `.env` file. No feature-specific settings (schedule parsing, LLM, etc.)
belong here yet — add them when the corresponding slice needs them.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root is two levels up from this file (backend/config/settings.py -> backend -> repo root).
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    backend_port: int = 8000

    # Local Postgres default for dev — override via .env, never hardcode real credentials.
    database_url: str = "postgresql://postgres:postgres@localhost:5432/setuai"

    # Frontend origin allowed to call the API in dev (CORS).
    frontend_origin: str = "http://localhost:3000"

    # Upload constraints (docs/API.md) — centralized here so every upload
    # endpoint enforces the same limit instead of each hardcoding it.
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB

    # Where uploaded source documents are written (docs/API.md "File Storage").
    # Relative to repo root; not committed (see .gitignore).
    uploads_dir: Path = REPO_ROOT / "data" / "uploads"


settings = Settings()
