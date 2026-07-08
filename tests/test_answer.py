from __future__ import annotations

from pgvector_rag import SearchHit

from services.answer import (
    NO_CONTEXT_REPLY,
    answer_question,
    build_context,
    build_messages,
    unique_sources,
)


def hit(doc="Тарифы", title=None, content="Базовый тариф — 990 ₽/мес.", sim=0.8) -> SearchHit:
    return SearchHit(
        chunk_id=1, document_id="d1", document_name=doc, title=title,
        breadcrumb=None, content=content, metadata={}, similarity=sim,
    )


class FakeRag:
    def __init__(self, hits):
        self._hits = hits
        self.calls = []

    async def search(self, question, *, top_k, min_similarity):
        self.calls.append((question, top_k, min_similarity))
        return self._hits


class FakeChat:
    def __init__(self, reply="Базовый тариф стоит 990 ₽ в месяц."):
        self.reply = reply
        self.seen_messages = None

    async def __call__(self, messages):
        self.seen_messages = messages
        return self.reply


def test_build_context_labels_each_chunk():
    ctx = build_context([hit(doc="FAQ", title="Оплата", content="Картой или СБП.")])
    assert "[FAQ · Оплата]" in ctx
    assert "Картой или СБП." in ctx


def test_build_messages_has_system_and_puts_question_and_context():
    msgs = build_messages("Как оплатить?", [hit()])
    assert msgs[0]["role"] == "system"
    assert "Как оплатить?" in msgs[1]["content"]
    assert "Базовый тариф" in msgs[1]["content"]


def test_unique_sources_dedupes_keeping_order():
    hits = [hit(doc="A"), hit(doc="B"), hit(doc="A")]
    assert unique_sources(hits) == ["A", "B"]


async def test_answer_grounds_on_hits_and_returns_sources():
    rag, chat = FakeRag([hit(doc="Тарифы")]), FakeChat("Ответ по контексту.")
    result = await answer_question(rag, chat, "Сколько стоит?", top_k=4, min_similarity=0.3)

    assert result.text == "Ответ по контексту."
    assert result.sources == ["Тарифы"]
    assert rag.calls == [("Сколько стоит?", 4, 0.3)]
    # The model was called with grounded messages.
    assert chat.seen_messages[0]["role"] == "system"


async def test_no_hits_returns_fallback_without_calling_model():
    rag, chat = FakeRag([]), FakeChat()
    result = await answer_question(rag, chat, "Вопрос без ответа", top_k=4, min_similarity=0.3)

    assert result.text == NO_CONTEXT_REPLY
    assert result.sources == []
    assert chat.seen_messages is None  # model must not be called when there's no context
