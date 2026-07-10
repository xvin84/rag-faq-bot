"""The /docs view is a pure function over DocumentInfo rows — tested without
aiogram dispatching, OpenAI or a database."""
from __future__ import annotations

from datetime import datetime

from pgvector_rag import DocumentInfo

from bot.handlers.admin import DELETE_PREFIX, EMPTY_BASE_TEXT, docs_view


def _doc(**over) -> DocumentInfo:
    base = dict(
        id="doc-uuid",
        name="faq.md",
        weight=1.0,
        is_archived=False,
        created_at=datetime(2026, 7, 8),
        chunk_count=12,
    )
    base.update(over)
    return DocumentInfo(**base)


def test_empty_base_has_no_keyboard():
    text, keyboard = docs_view([])
    assert text == EMPTY_BASE_TEXT
    assert keyboard is None


def test_lists_documents_with_chunk_counts_and_dates():
    text, keyboard = docs_view([_doc(), _doc(id="doc-2", name="prices.txt", chunk_count=3)])
    assert "1. <b>faq.md</b> — 12 фрагм., 08.07.2026" in text
    assert "2. <b>prices.txt</b> — 3 фрагм." in text
    assert keyboard is not None


def test_delete_button_per_document_carries_its_id():
    _, keyboard = docs_view([_doc(id="aaa"), _doc(id="bbb", name="prices.txt")])
    callbacks = [row[0].callback_data for row in keyboard.inline_keyboard]
    assert callbacks == [f"{DELETE_PREFIX}aaa", f"{DELETE_PREFIX}bbb"]


def test_document_name_is_html_escaped():
    text, _ = docs_view([_doc(name="a<b>&c.md")])
    assert "a&lt;b&gt;&amp;c.md" in text
