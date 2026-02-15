import random

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from tgbot.keyboards import languages_categories_keyboard, languages_pagination_keyboard
from tgbot.runtime import bot
from tgbot.storage import SLUG_TO_LANG_CATEGORY, languages_db

from .shared import ensure_subscribed


router = Router(name="language_handlers")


@router.message(Command("randomlanguage"))
async def random_language(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда работает только в группах.")
        return
    if not await ensure_subscribed(message.from_user.id):
        await message.answer("❣️ Подпишись на канал для использования команды.")
        return
    categories = languages_db["categories"]
    if not categories:
        await message.answer("❌ Нет языков")
        return
    category = random.choice(categories)
    langs = category["languages"]
    if not langs:
        await message.answer("❌ Нет языков в категории")
        return
    lang = random.choice(langs)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📥 Установить", url=lang["link"])]] )
    await message.answer(f"Случайный язык: {lang['name']}", reply_markup=kb)


@router.callback_query(F.data == "languages")
async def choose_language_category(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    await call.message.edit_text("Выбери категорию языков:", reply_markup=languages_categories_keyboard())


@router.callback_query(F.data.startswith("lang_cat_page_"))
async def paginate_languages_categories(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    page = int(call.data.replace("lang_cat_page_", ""))
    await call.message.edit_text("Выбери категорию языков:", reply_markup=languages_categories_keyboard(page))


@router.callback_query(F.data.startswith("lang_category_"))
async def select_language_category(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    slug = call.data.replace("lang_category_", "")
    category_name = SLUG_TO_LANG_CATEGORY.get(slug)
    if not category_name:
        await call.answer("❌ Категория не найдена")
        return
    page = 0
    current_lang = next((cat for cat in languages_db["categories"] if cat["slug"] == slug), None)["languages"][page]
    description = current_lang.get("description", "")
    await call.message.edit_text(
        f"🎨 {category_name}: {current_lang['name']}\n{description}",
        reply_markup=languages_pagination_keyboard(slug, page),
    )


@router.callback_query(F.data.startswith("lang_page_"))
async def paginate_languages(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    parts = call.data.split("_")
    slug = parts[2]
    page = int(parts[3])
    category_name = SLUG_TO_LANG_CATEGORY.get(slug)
    current_lang = next((cat for cat in languages_db["categories"] if cat["slug"] == slug), None)["languages"][page]
    description = current_lang.get("description", "")
    await call.message.edit_text(
        f"🎨 {category_name}: {current_lang['name']}\n{description}",
        reply_markup=languages_pagination_keyboard(slug, page),
    )


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()


@router.callback_query(F.data == "random_language")
async def random_language_callback(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    categories = languages_db["categories"]
    if not categories:
        await call.answer("❌ Нет языков")
        return
    category = random.choice(categories)
    langs = category["languages"]
    if not langs:
        await call.answer("❌ Нет языков в категории")
        return

    lang = random.choice(langs)
    description = lang.get("description", "")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📥 Установить", url=lang["link"])]] )
    await bot.send_message(call.from_user.id, f"Случайный язык: {lang['name']}\n{description}", reply_markup=kb)
    try:
        await call.message.delete()
    except Exception:
        pass
    await bot.send_message(call.from_user.id, "Выбери категорию языков:", reply_markup=languages_categories_keyboard())
    await call.answer()
