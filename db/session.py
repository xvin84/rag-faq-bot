"""Async engine, session factory, and schema init via pgvector-rag."""
from __future__ import annotations

from pgvector_rag import PgVectorStore
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.config import get_settings

_settings = get_settings()

engine = create_async_engine(_settings.db_url, future=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Create the pgvector extension, tables and index (idempotent)."""
    async with async_session() as session:
        await PgVectorStore(session).create_schema(dim=_settings.embed_dim)
