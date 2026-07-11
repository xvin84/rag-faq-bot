"""Knowledge-base management for ADMIN_IDS: an inline-keyboard panel (/admin) to
browse documents, view a document card, delete with confirmation and see base
stats; uploading a .txt/.md file indexes it.

Every view is a pure function returning (text, keyboard), so navigation is
unit-tested without aiogram dispatching or a database; callbacks just edit the
panel message in place.
"""
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

CB_PANEL = "panel"
CB_DOCS = "docs"
CB_STATS = "stats"
CB_HELP = "help"
DOC_PREFIX = "doc:"          # document card
ASK_DELETE_PREFIX = "del:"   # confirmation step
DELETE_PREFIX = "delok:"     # confirmed deletion

EMPTY_BASE_TEXT = (
    "📭 База знаний пуста.\n\n"
    "Пришлите файл <b>.txt</b> или <b>.md</b>, чтобы наполнить её."
)


class IsAdmin(Filter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user and settings.is_admin(user.id))


admin_router.message.filter(IsAdmin())
admin_router.callback_query.filter(IsAdmin())


# ── Views: pure (text, keyboard) builders ────────────────────────────────────


def _kb(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=list(rows))


def _back_to_panel() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text="⬅️ В панель", callback_data=CB_PANEL)]


def panel_view() -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "🛠 <b>Панель администратора</b>\n\n"
        "Управляйте базой знаний, по которой бот отвечает клиентам."
    )
    keyboard = _kb(
        [InlineKeyboardButton(text="📚 Документы", callback_data=CB_DOCS)],
        [InlineKeyboardButton(text="📊 Статистика", callback_data=CB_STATS)],
        [InlineKeyboardButton(text="➕ Как пополнить базу", callback_data=CB_HELP)],
    )
    return text, keyboard


def docs_view(docs: list[DocumentInfo]) -> tuple[str, InlineKeyboardMarkup]:
    if not docs:
        return EMPTY_BASE_TEXT, _kb(_back_to_panel())
    text = (
        "📚 <b>Документы в базе знаний</b>\n\n"
        "Нажмите на документ, чтобы посмотреть карточку или удалить его."
    )
    rows = [
        [
            InlineKeyboardButton(
                text=f"📄 {doc.name} · {doc.chunk_count} фрагм.",
                callback_data=f"{DOC_PREFIX}{doc.id}",
            )
        ]
        for doc in docs
    ]
    rows.append(_back_to_panel())
    return text, _kb(*rows)


def doc_view(doc: DocumentInfo) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        f"📄 <b>{escape(doc.name)}</b>\n\n"
        f"🧩 Фрагментов в индексе: <b>{doc.chunk_count}</b>\n"
        f"🗓 Загружен: <b>{doc.created_at:%d.%m.%Y %H:%M}</b>"
    )
    keyboard = _kb(
        [
            InlineKeyboardButton(
                text="🗑 Удалить документ", callback_data=f"{ASK_DELETE_PREFIX}{doc.id}"
            )
        ],
        [InlineKeyboardButton(text="⬅️ К списку", callback_data=CB_DOCS)],
    )
    return text, keyboard


def confirm_delete_view(doc: DocumentInfo) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        f"⚠️ Удалить <b>{escape(doc.name)}</b> безвозвратно?\n\n"
        f"Бот перестанет отвечать по этому документу "
        f"({doc.chunk_count} фрагм. будет удалено)."
    )
    keyboard = _kb(
        [
            InlineKeyboardButton(
                text="✅ Да, удалить", callback_data=f"{DELETE_PREFIX}{doc.id}"
            ),
            InlineKeyboardButton(text="↩️ Отмена", callback_data=f"{DOC_PREFIX}{doc.id}"),
        ],
    )
    return text, keyboard


def stats_view(docs: list[DocumentInfo]) -> tuple[str, InlineKeyboardMarkup]:
    chunks = sum(d.chunk_count for d in docs)
    lines = [
        "📊 <b>Статистика базы знаний</b>\n",
        f"📚 Документов: <b>{len(docs)}</b>",
        f"🧩 Фрагментов в индексе: <b>{chunks}</b>",
    ]
    if docs:
        latest = max(docs, key=lambda d: d.created_at)
        lines.append(
            f"🕓 Последнее пополнение: <b>{latest.created_at:%d.%m.%Y}</b> "
            f"({escape(latest.name)})"
        )
    return "\n".join(lines), _kb(_back_to_panel())


