"""
config.py
Loads and validates all environment variables from .env.
All other modules import from here — never from os.environ directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    """Fetch a required env variable or raise a clear error at startup."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is missing or empty. "
            "Check your .env file."
        )
    return value


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default)


@dataclass(frozen=True)
class Settings:
    # ── D2L ──────────────────────────────────────────────────────────────────
    d2l_base_url: str          # e.g. https://your-institution.brightspace.com
    d2l_api_token: str         # Valence API bearer token

    # ── Notion ────────────────────────────────────────────────────────────────
    notion_api_token: str
    notion_assignments_db_id: str
    notion_quizzes_db_id: str
    notion_syllabus_page_id: str

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    postgres_url: str          # e.g. postgresql+asyncpg://user:pass@host/db

    # ── Redis (optional) ─────────────────────────────────────────────────────
    redis_url: str
    cache_ttl_seconds: int

    # ── OpenAI (optional) ────────────────────────────────────────────────────
    openai_api_key: str

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: str
    log_level: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance.

    Called once at import time by dependent modules; subsequent calls return
    the cached object so .env parsing only happens once.
    """
    return Settings(
        # D2L
        d2l_base_url=_require("D2L_BASE_URL"),
        d2l_api_token=_require("D2L_API_TOKEN"),
        # Notion
        notion_api_token=_require("NOTION_API_TOKEN"),
        notion_assignments_db_id=_optional("NOTION_ASSIGNMENTS_DB_ID"),
        notion_quizzes_db_id=_optional("NOTION_QUIZZES_DB_ID"),
        notion_syllabus_page_id=_optional("NOTION_SYLLABUS_PAGE_ID"),
        # PostgreSQL
        postgres_url=_require("POSTGRES_URL"),
        # Redis
        redis_url=_optional("REDIS_URL", "redis://localhost:6379"),
        cache_ttl_seconds=int(_optional("CACHE_TTL_SECONDS", "300")),
        # OpenAI
        openai_api_key=_optional("OPENAI_API_KEY"),
        # App
        app_env=_optional("APP_ENV", "development"),
        log_level=_optional("LOG_LEVEL", "INFO"),
    )