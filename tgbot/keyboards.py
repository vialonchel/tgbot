import re

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tgbot.config import (
    ALL_THEME_CATEGORIES,
    BOT_USERNAME,
    CHANNEL_USERNAME,
    LANG_PER_PAGE,
    THEMES_PER_PAGE,
)
from tgbot.storage import ALL_LANG_CATEGORIES, languages_db
from tgbot.theme_utils import get_themes_page_data


def sticker_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📂 Мои стикерпаки", callback_data="stickers_my"),
                InlineKeyboardButton(text="✂️ Создать стикеры", callback_data="stickers_create"),
            ],
            [InlineKeyboardButton(text="🎲 Случайный стикерпак", callback_data="stickers_random")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="back_menu")],
        ]
    )


def make_sticker_pack_name(user_id: int, seq: int) -> str:
    return f"u{user_id}_{seq}_by_{BOT_USERNAME.lower()}"


def parse_pack_name(pack: dict) -> str | None:
    raw_name = str(pack.get("name", "")).strip()
    if raw_name:
        return raw_name
    link = str(pack.get("link", "")).strip()
    if not link:
        return None
    m = re.search(r"(?:https?://)?(?:t\\.me|telegram\\.me)/addstickers/([A-Za-z0-9_]+)", link)
    if m:
        return m.group(1)
    m = re.search(r"^addstickers/([A-Za-z0-9_]+)$", link)
    if m:
        return m.group(1)
    return None


def pack_install_link(pack: dict, pack_name: str) -> str:
    link = str(pack.get("link", "")).strip()
    if link.startswith("http://") or link.startswith("https://"):
        return link
    if link.startswith("t.me/") or link.startswith("telegram.me/"):
        return f"https://{link}"
    return f"https://t.me/addstickers/{pack_name}"


def random_sticker_keyboard(install_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📥 Установить", url=install_url),
                InlineKeyboardButton(text="▶️ Вперед", callback_data="stickers_random_next"),
            ],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="back_menu")],
        ]
    )


def video_note_request_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить", callback_data="video_note_cancel")]]
    )


def theme_photo_wait_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить", callback_data="make_theme_photo_cancel")]]
    )


def video_note_result_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="➡️ Кружок из видео", url=f"https://t.me/{BOT_USERNAME}")]]
    )


def font_wait_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить", callback_data="font_cancel")]])


def font_styles_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="абв 𝐴𝑏𝑐", callback_data="font_pick_math_italic"),
                InlineKeyboardButton(text="абв 𝐀𝐛𝐜", callback_data="font_pick_math_bold"),
            ],
            [
                InlineKeyboardButton(text="абв 𝑨𝒃𝒄", callback_data="font_pick_math_bold_italic"),
                InlineKeyboardButton(text="абв 𝖠𝖻𝖼", callback_data="font_pick_sans"),
            ],
            [
                InlineKeyboardButton(text="абв 𝗔𝗯𝗰", callback_data="font_pick_sans_bold"),
                InlineKeyboardButton(text="абв 𝘈𝘣𝘤", callback_data="font_pick_sans_italic"),
            ],
            [
                InlineKeyboardButton(text="абв 𝘼𝗯𝗰", callback_data="font_pick_sans_bold_italic"),
                InlineKeyboardButton(text="абв 𝙰𝚋𝚌", callback_data="font_pick_monospace"),
            ],
            [
                InlineKeyboardButton(text="абв 𝔸𝕓𝕔", callback_data="font_pick_double_struck"),
                InlineKeyboardButton(text="абв Ａｂｃ", callback_data="font_pick_fullwidth"),
            ],
            [
                InlineKeyboardButton(text="абв ⓐⓑⓒ", callback_data="font_pick_circled"),
                InlineKeyboardButton(text="абв x͛͑̓y̽̒̚z͌̕", callback_data="font_pick_combining_glitch"),
            ],
            [
                InlineKeyboardButton(text="абв 𝒻𝒽𝓂", callback_data="font_pick_script"),
                InlineKeyboardButton(text="абв t̅k̅h̅", callback_data="font_pick_overline"),
            ],
            [
                InlineKeyboardButton(text="абв l̲k̲j̲", callback_data="font_pick_underline"),
                InlineKeyboardButton(text="абв j̶k̶n̶", callback_data="font_pick_strikethrough"),
            ],
            [InlineKeyboardButton(text="абв 🄳🄶🄽", callback_data="font_pick_squared")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="font_cancel")],
        ]
    )


def subscribe_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")],
        ]
    )


def menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎨 Темки", callback_data="themes"),
                InlineKeyboardButton(text="🗣️ Язычки", callback_data="languages"),
                InlineKeyboardButton(text="🧩 Стикеры", callback_data="stickers"),
            ],
            [InlineKeyboardButton(text="🎬 Кружок из видео", callback_data="video_note_menu")],
            [InlineKeyboardButton(text="🖼️ Сделать тему из фото", callback_data="make_theme_photo")],
            [InlineKeyboardButton(text="🔤 Изменить шрифт", callback_data="font_menu")],
            [InlineKeyboardButton(text="❓ F.A.Q", url="https://telegra.ph/Otvety-na-voprosy-02-15-3")],
        ]
    )


def admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📤 Сделать рассылку", callback_data="start_broadcast")],
            [InlineKeyboardButton(text="📣 Кампании", callback_data="campaigns")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_menu")],
        ]
    )


def device_keyboard(prefix: str = "device_"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📱 iOS", callback_data=f"{prefix}ios"),
                InlineKeyboardButton(text="🤖 Android", callback_data=f"{prefix}android"),
                InlineKeyboardButton(text="💻 Windows", callback_data=f"{prefix}windows"),
            ],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="back_menu")],
        ]
    )


def categories_keyboard(device: str, page: int = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    total = len(ALL_THEME_CATEGORIES)
    start = page * THEMES_PER_PAGE
    end = min(start + THEMES_PER_PAGE, total)
    page_cats = ALL_THEME_CATEGORIES[start:end]
    for i in range(0, len(page_cats), 3):
        row = [
            InlineKeyboardButton(text=f"🗂️ {name}", callback_data=f"category_{device}_{slug}")
            for name, slug in page_cats[i : i + 3]
        ]
        kb.row(*row)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"cat_page_{device}_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page+1}/{(total // THEMES_PER_PAGE) + 1}", callback_data="noop"))
    if end < total:
        nav.append(InlineKeyboardButton(text="▶️ Вперед", callback_data=f"cat_page_{device}_{page+1}"))
    kb.row(*nav)
    kb.row(InlineKeyboardButton(text="🎲 Рандомная тема", callback_data=f"random_theme_{device}"))
    kb.row(InlineKeyboardButton(text="🏠 В меню", callback_data="back_menu"))
    return kb.as_markup()


def themes_keyboard_for_category(device: str, category_slug: str, page: int = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    page_data, _ = get_themes_page_data(device, category_slug, page)
    if not page_data:
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Категория не найдена", callback_data=f"back_to_categories_{device}")]]
        )

    page = page_data["page"]
    total_pages = page_data["total_pages"]
    current_theme = page_data["current_theme"]
    kb.row(InlineKeyboardButton(text="📥 Установить", callback_data=f"install|{device}|{category_slug}|{current_theme}"))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"theme_page|{device}|{category_slug}|{page-1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️ Вперед", callback_data=f"theme_page|{device}|{category_slug}|{page+1}"))
    kb.row(*nav)

    kb.row(InlineKeyboardButton(text="📚 ⬅️ К категориям", callback_data=f"back_to_categories_{device}"))
    kb.row(InlineKeyboardButton(text="🏠 В меню", callback_data="back_menu"))
    return kb.as_markup()


def languages_categories_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    total = len(ALL_LANG_CATEGORIES)
    start = page * LANG_PER_PAGE
    end = min(start + LANG_PER_PAGE, total)
    page_cats = ALL_LANG_CATEGORIES[start:end]
    for i in range(0, len(page_cats), 3):
        row = [
            InlineKeyboardButton(text=f"🗂️ {cat['name']}", callback_data=f"lang_category_{cat['slug']}")
            for cat in page_cats[i : i + 3]
        ]
        kb.row(*row)

    nav = []
    total_pages = max(1, (total + LANG_PER_PAGE - 1) // LANG_PER_PAGE)
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"lang_cat_page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page+1}/{total_pages}", callback_data="noop"))
    if end < total:
        nav.append(InlineKeyboardButton(text="▶️ Вперед", callback_data=f"lang_cat_page_{page+1}"))
    kb.row(*nav)
    kb.row(InlineKeyboardButton(text="🎲 Рандомный язык", callback_data="random_language"))
    kb.row(InlineKeyboardButton(text="🏠 В меню", callback_data="back_menu"))
    return kb.as_markup()


def languages_pagination_keyboard(category_slug: str, page: int = 0) -> InlineKeyboardMarkup:
    category = next((cat for cat in languages_db["categories"] if cat["slug"] == category_slug), None)
    if not category:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Категория не найдена", callback_data="languages")]])
    langs = category["languages"]
    total = len(langs)
    if total == 0:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Языки не найдены", callback_data="languages")]])
    page = max(0, min(page, total - 1))
    current_lang = langs[page]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📥 Установить", url=current_lang["link"]))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"lang_page_{category_slug}_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page+1}/{total}", callback_data="noop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton(text="▶️ Вперед", callback_data=f"lang_page_{category_slug}_{page+1}"))
    kb.row(*nav)
    kb.row(InlineKeyboardButton(text="📚 ⬅️ К категориям", callback_data="languages"))
    kb.row(InlineKeyboardButton(text="🏠 В меню", callback_data="back_menu"))
    return kb.as_markup()


def bot_link_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💋Бот с темками 👉", url="https://t.me/TT_temki_bot")]])
