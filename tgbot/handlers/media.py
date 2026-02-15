import asyncio
import os
import random

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from tgbot.config import REPEAT_MENU_TEXT
from tgbot.font_utils import apply_font_style
from tgbot.keyboards import (
    font_styles_keyboard,
    font_wait_keyboard,
    menu_keyboard,
    video_note_request_keyboard,
    video_note_result_keyboard,
)
from tgbot.media_utils import convert_video_to_note
from tgbot.runtime import bot
from tgbot.states import FontStates, VideoNoteStates
from tgbot.storage import db, ensure_user

from .shared import animate_loading, ensure_subscribed, safe_delete_message


router = Router(name="media_handlers")


@router.callback_query(F.data == "video_note_menu")
async def video_note_menu(call: CallbackQuery, state: FSMContext):
    if not await ensure_subscribed(call.from_user.id):
        return
    ensure_user(db, call.from_user)
    await state.set_state(VideoNoteStates.waiting_for_video)
    wait_message = await bot.send_message(
        call.from_user.id,
        "Пришли видео, и я сделаю из него кружок.",
        reply_markup=video_note_request_keyboard(),
    )
    await state.update_data(
        video_note_menu_message_id=call.message.message_id,
        video_note_wait_message_id=wait_message.message_id,
    )
    await call.answer()


@router.callback_query(F.data == "font_menu")
async def font_menu(call: CallbackQuery, state: FSMContext):
    if not await ensure_subscribed(call.from_user.id):
        return
    wait_message = await bot.send_message(
        call.from_user.id,
        "Отправь текст и я изменю его шрифт:",
        reply_markup=font_wait_keyboard(),
    )
    await state.update_data(
        font_menu_message_id=call.message.message_id,
        font_wait_message_id=wait_message.message_id,
        font_source_text=None,
        font_picker_message_id=None,
    )
    await state.set_state(FontStates.waiting_for_text)
    await call.answer()


@router.callback_query(F.data == "font_cancel", FontStates.waiting_for_text)
@router.callback_query(F.data == "font_cancel", FontStates.waiting_for_font_choice)
async def font_cancel(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await safe_delete_message(call.message.chat.id, data.get("font_menu_message_id"))
    await safe_delete_message(call.message.chat.id, data.get("font_wait_message_id"))
    await safe_delete_message(call.message.chat.id, data.get("font_picker_message_id"))

    try:
        await call.message.delete()
    except Exception:
        pass

    await state.clear()
    await bot.send_message(call.from_user.id, REPEAT_MENU_TEXT, reply_markup=menu_keyboard())
    await call.answer()


@router.message(FontStates.waiting_for_text, F.text)
async def receive_text_for_font(message: Message, state: FSMContext):
    if not await ensure_subscribed(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    await safe_delete_message(message.chat.id, data.get("font_menu_message_id"))
    await safe_delete_message(message.chat.id, data.get("font_wait_message_id"))

    picker_message = await bot.send_message(message.from_user.id, "Выбери шрифт:", reply_markup=font_styles_keyboard())
    await state.update_data(font_source_text=message.text, font_picker_message_id=picker_message.message_id)
    await state.set_state(FontStates.waiting_for_font_choice)


@router.message(FontStates.waiting_for_text)
async def receive_text_for_font_invalid(message: Message):
    await message.answer("Пришли обычный текст, который нужно преобразовать.")


@router.callback_query(F.data.startswith("font_pick_"), FontStates.waiting_for_font_choice)
async def apply_font_to_text(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    source_text = data.get("font_source_text")
    if not source_text:
        await state.clear()
        await bot.send_message(call.from_user.id, REPEAT_MENU_TEXT, reply_markup=menu_keyboard())
        await call.answer()
        return
    style_id = call.data.replace("font_pick_", "", 1)
    converted = apply_font_style(source_text, style_id)
    await bot.send_message(call.from_user.id, converted)

    await safe_delete_message(call.message.chat.id, data.get("font_picker_message_id"))
    try:
        await call.message.delete()
    except Exception:
        pass

    await state.clear()
    await bot.send_message(call.from_user.id, REPEAT_MENU_TEXT, reply_markup=menu_keyboard())
    await call.answer()


@router.callback_query(F.data == "video_note_cancel", VideoNoteStates.waiting_for_video)
async def video_note_cancel(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prev_menu_message_id = data.get("video_note_menu_message_id")
    wait_message_id = data.get("video_note_wait_message_id")
    await state.clear()

    new_menu = await bot.send_message(call.from_user.id, REPEAT_MENU_TEXT, reply_markup=menu_keyboard())

    if wait_message_id:
        try:
            await bot.delete_message(call.message.chat.id, int(wait_message_id))
        except Exception:
            pass
    else:
        try:
            await call.message.delete()
        except Exception:
            pass

    if prev_menu_message_id and int(prev_menu_message_id) != int(new_menu.message_id):
        try:
            await bot.delete_message(call.message.chat.id, int(prev_menu_message_id))
        except Exception:
            pass

    await call.answer()


@router.message(VideoNoteStates.waiting_for_video, F.video | F.document)
async def process_video_note_source(message: Message, state: FSMContext):
    if not await ensure_subscribed(message.from_user.id):
        await state.clear()
        return

    uid = str(message.from_user.id)
    input_path = f"video_src_{uid}_{random.randint(1000, 9999)}.mp4"
    output_path = f"video_note_{uid}_{random.randint(1000, 9999)}.mp4"
    loading_message = await message.answer("загрузка.")
    stop_event = asyncio.Event()
    animation_task = asyncio.create_task(animate_loading(loading_message, stop_event))

    try:
        file = None
        if message.video:
            file = await bot.get_file(message.video.file_id)
        elif message.document:
            mime = (message.document.mime_type or "").lower()
            if not mime.startswith("video/"):
                await message.answer("Пришли видео (не изображение и не архив).")
                return
            file = await bot.get_file(message.document.file_id)

        if not file:
            await message.answer("Пришли видео.")
            return

        await bot.download_file(file.file_path, input_path)
        convert_video_to_note(input_path, output_path)

        await bot.send_video_note(
            chat_id=message.from_user.id,
            video_note=FSInputFile(output_path),
            reply_markup=video_note_result_keyboard(),
        )
        await state.clear()
        await bot.send_message(message.from_user.id, REPEAT_MENU_TEXT, reply_markup=menu_keyboard())
    except FileNotFoundError:
        await message.answer("Не найден ffmpeg. Добавь его в Railway сборку.")
    except Exception:
        await message.answer("Не удалось сделать кружок из этого видео. Попробуй другое.")
    finally:
        stop_event.set()
        try:
            await animation_task
        except Exception:
            pass
        try:
            await loading_message.delete()
        except Exception:
            pass
        for path in (input_path, output_path):
            if os.path.exists(path):
                os.remove(path)


@router.message(VideoNoteStates.waiting_for_video)
async def process_video_note_source_invalid(message: Message):
    await message.answer("Пришли видео файлом или обычным видео сообщением.")
