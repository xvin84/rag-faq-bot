"""Any plain text is treated as a question and answered from the knowledge base."""
from __future__ import annotations

import logging
from html import escape

from aiogram import F, Router
from aiogram.types import Message

from services import rag_service
from services.answer import Answer

ask_router = Router()
logger = logging.getLogger(__name__)

SEARCHING_TEXT = "🔎 Ищу ответ в базе знаний…"
ERROR_TEXT = "😔 Упс, что-то пошло не так. Попробуйте ещё раз чуть позже."


def format_answer(result: Answer) -> str:
    """Render the model's plain-text reply as safe HTML with a sources footer."""
    text = escape(result.text)
    if result.sources:
        listed = ", ".join(escape(s) for s in result.sources)
        text += f"\n\n📚 <b>Источник:</b> <i>{listed}</i>"
    return text


@ask_router.message(F.text & ~F.text.startswith("/"))
async def answer_question(message: Message) -> None:
    placeholder = await message.answer(SEARCHING_TEXT)
    try:
        result = await rag_service.answer(message.text)
    except Exception:  # noqa: BLE001 — surface a friendly message, log the detail
        logger.exception("failed to answer question")
        await placeholder.edit_text(ERROR_TEXT)
        return
    await placeholder.edit_text(format_answer(result))
