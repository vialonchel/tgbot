import asyncio
import os
import random
import zipfile

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from tgbot.config import CATEGORIES, REPEAT_MENU_TEXT, SLUG_TO_CATEGORY
from tgbot.keyboards import categories_keyboard, device_keyboard, menu_keyboard, theme_photo_wait_keyboard
from tgbot.media_utils import build_attheme_with_wallpaper, build_wallpaper_jpg
from tgbot.runtime import bot
from tgbot.states import CustomThemeStates, RandomThemeStates
from tgbot.theme_utils import find_theme_preview, is_theme_file, resolve_device_folder, resolve_theme_file, theme_extension

from .shared import ensure_subscribed, replace_message_with_text, show_theme_page


router = Router(name="theme_handlers")


@router.message(Command("randomtheme"))
async def random_theme(message: Message, state: FSMContext):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда работает только в группах.")
        return
    if not await ensure_subscribed(message.from_user.id):
        await message.answer("❣️ Подпишись на канал для использования команды.")
        return
    await message.answer("С какого девайса? Выбери:", reply_markup=device_keyboard("random_"))
    await state.set_state(RandomThemeStates.waiting_for_device)


@router.callback_query(F.data.startswith("random_"), RandomThemeStates.waiting_for_device)
async def process_random_theme_device(call: CallbackQuery, state: FSMContext):
    device = call.data.replace("random_", "")
    category_row = random.choice(CATEGORIES)
    _, category_slug = random.choice(category_row)
    category = SLUG_TO_CATEGORY[category_slug]
    folder = os.path.join(resolve_device_folder(device), category)
    if not os.path.exists(folder):
        await call.message.edit_text("❌ Темы не найдены")
        await state.clear()
        return
    themes = [f for f in os.listdir(folder) if not f.startswith(".") and is_theme_file(f, device)]
    if not themes:
        await call.message.edit_text("❌ Темы не найдены")
        await state.clear()
        return
    theme_file = random.choice(themes)
    filename_no_ext = os.path.splitext(theme_file)[0]
    preview_file = find_theme_preview(folder, filename_no_ext)
    theme_path = resolve_theme_file(folder, filename_no_ext, device)
    if preview_file:
        await bot.send_photo(call.from_user.id, photo=FSInputFile(preview_file), caption="📌 Предпросмотр случайной темы")
    if theme_path and os.path.exists(theme_path):
        output_name = f"{filename_no_ext}{theme_extension(device)}"
        await bot.send_document(
            call.from_user.id,
            document=FSInputFile(theme_path, filename=output_name),
            caption="Нажми для установки случайной темы!\n\nТема создана в @TT_temki_bot 😉",
        )
    else:
        await call.answer("❌ Файл темы не найден", show_alert=True)
    await state.clear()


