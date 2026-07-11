"""Rendering the model's reply into safe HTML for Telegram."""
from __future__ import annotations

from bot.handlers.ask import format_answer
from services.answer import Answer


def test_appends_sources_footer():
    text = format_answer(Answer("Доставка стоит 300 ₽.", ["faq.md", "prices.txt"]))
    assert text.startswith("Доставка стоит 300 ₽.")
    assert "📚 <b>Источник:</b> <i>faq.md, prices.txt</i>" in text


def test_no_footer_without_sources():
    assert format_answer(Answer("Не нашёл.", [])) == "Не нашёл."


def test_model_reply_and_sources_are_html_escaped():
    text = format_answer(Answer("1 < 2 & 3", ["a<b>.md"]))
    assert "1 &lt; 2 &amp; 3" in text
    assert "a&lt;b&gt;.md" in text