def help_view() -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "➕ <b>Как пополнить базу</b>\n\n"
        "Пришлите мне файл <b>.txt</b> или <b>.md</b> с материалами — FAQ, описание "
        "услуг, прайс.\n\n"
        "Я разобью его на фрагменты по заголовкам, проиндексирую и сразу начну "
        "отвечать клиентам по нему. Имя файла станет названием источника в ответах."
    )
    return text, _kb(_back_to_panel())


# ── Commands ─────────────────────────────────────────────────────────────────


@admin_router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    text, keyboard = panel_view()
    await message.answer(text, reply_markup=keyboard)


@admin_router.message(Command("docs"))
async def list_docs(message: Message) -> None:
    text, keyboard = docs_view(await rag_service.list_documents())
    await message.answer(text, reply_markup=keyboard)


@admin_router.message(F.document)
async def on_document(message: Message, bot: Bot) -> None:
    doc = message.document
    if not doc.file_name.lower().endswith((".txt", ".md")):
        await message.answer("🤷 Нужен текстовый файл: <b>.txt</b> или <b>.md</b>.")
        return
    file = await bot.get_file(doc.file_id)
    buffer = await bot.download_file(file.file_path)
    text = buffer.read().decode("utf-8", errors="replace").strip()
    if not text:
        await message.answer("🤔 Файл пустой.")
        return
    placeholder = await message.answer("⏳ Индексирую документ…")
    chunks = await rag_service.ingest(doc.file_name, text)
    await placeholder.edit_text(
        f"✅ Добавлено в базу: <b>{escape(doc.file_name)}</b> ({chunks} фрагм.).\n"
        f"Бот уже отвечает по этому документу. Список: /docs"
    )


# ── Panel navigation callbacks ───────────────────────────────────────────────


async def _find_doc(document_id: str) -> DocumentInfo | None:
    return next(
        (d for d in await rag_service.list_documents() if d.id == document_id), None
    )


async def _show_docs_list(callback: CallbackQuery) -> None:
    text, keyboard = docs_view(await rag_service.list_documents())
    await callback.message.edit_text(text, reply_markup=keyboard)


@admin_router.callback_query(F.data == CB_PANEL)
async def cb_panel(callback: CallbackQuery) -> None:
    text, keyboard = panel_view()
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data == CB_DOCS)
async def cb_docs(callback: CallbackQuery) -> None:
    await _show_docs_list(callback)
    await callback.answer()


@admin_router.callback_query(F.data == CB_STATS)
async def cb_stats(callback: CallbackQuery) -> None:
    text, keyboard = stats_view(await rag_service.list_documents())
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data == CB_HELP)
async def cb_help(callback: CallbackQuery) -> None:
    text, keyboard = help_view()
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data.startswith(DOC_PREFIX))
async def cb_doc(callback: CallbackQuery) -> None:
    doc = await _find_doc(callback.data.removeprefix(DOC_PREFIX))
    if doc is None:
        await callback.answer("Документ не найден — список обновлён.")
        await _show_docs_list(callback)
        return
    text, keyboard = doc_view(doc)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data.startswith(ASK_DELETE_PREFIX))
async def cb_ask_delete(callback: CallbackQuery) -> None:
    doc = await _find_doc(callback.data.removeprefix(ASK_DELETE_PREFIX))
    if doc is None:
        await callback.answer("Документ не найден — список обновлён.")
        await _show_docs_list(callback)
        return
    text, keyboard = confirm_delete_view(doc)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@admin_router.callback_query(F.data.startswith(DELETE_PREFIX))
async def cb_delete(callback: CallbackQuery) -> None:
    await rag_service.delete_document(callback.data.removeprefix(DELETE_PREFIX))
    await callback.answer("🗑 Документ удалён")
    await _show_docs_list(callback)
