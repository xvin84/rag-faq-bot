"""Knowledge-base management: admins upload .txt/.md files to index, list the
indexed documents with /docs and delete any of them with one tap. ADMIN_IDS only."""
from __future__ import annotations

from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command, Filter
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    TelegramObject,
)
from pgvector_rag import DocumentInfo

from core.config import get_settings
from services import rag_service

admin_router = Router()
settings = get_settings()

DELETE_PREFIX = "deldoc:"
EMPTY_BASE_TEXT = "База знаний пуста. Пришлите файл <b>.txt</b> или <b>.md</b>, чтобы наполнить её."


class IsAdmin(Filter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user and settings.is_admin(user.id))


admin_router.message.filter(IsAdmin())
admin_router.callback_query.filter(IsAdmin())


def docs_view(docs: list[DocumentInfo]) -> tuple[str, InlineKeyboardMarkup | None]:
    """Build the /docs message: a numbered list plus a delete button per document."""
    if not docs:
        return EMPTY_BASE_TEXT, None
    lines = ["Документы в базе знаний:\n"]
    buttons = []
    for i, doc in enumerate(docs, 1):
        lines.append(
            f"{i}. <b>{escape(doc.name)}</b> — {doc.chunk_count} фрагм., {doc.created_at:%d.%m.%Y}"
        )
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 Удалить «{doc.name}»", callback_data=f"{DELETE_PREFIX}{doc.id}"
            )
        ])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons)


@admin_router.message(Command("admin"))
async def admin_help(message: Message) -> None:
    await message.answer(
        "Управление базой знаний.\n\n"
        "Пришлите файл <b>.txt</b> или <b>.md</b> с материалами (FAQ, услуги, прайс) — "
        "я разобью его на фрагменты, проиндексирую и буду отвечать по нему.\n"
        "Имя файла станет названием источника.\n\n"
        "/docs — список документов и удаление устаревших."
    )


@admin_router.message(Command("docs"))
async def list_docs(message: Message) -> None:
    text, keyboard = docs_view(await rag_service.list_documents())
    await message.answer(text, reply_markup=keyboard)


@admin_router.callback_query(F.data.startswith(DELETE_PREFIX))
async def delete_doc(callback: CallbackQuery) -> None:
    await rag_service.delete_document(callback.data.removeprefix(DELETE_PREFIX))
    await callback.answer("Документ удалён")
    text, keyboard = docs_view(await rag_service.list_documents())
    await callback.message.edit_text(text, reply_markup=keyboard)


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
    await message.answer(f"✅ Добавлено в базу: <b>{escape(doc.file_name)}</b> ({chunks} фрагментов).")
