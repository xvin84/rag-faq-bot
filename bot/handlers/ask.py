"""Any plain text is treated as a question and answered from the knowledge base."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message

from services import rag_service

ask_router = Router()
logger = logging.getLogger(__name__)


@ask_router.message(F.text & ~F.text.startswith("/"))
async def answer_question(message: Message) -> None:
    await message.bot.send_chat_action(message.chat.id, "typing")
    try:
        result = await rag_service.answer(message.text)
    except Exception:  # noqa: BLE001 — surface a friendly message, log the detail
        logger.exception("failed to answer question")
        await message.answer("Упс, что-то пошло не так. Попробуйте ещё раз чуть позже.")
        return

    text = result.text
    if result.sources:
        text += "\n\n📚 Источник: " + ", ".join(result.sources)
    await message.answer(text)
