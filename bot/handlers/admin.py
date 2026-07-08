"""Knowledge-base management: admins upload .txt/.md files to index. ADMIN_IDS only."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command, Filter
from aiogram.types import Message, TelegramObject

from core.config import get_settings
from services import rag_service

admin_router = Router()
settings = get_settings()


class IsAdmin(Filter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user and settings.is_admin(user.id))


admin_router.message.filter(IsAdmin())


@admin_router.message(Command("admin"))
async def admin_help(message: Message) -> None:
    await message.answer(
        "Управление базой знаний.\n\n"
        "Пришлите файл <b>.txt</b> или <b>.md</b> с материалами (FAQ, услуги, прайс) — "
        "я разобью его на фрагменты, проиндексирую и буду отвечать по нему.\n"
        "Имя файла станет названием источника."
    )


@admin_router.message(F.document)
async def on_document(message: Message, bot: Bot) -> None:
    doc = message.document
    if not doc.file_name.lower().endswith((".txt", ".md")):
        await message.answer("Нужен текстовый файл: .txt или .md.")
        return
    file = await bot.get_file(doc.file_id)
    buffer = await bot.download_file(file.file_path)
    text = buffer.read().decode("utf-8", errors="replace").strip()
    if not text:
        await message.answer("Файл пустой.")
        return
    await message.answer("Индексирую документ…")
    chunks = await rag_service.ingest(doc.file_name, text)
    await message.answer(f"✅ Добавлено в базу: <b>{doc.file_name}</b> ({chunks} фрагментов).")
