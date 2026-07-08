"""OpenAI clients: one embedder (via pgvector-rag) and a chat helper, sharing a
single AsyncOpenAI instance. ``base_url`` lets you point at a proxy aggregator
where api.openai.com is blocked."""
from __future__ import annotations

from functools import lru_cache

from openai import AsyncOpenAI
from pgvector_rag import OpenAIEmbedder

from core.config import get_settings

_settings = get_settings()


@lru_cache
def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=_settings.openai_api_key, base_url=_settings.openai_base_url or None)


@lru_cache
def get_embedder() -> OpenAIEmbedder:
    return OpenAIEmbedder(model=_settings.embed_model, dimensions=_settings.embed_dim, client=_client())


async def chat(messages: list[dict]) -> str:
    resp = await _client().chat.completions.create(
        model=_settings.chat_model,
        messages=messages,
        temperature=0.2,
        max_tokens=500,
    )
    return (resp.choices[0].message.content or "").strip()
