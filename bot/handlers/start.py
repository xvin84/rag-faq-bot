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
        "👋 Здравствуйте! Я — бот-консультант: отвечаю на вопросы по базе знаний "
        "компании.\n\n"
        "💬 Просто напишите вопрос обычным языком — например, "
        "<i>«сколько стоит доставка?»</i> — я найду ответ в загруженных материалах "
        "и укажу источник.\n\n"
        "🙅 Если ответа в базе нет, я честно скажу об этом, а не стану выдумывать."
    )
    if settings.is_admin(message.from_user.id):
        text += "\n\n🔑 Вы администратор. Панель управления базой знаний: /admin"
    await message.answer(text)
