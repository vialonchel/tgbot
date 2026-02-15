import os
import random

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from tgbot.keyboards import make_sticker_pack_name, sticker_menu_keyboard
from tgbot.media_utils import build_sticker_png, extract_sticker_pack_title
from tgbot.runtime import bot
from tgbot.states import StickerStates
from tgbot.storage import db, ensure_user

from .shared import (
    add_sticker_to_pack,
    create_sticker_set,
    ensure_subscribed,
    register_sticker_pack,
    send_random_sticker_from_catalog,
)


router = Router(name="sticker_handlers")


@router.callback_query(F.data == "stickers")
async def stickers_menu(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    ensure_user(db, call.from_user)
    await call.message.edit_text("Стикеры:", reply_markup=sticker_menu_keyboard())


@router.callback_query(F.data == "stickers_my")
async def stickers_my(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    uid = ensure_user(db, call.from_user)
    packs = db["users"][uid].get("sticker_packs", [])
    if not packs:
        await call.answer("У тебя пока нет стикерпаков", show_alert=True)
        return
    links = [f"https://t.me/addstickers/{name}" for name in packs]
    text = "Твои стикерпаки:\n\n" + "\n".join(links)
    await call.message.edit_text(text, reply_markup=sticker_menu_keyboard())


@router.callback_query(F.data == "stickers_random")
async def stickers_random(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    sent = await send_random_sticker_from_catalog(call.from_user.id)
    if not sent:
        await call.answer("Добавь стикерпаки в stickerpacks.json", show_alert=True)
        return
    await call.answer()


@router.callback_query(F.data == "stickers_random_next")
async def stickers_random_next(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    try:
        await call.message.delete()
    except Exception:
        pass
    sent = await send_random_sticker_from_catalog(call.from_user.id)
    if not sent:
        await bot.send_message(call.from_user.id, "Добавь стикерпаки в stickerpacks.json")
    await call.answer()


@router.callback_query(F.data == "stickers_create")
async def stickers_create(call: CallbackQuery, state: FSMContext):
    if not await ensure_subscribed(call.from_user.id):
        return
    ensure_user(db, call.from_user)
    await call.message.edit_text(
        "Пришли фото или файл изображения, и я сделаю из него стикер.\n\n"
        "Если хочешь, сначала отправь текст:\nНазвание: Мой пак",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data="back_menu")]]),
    )
    await state.update_data(sticker_wait_message_id=call.message.message_id, sticker_pack_title=None)
    await state.set_state(StickerStates.waiting_for_source)
    await call.answer()


@router.message(StickerStates.waiting_for_source, F.photo | F.document)
async def process_sticker_source(message: Message, state: FSMContext):
    if not await ensure_subscribed(message.from_user.id):
        await state.clear()
        return

    uid = ensure_user(db, message.from_user)
    user_data = db["users"][uid]
    state_data = await state.get_data()
    source_path = f"sticker_src_{uid}_{random.randint(1000, 9999)}"
    png_path = f"sticker_{uid}_{random.randint(1000, 9999)}.png"

    try:
        if message.photo:
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)
            await bot.download_file(file.file_path, source_path)
        elif message.document:
            mime = message.document.mime_type or ""
            if not mime.startswith("image/"):
                await message.answer("Нужен файл изображения (jpg/png/webp).")
                return
            file = await bot.get_file(message.document.file_id)
            await bot.download_file(file.file_path, source_path)
        else:
            await message.answer("Пришли фото или файл изображения.")
            return

        build_sticker_png(source_path, png_path)

        custom_title = state_data.get("sticker_pack_title")
        caption_title = extract_sticker_pack_title(getattr(message, "caption", None))
        if caption_title:
            custom_title = caption_title

        packs = user_data.get("sticker_packs", [])
        pack_name = None if custom_title else (packs[-1] if packs else None)
        added_to_existing = False

        if pack_name:
            try:
                await add_sticker_to_pack(message.from_user.id, pack_name, png_path)
                added_to_existing = True
            except Exception:
                pack_name = None

        if not pack_name:
            user_data["sticker_pack_seq"] = user_data.get("sticker_pack_seq", 0) + 1
            seq = user_data["sticker_pack_seq"]
            pack_name = make_sticker_pack_name(message.from_user.id, seq)
            pack_title = custom_title or f"Стикеры {message.from_user.first_name} #{seq}"
            await create_sticker_set(message.from_user.id, pack_name, pack_title, png_path)
            register_sticker_pack(uid, pack_name, pack_title)
            status_text = "✅ Создал новый стикерпак и добавил стикер:"
        else:
            status_text = "✅ Добавил стикер в твой стикерпак:" if added_to_existing else "✅ Добавил стикер:"

        wait_message_id = state_data.get("sticker_wait_message_id")
        if wait_message_id:
            try:
                await bot.delete_message(message.chat.id, int(wait_message_id))
            except Exception:
                pass
        await message.answer(f"{status_text}\nhttps://t.me/addstickers/{pack_name}")
        await message.answer("Стикеры:", reply_markup=sticker_menu_keyboard())
        await state.clear()
    except Exception:
        await message.answer("Не удалось сделать стикер. Пришли другое изображение.")
    finally:
        for path in (source_path, png_path):
            if os.path.exists(path):
                os.remove(path)


@router.message(StickerStates.waiting_for_source, F.text)
async def set_sticker_pack_title(message: Message, state: FSMContext):
    title = extract_sticker_pack_title(message.text)
    if not title:
        await message.answer("Напиши так: Название: Мой пак")
        return
    await state.update_data(sticker_pack_title=title)
    await message.answer(f"✅ Название сохранено: {title}\nТеперь пришли фото или файл изображения.")


@router.message(StickerStates.waiting_for_source)
async def process_sticker_source_invalid(message: Message):
    await message.answer("Пришли фото или файл изображения (jpg/png/webp).")