@router.message(F.photo & F.caption.startswith("/bg"))
async def set_bg(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    temp_photo = "temp_bg.jpg"
    await bot.download_file(file.file_path, temp_photo)
    await state.update_data(photo_path=temp_photo)
    device_msg = await message.answer("На каком устройстве установить тему?", reply_markup=device_keyboard("bg_"))
    await state.update_data(bg_device_message_id=device_msg.message_id)
    await state.set_state(CustomThemeStates.waiting_for_device)


@router.callback_query(F.data == "make_theme_photo")
async def make_theme_photo(call: CallbackQuery, state: FSMContext):
    if not await ensure_subscribed(call.from_user.id):
        await call.answer("❣️ Подпишись на канал для использования.")
        return
    wait_message = await call.message.answer("Пришли фото для темы:", reply_markup=theme_photo_wait_keyboard())
    await state.update_data(
        theme_photo_wait_message_id=wait_message.message_id,
        theme_photo_menu_message_id=call.message.message_id,
    )
    await state.set_state(CustomThemeStates.waiting_for_photo)
    await call.answer()


@router.callback_query(F.data == "make_theme_photo_cancel", CustomThemeStates.waiting_for_photo)
async def make_theme_photo_cancel(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    menu_message_id = data.get("theme_photo_menu_message_id")

    if menu_message_id:
        try:
            await bot.delete_message(call.message.chat.id, int(menu_message_id))
        except Exception:
            pass

    try:
        await call.message.delete()
    except Exception:
        pass

    await state.clear()
    await bot.send_message(call.from_user.id, REPEAT_MENU_TEXT, reply_markup=menu_keyboard())
    await call.answer()


@router.message(F.photo, CustomThemeStates.waiting_for_photo)
async def receive_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    wait_message_id = data.get("theme_photo_wait_message_id")
    menu_message_id = data.get("theme_photo_menu_message_id")

    for msg_id in (wait_message_id, menu_message_id):
        if msg_id:
            try:
                await bot.delete_message(message.chat.id, int(msg_id))
            except Exception:
                pass

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    temp_photo = "temp_bg.jpg"
    await bot.download_file(file.file_path, temp_photo)
    await state.update_data(photo_path=temp_photo)
    device_msg = await message.answer("На каком устройстве установить тему?", reply_markup=device_keyboard("bg_"))
    await state.update_data(bg_device_message_id=device_msg.message_id)
    await state.set_state(CustomThemeStates.waiting_for_device)


@router.callback_query(F.data.startswith("bg_"), CustomThemeStates.waiting_for_device)
async def process_bg_device(call: CallbackQuery, state: FSMContext):
    device = call.data.replace("bg_", "")
    data = await state.get_data()
    photo_path = data.get("photo_path")
    if not photo_path or not os.path.exists(photo_path):
        await call.answer("Ошибка с фото.")
        await state.clear()
        return
    uid = str(call.from_user.id)
    wallpaper_jpg = f"temp_bg_{uid}.jpg"

    build_wallpaper_jpg(photo_path, wallpaper_jpg)

    if device == "windows":
        theme_file = "custom_bg.tdesktop-theme"
    elif device == "ios":
        theme_file = "custom_bg.tgios-theme"
    else:
        theme_file = "custom_bg.attheme"

    colors_file = None
    if device == "windows":
        colors_file = "colors.tdesktop-theme"
        with open(colors_file, "w", encoding="utf-8") as p:
            p.write("// Generated by bot\n")
        with zipfile.ZipFile(theme_file, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(colors_file, "colors.tdesktop-theme")
            zipf.write(wallpaper_jpg, "background.jpg")
    else:
        build_attheme_with_wallpaper(wallpaper_jpg, theme_file)

    await bot.send_document(call.from_user.id, document=FSInputFile(theme_file), caption="Вот тема с твоим фото на фоне! Установи её.")
    bg_device_message_id = data.get("bg_device_message_id")
    if bg_device_message_id:
        try:
            await bot.delete_message(call.message.chat.id, int(bg_device_message_id))
        except Exception:
            pass
    else:
        try:
            await call.message.delete()
        except Exception:
            pass
    await asyncio.sleep(0.5)
    await bot.send_message(call.from_user.id, REPEAT_MENU_TEXT, reply_markup=menu_keyboard())
    os.remove(photo_path)
    os.remove(wallpaper_jpg)
    if colors_file and os.path.exists(colors_file):
        os.remove(colors_file)
    os.remove(theme_file)
    await state.clear()
    await call.answer()


@router.callback_query(F.data.startswith("device_"))
async def select_device(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    device = call.data.replace("device_", "")
    await call.message.edit_text("Выбери категорию:", reply_markup=categories_keyboard(device))


@router.callback_query(F.data.startswith("cat_page_"))
async def paginate_themes_categories(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    try:
        payload = call.data.replace("cat_page_", "", 1)
        device, page_str = payload.rsplit("_", 1)
        page = int(page_str)
    except (ValueError, IndexError):
        await call.answer("❌ Ошибка пагинации", show_alert=True)
        return
    await call.message.edit_text("Выбери категорию:", reply_markup=categories_keyboard(device, page))


@router.callback_query(F.data.startswith("category_"))
async def select_category(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    _, device, slug = call.data.split("_", 2)
    await show_theme_page(call, device, slug, page=0)


@router.callback_query(F.data.startswith("theme_page|"))
async def paginate_themes_in_category(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    try:
        _, device, slug, page_str = call.data.split("|", 3)
        page = int(page_str)
    except (ValueError, IndexError):
        await call.answer("❌ Ошибка пагинации", show_alert=True)
        return
    await show_theme_page(call, device, slug, page=page)


@router.callback_query(F.data.startswith("back_to_devices_"))
async def back_to_devices(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    device = call.data.replace("back_to_devices_", "")
    await call.message.edit_text("С какого девайса ты?", reply_markup=device_keyboard())


@router.callback_query(F.data.startswith("back_to_categories_"))
async def back_to_categories(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    device = call.data.replace("back_to_categories_", "")
    await replace_message_with_text(call, "Выбери категорию:", categories_keyboard(device))
    await call.answer()


@router.callback_query(F.data == "themes")
async def choose_device(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    await call.message.edit_text("С какого девайса ты?", reply_markup=device_keyboard())


@router.callback_query(F.data.startswith("random_theme_"))
async def random_theme_callback(call: CallbackQuery, state: FSMContext):
    if not await ensure_subscribed(call.from_user.id):
        return
    device = call.data.replace("random_theme_", "")
    category_row = random.choice(CATEGORIES)
    _, category_slug = random.choice(category_row)
    category = SLUG_TO_CATEGORY[category_slug]
    folder = os.path.join(resolve_device_folder(device), category)
    if not os.path.exists(folder):
        await call.answer("❌ Темы не найдены")
        return
    themes = [f for f in os.listdir(folder) if not f.startswith(".") and is_theme_file(f, device)]
    if not themes:
        await call.answer("❌ Темы не найдены")
        return
    theme_file = random.choice(themes)
    filename_no_ext = os.path.splitext(theme_file)[0]
    preview_file = find_theme_preview(folder, filename_no_ext)
    theme_path = resolve_theme_file(folder, filename_no_ext, device)
    if preview_file:
        await bot.send_photo(call.from_user.id, photo=FSInputFile(preview_file), caption="📌 Предпросмотр случайной темы")
    if theme_path and os.path.exists(theme_path):
        output_name = f"{filename_no_ext}{theme_extension(device)}"
        await bot.send_document(
            call.from_user.id,
            document=FSInputFile(theme_path, filename=output_name),
            caption="Нажми для установки случайной темы!\n\nТема создана в @TT_temki_bot 😉",
        )
    else:
        await call.answer("❌ Файл темы не найден", show_alert=True)
        return
    try:
        await call.message.delete()
    except Exception:
        pass
    await bot.send_message(call.from_user.id, "Выбери категорию:", reply_markup=categories_keyboard(device))
    await call.answer()


@router.callback_query(F.data.startswith("install|"))
async def install_theme(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    try:
        _, device, category_slug, filename = call.data.split("|", 3)
    except ValueError:
        await call.answer("❌ Ошибка установки темы", show_alert=True)
        return
    category = SLUG_TO_CATEGORY.get(category_slug)
    if not category:
        await call.answer("❌ Категория не найдена", show_alert=True)
        return
    base_dir = os.path.join(resolve_device_folder(device), category)
    theme_file = resolve_theme_file(base_dir, filename, device)
    if theme_file and os.path.exists(theme_file):
        output_name = f"{filename}{theme_extension(device)}"
        await bot.send_document(
            call.from_user.id,
            document=FSInputFile(theme_file, filename=output_name),
            caption="Нажми для установки!\n\nТема создана в @TT_temki_bot 😉",
        )
    else:
        await call.answer("❌ Файл темы не найден", show_alert=True)
