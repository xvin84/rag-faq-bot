"""Wiring: open a session, build a RagIndex over pgvector-rag, and expose the two
operations the bot needs — answer a question and ingest a document."""
from __future__ import annotations

from pgvector_rag import DocumentInfo, PgVectorStore, RagIndex, chunk_markdown

from core.config import get_settings
from db.session import async_session
from services.answer import Answer, answer_question
from services.openai_chat import chat, get_embedder

_settings = get_settings()


async def answer(question: str) -> Answer:
    async with async_session() as session:
        rag = RagIndex(PgVectorStore(session), get_embedder())
        return await answer_question(
            rag, chat, question,
            top_k=_settings.rag_top_k, min_similarity=_settings.rag_min_similarity,
        )


async def ingest(name: str, text: str) -> int:
    """Chunk, embed and store a document. Returns the number of chunks indexed."""
    async with async_session() as session:
        rag = RagIndex(PgVectorStore(session), get_embedder())
        await rag.index_markdown(name, text)
    return len(chunk_markdown(text))


async def list_documents() -> list[DocumentInfo]:
    async with async_session() as session:
        return await PgVectorStore(session).list_documents()


async def delete_document(document_id: str) -> None:
    async with async_session() as session:
        await PgVectorStore(session).delete_document(document_id)
