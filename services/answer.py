"""Grounded question answering.

The bot never lets the model free-wheel: it retrieves the most relevant chunks
from the knowledge base (via pgvector-rag) and asks the model to answer *only*
from that context, or admit it doesn't know. The prompt-building and
source-formatting are pure functions, so the grounding rules are unit-tested
without touching OpenAI or the database.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pgvector_rag import RagIndex, SearchHit

SYSTEM_PROMPT = (
    "Ты — вежливый ассистент службы поддержки компании. Отвечай на вопрос "
    "пользователя СТРОГО на основе приведённого ниже контекста из базы знаний. "
    "Если ответа в контексте нет — честно скажи, что не располагаешь такой "
    "информацией, и предложи обратиться в поддержку. Ничего не выдумывай. "
    "Отвечай кратко, по делу и на языке вопроса."
)

NO_CONTEXT_REPLY = (
    "Я не нашёл ответа на этот вопрос в базе знаний 🤔\n"
    "Попробуйте переформулировать вопрос или обратитесь в поддержку."
)

# The callable that talks to the LLM. Injected so tests can fake it.
ChatFn = Callable[[list[dict]], Awaitable[str]]


@dataclass
class Answer:
    text: str
    sources: list[str]


def build_context(hits: list[SearchHit]) -> str:
    blocks = []
    for h in hits:
        label = h.document_name + (f" · {h.title}" if h.title else "")
        blocks.append(f"[{label}]\n{h.content}")
    return "\n\n".join(blocks)


def build_messages(question: str, hits: list[SearchHit]) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Контекст:\n{build_context(hits)}\n\nВопрос: {question}"},
    ]


def unique_sources(hits: list[SearchHit]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for h in hits:
        if h.document_name not in seen:
            seen.add(h.document_name)
            ordered.append(h.document_name)
    return ordered


async def answer_question(
    rag: RagIndex,
    chat: ChatFn,
    question: str,
    *,
    top_k: int,
    min_similarity: float,
) -> Answer:
    """Retrieve, ground and answer. Returns the fallback reply (without calling the
    model) when nothing relevant is found."""
    hits = await rag.search(question, top_k=top_k, min_similarity=min_similarity)
    if not hits:
        return Answer(NO_CONTEXT_REPLY, [])
    reply = await chat(build_messages(question, hits))
    return Answer(reply, unique_sources(hits))
