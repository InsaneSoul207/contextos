"""
ContextOS Core Configuration.

Loads settings from environment variables and .env file using Pydantic Settings.
"""

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    contextos_data_dir: str = "~/.contextos"
    contextos_host: str = "127.0.0.1"
    contextos_port: int = 44480
    contextos_log_level: str = "info"
    contextos_api_key: str = "change-me-to-a-random-secret"

    @property
    def host(self) -> str:
        return self.contextos_host

    @property
    def port(self) -> int:
        return self.contextos_port

    @property
    def log_level(self) -> str:
        return self.contextos_log_level

    @property
    def api_key(self) -> str:
        return self.contextos_api_key

    # LLM
    llm_provider: str = "local"
    llm_api_key: str = ""
    llm_model: str = ""

    # Models
    local_embedding_model: str = "all-MiniLM-L6-v2"
    local_clip_model: str = "openai/clip-vit-base-patch32"

    # OCR
    ocr_language: str = "en"

    # Database
    postgres_url: str = ""  # e.g. postgresql://user:password@localhost:5432/contextos

    # Limits
    max_file_size_mb: int = 100
    indexing_batch_size: int = 10

    @computed_field  # type: ignore[prop-decorator]
    @property
    def data_dir(self) -> Path:
        """Return the resolved data directory, creating it if necessary."""
        try:
            path = Path(os.path.expanduser(self.contextos_data_dir)).resolve()
            path.mkdir(parents=True, exist_ok=True)
            return path
        except Exception:
            fallback = Path(__file__).resolve().parent.parent.parent / "data"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_path(self) -> Path:
        """Return the path to the SQLite database file."""
        return self.data_dir / "contextos.db"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def uploads_dir(self) -> Path:
        """Return the path for uploaded files, creating it if necessary."""
        path = self.data_dir / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings()
