"""Admin-panel views are pure functions over DocumentInfo rows — tested without
aiogram dispatching, OpenAI or a database."""
from __future__ import annotations

from datetime import datetime

from pgvector_rag import DocumentInfo

from bot.handlers.admin import (
    ASK_DELETE_PREFIX,
    CB_DOCS,
    CB_PANEL,
    DELETE_PREFIX,
    DOC_PREFIX,
    EMPTY_BASE_TEXT,
    confirm_delete_view,
    doc_view,
    docs_view,
    panel_view,
    stats_view,
)


def _doc(**over) -> DocumentInfo:
    base = dict(
        id="doc-uuid",
        name="faq.md",
        weight=1.0,
        is_archived=False,
        created_at=datetime(2026, 7, 8, 12, 30),
        chunk_count=12,
    )
    base.update(over)
    return DocumentInfo(**base)


def _callbacks(keyboard) -> list[str]:
    return [btn.callback_data for row in keyboard.inline_keyboard for btn in row]


def test_panel_links_to_all_sections():
    _, keyboard = panel_view()
    assert _callbacks(keyboard) == [CB_DOCS, "stats", "help"]


def test_empty_base_still_navigates_back():
    text, keyboard = docs_view([])
    assert text == EMPTY_BASE_TEXT
    assert _callbacks(keyboard) == [CB_PANEL]


def test_docs_list_has_a_card_button_per_document():
    _, keyboard = docs_view([_doc(id="aaa"), _doc(id="bbb", name="prices.txt")])
    assert _callbacks(keyboard) == [f"{DOC_PREFIX}aaa", f"{DOC_PREFIX}bbb", CB_PANEL]


def test_doc_card_shows_details_and_asks_before_deleting():
    text, keyboard = doc_view(_doc())
    assert "faq.md" in text and "12" in text and "08.07.2026" in text
    assert _callbacks(keyboard) == [f"{ASK_DELETE_PREFIX}doc-uuid", CB_DOCS]


def test_confirmation_offers_delete_and_cancel():
    text, keyboard = confirm_delete_view(_doc())
    assert "faq.md" in text
    assert _callbacks(keyboard) == [f"{DELETE_PREFIX}doc-uuid", f"{DOC_PREFIX}doc-uuid"]


def test_stats_counts_documents_and_chunks():
    text, _ = stats_view([_doc(), _doc(id="b", name="prices.txt", chunk_count=3)])
    assert "<b>2</b>" in text and "<b>15</b>" in text


def test_document_name_is_html_escaped_in_views():
    evil = _doc(name="a<b>&c.md")
    for text in (doc_view(evil)[0], confirm_delete_view(evil)[0]):
        assert "a&lt;b&gt;&amp;c.md" in text
