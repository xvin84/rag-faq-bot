"""Entry point: init the pgvector schema, then poll."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.handlers.admin import admin_router
from bot.handlers.ask import ask_router
from bot.handlers.start import start_router
from core.config import get_settings
from db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    await init_db()

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(admin_router)   # admin-filtered; /admin + file uploads
    dp.include_router(ask_router)     # catch-all: plain text -> answered from the KB

    await bot.set_my_commands([
        BotCommand(command="start", description="О боте"),
        BotCommand(command="admin", description="Управление базой знаний (админ)"),
        BotCommand(command="docs", description="Документы в базе: список и удаление (админ)"),
    ])
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("RAG FAQ bot started.")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
