"""Settings loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram bot token from @BotFather.
    bot_token: str
    # Comma-separated Telegram user ids allowed to manage the knowledge base.
    admin_ids: str = ""

    # PostgreSQL with the pgvector extension (docker-compose provides one).
    db_url: str = "postgresql+asyncpg://faq:faq@localhost:5432/faq"

    # OpenAI-compatible API. Leave base_url empty for OpenAI; set it to a proxy
    # aggregator's endpoint where api.openai.com is unreachable.
    openai_api_key: str
    openai_base_url: str = ""
    chat_model: str = "gpt-4o-mini"
    embed_model: str = "text-embedding-3-small"
    embed_dim: int = 1536

    # Retrieval tuning.
    rag_top_k: int = 4
    rag_min_similarity: float = 0.3

    @property
    def admin_id_list(self) -> list[int]:
        return [int(x) for x in self.admin_ids.replace(" ", "").split(",") if x]

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_id_list


@lru_cache
def get_settings() -> Settings:
    return Settings()
