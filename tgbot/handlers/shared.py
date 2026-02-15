import asyncio
from datetime import datetime, timezone

from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, InputSticker, Message

from tgbot.config import CHANNEL_USERNAME
from tgbot.keyboards import menu_keyboard, pack_install_link, parse_pack_name, random_sticker_keyboard, themes_keyboard_for_category
from tgbot.runtime import bot
from tgbot.storage import db, load_stickerpacks, save_users
from tgbot.theme_utils import get_themes_page_data


async def ensure_subscribed(user_id: int):
    uid = str(user_id)
    if uid in db["users"] and db["users"][uid]["subscribed"]:
        return True
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ("member", "administrator", "creator"):
            if uid not in db["users"]:
                db["users"][uid] = {
                    "first_start": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "subscribed": False,
                    "device": None,
                    "campaign": "organic",
                    "sticker_packs": [],
                    "sticker_pack_seq": 0,
                }
            db["users"][uid]["subscribed"] = True
            save_users(db)
            return True
    except Exception:
        pass
    return False


async def replace_message_with_text(call: CallbackQuery, text: str, markup: InlineKeyboardMarkup):
    try:
        await call.message.edit_text(text, reply_markup=markup)
        return
    except Exception:
        pass
    try:
        await call.message.delete()
    except Exception:
        pass
    await bot.send_message(call.from_user.id, text, reply_markup=markup)


async def show_theme_page(call: CallbackQuery, device: str, category_slug: str, page: int = 0):
    page_data, error_text = get_themes_page_data(device, category_slug, page)
    if error_text:
        await call.answer(error_text, show_alert=True)
        return

    caption = f"🎨 {page_data['category']}\n\n📦 {page_data['current_theme']}"
    markup = themes_keyboard_for_category(device, category_slug, page_data["page"])
    preview_file = page_data["preview_file"]

    try:
        await call.message.delete()
    except Exception:
        pass

    if preview_file:
        await bot.send_photo(
            call.from_user.id,
            photo=FSInputFile(preview_file),
            caption=caption,
            reply_markup=markup,
        )
    else:
        await bot.send_message(
            call.from_user.id,
            text=caption,
            reply_markup=markup,
        )
    await call.answer()


async def safe_delete_message(chat_id: int, message_id: int | None):
    if not message_id:
        return
    try:
        await bot.delete_message(chat_id, int(message_id))
    except Exception:
        pass


def register_sticker_pack(uid: str, name: str, title: str):
    if name not in db["users"][uid]["sticker_packs"]:
        db["users"][uid]["sticker_packs"].append(name)
    if not any(p.get("name") == name for p in db["sticker_packs"]):
        db["sticker_packs"].append({"name": name, "title": title, "owner": uid})
    save_users(db)


async def create_sticker_set(user_id: int, pack_name: str, pack_title: str, png_path: str):
    sticker = InputSticker(sticker=FSInputFile(png_path), emoji_list=["💞"], format="static")
    try:
        await bot.create_new_sticker_set(
            user_id=user_id,
            name=pack_name,
            title=pack_title,
            stickers=[sticker],
            sticker_format="static",
        )
    except TypeError:
        await bot.create_new_sticker_set(
            user_id=user_id,
            name=pack_name,
            title=pack_title,
            stickers=[sticker],
        )


async def add_sticker_to_pack(user_id: int, pack_name: str, png_path: str):
    sticker = InputSticker(sticker=FSInputFile(png_path), emoji_list=["💞"], format="static")
    await bot.add_sticker_to_set(user_id=user_id, name=pack_name, sticker=sticker)


async def send_random_sticker_from_catalog(chat_id: int) -> bool:
    catalog = load_stickerpacks()
    packs = catalog.get("packs", [])
    valid_packs = []
    for pack in packs:
        if not isinstance(pack, dict):
            continue
        pack_name = parse_pack_name(pack)
        if not pack_name:
            continue
        valid_packs.append((pack, pack_name, pack_install_link(pack, pack_name)))

    if not valid_packs:
        return False

    import random

    random.shuffle(valid_packs)
    for pack, pack_name, install_url in valid_packs:
        try:
            sticker_set = await bot.get_sticker_set(pack_name)
            if not sticker_set.stickers:
                continue
            sticker = random.choice(sticker_set.stickers)
            await bot.send_sticker(
                chat_id=chat_id,
                sticker=sticker.file_id,
                reply_markup=random_sticker_keyboard(install_url),
            )
            return True
        except Exception:
            continue
    return False


async def animate_loading(message: Message, stop_event: asyncio.Event):
    dots = [".", "..", "..."]
    idx = 0
    while not stop_event.is_set():
        try:
            await message.edit_text(f"загрузка{dots[idx]}")
        except Exception:
            return
        idx = (idx + 1) % len(dots)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
