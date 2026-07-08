"""/start greeting."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from core.config import get_settings

start_router = Router()
settings = get_settings()


@start_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = (
        "Здравствуйте! Я отвечаю на вопросы по нашей базе знаний.\n\n"
        "Просто напишите вопрос — например, «сколько стоит доставка?» — и я найду "
        "ответ в загруженных материалах."
    )
    if settings.is_admin(message.from_user.id):
        text += "\n\nВы администратор: пришлите .txt или .md файл, чтобы пополнить базу (/admin)."
    await message.answer(text)
