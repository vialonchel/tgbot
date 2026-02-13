import asyncio
import random
import json
import os
import base64
import zipfile
from PIL import Image
from datetime import datetime, timezone
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =========================
# Категории тем (flatten для пагинации)
# =========================
CATEGORIES = [
    [("Аниме", "anime"), ("Дед инсайд", "ded_insayd"), ("Котики", "kotiki")],
    [("Милые", "milye"), ("Зимние", "zimnie"), ("Пошлые", "poshlye")],
    [("Кино", "kino"), ("Сердечки", "serdechki"), ("K-Pop", "k_pop")],
    [("Автомобили", "avtomobili"), ("Парные", "parnye")]
]
SLUG_TO_CATEGORY = {slug: name for row in CATEGORIES for name, slug in row}
ALL_THEME_CATEGORIES = [item for sublist in CATEGORIES for item in sublist]  # Плоский список для пагинации
THEMES_PER_PAGE = 9  # 3 ряда по 3

# =========================
# Настройки
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Environment variable BOT_TOKEN is required")
CHANNEL_USERNAME = "@wursix"
USERS_FILE = "users.json"
ADMINS = {913949366}
BOT_USERNAME = "TT_temki_bot"
GROUP_START_IMAGE = "groupstart.jpg"
# =========================
# BOT
# =========================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
# =========================
# FSM
# =========================
class BroadcastStates(StatesGroup):
    waiting_for_message = State()
class CampaignStates(StatesGroup):
    waiting_for_name = State()
class RandomThemeStates(StatesGroup):
    waiting_for_device = State()
class CustomThemeStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_device = State()
# =========================
# ХРАНИЛИЩЕ
# =========================
def load_users():
    if not os.path.exists(USERS_FILE):
        return {"users": {}, "campaigns": ["organic"]}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "users" not in data:
        data["users"] = {}
    if "campaigns" not in data:
        data["campaigns"] = ["organic"]
    return data

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load_users()

def ensure_user(tg_user, campaign="organic"):
    uid = str(tg_user.id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "first_start": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "subscribed": False,
            "device": None,
            "campaign": campaign
        }
        save_users()
    return uid

def load_languages():
    if not os.path.exists("languages.json"):
        return {"categories": []}
    with open("languages.json", "r", encoding="utf-8") as f:
        return json.load(f)

languages_db = load_languages()
SLUG_TO_LANG_CATEGORY = {cat["slug"]: cat["name"] for cat in languages_db["categories"]}
ALL_LANG_CATEGORIES = languages_db["categories"]  # Для пагинации языковых категорий
LANG_PER_PAGE = 9
# =========================
# ПРОВЕРКА ПОДПИСКИ
# =========================
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
                    "campaign": "organic"
                }
            db["users"][uid]["subscribed"] = True
            save_users()
            return True
    except Exception:
        pass
    return False

def theme_extension(device: str) -> str:
    return {"ios": ".tgios-theme", "android": ".attheme", "windows": ".tgdesktop-theme"}.get(device, "")

def resolve_device_folder(device: str) -> str:
    folder = os.path.join("themes", device)
    if os.path.isdir(folder):
        return folder
    if device == "android":
        fallback = os.path.join("themes", "andriod")
        if os.path.isdir(fallback):
            return fallback
    return folder

def find_theme_preview(folder: str, theme_name: str) -> str | None:
    same_name_jpg = os.path.join(folder, f"{theme_name}.jpg")
    legacy_preview = os.path.join(folder, f"{theme_name}_preview.jpg")
    if os.path.exists(same_name_jpg):
        return same_name_jpg
    if os.path.exists(legacy_preview):
        return legacy_preview
    return None
# =========================
# КЛАВИАТУРЫ
# =========================
def subscribe_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")]
    ])
def menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="темки", callback_data="themes"),
            InlineKeyboardButton(text="язычки", callback_data="languages")
        ],
        [InlineKeyboardButton(text="сделать тему из фото", callback_data="make_theme_photo")],
        [InlineKeyboardButton(text="Добавить бота в группу", callback_data="add_to_group")]
    ])
def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📤 Сделать рассылку", callback_data="start_broadcast")],
        [InlineKeyboardButton(text="📣 Кампании", callback_data="campaigns")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_menu")]
    ])
def device_keyboard(prefix: str = "device_"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 iOS", callback_data=f"{prefix}ios"),
            InlineKeyboardButton(text="🤖 Android", callback_data=f"{prefix}android"),
            InlineKeyboardButton(text="💻 Windows", callback_data=f"{prefix}windows")
        ],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_menu")]
    ])
def categories_keyboard(device: str, page: int = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    total = len(ALL_THEME_CATEGORIES)
    start = page * THEMES_PER_PAGE
    end = min(start + THEMES_PER_PAGE, total)
    page_cats = ALL_THEME_CATEGORIES[start:end]
    for i in range(0, len(page_cats), 3):
        row = [InlineKeyboardButton(text=name, callback_data=f"category_{device}_{slug}") for name, slug in page_cats[i:i+3]]
        kb.row(*row)
    kb.row(InlineKeyboardButton(text="рандомная тема", callback_data=f"random_theme_{device}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"cat_page_{device}_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{(total // THEMES_PER_PAGE) + 1}", callback_data="noop"))
    if end < total:
        nav.append(InlineKeyboardButton(text="▶️ Вперед", callback_data=f"cat_page_{device}_{page+1}"))
    kb.row(*nav)
    kb.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="back_menu"))
    kb.row(InlineKeyboardButton(text="Добавить бота в группу", callback_data="add_to_group"))
    return kb.as_markup()
def themes_keyboard_for_category(device: str, category: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    folder = os.path.join(resolve_device_folder(device), category)
    if not os.path.exists(folder):
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Темы не найдены", callback_data=f"back_to_categories_{device}")]])
    ext = theme_extension(device)
    for file in os.listdir(folder):
        if file.startswith(".") or file.endswith("_preview.jpg") or not file.endswith(ext):
            continue
        filename_no_ext = os.path.splitext(file)[0]
        kb.add(InlineKeyboardButton(text=filename_no_ext, callback_data=f"install_{device}_{category}_{filename_no_ext}"))
    kb.add(InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data=f"back_to_categories_{device}"))
    kb.row(InlineKeyboardButton(text="Добавить бота в группу", callback_data="add_to_group"))
    return kb.as_markup()
def languages_categories_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    total = len(ALL_LANG_CATEGORIES)
    start = page * LANG_PER_PAGE
    end = min(start + LANG_PER_PAGE, total)
    page_cats = ALL_LANG_CATEGORIES[start:end]
    for i in range(0, len(page_cats), 3):
        row = [InlineKeyboardButton(text=cat["name"], callback_data=f"lang_category_{cat['slug']}") for cat in page_cats[i:i+3]]
        kb.row(*row)
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"lang_cat_page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{(total // LANG_PER_PAGE) + 1}", callback_data="noop"))
    if end < total:
        nav.append(InlineKeyboardButton(text="▶️ Вперед", callback_data=f"lang_cat_page_{page+1}"))
    kb.row(*nav)
    kb.row(InlineKeyboardButton(text="рандомный язык", callback_data="random_language"))
    kb.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="back_menu"))
    kb.row(InlineKeyboardButton(text="Добавить бота в группу", callback_data="add_to_group"))
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
    kb.row(InlineKeyboardButton(text="Установить", url=current_lang["link"]))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"lang_page_{category_slug}_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total}", callback_data="noop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton(text="▶️ Вперед", callback_data=f"lang_page_{category_slug}_{page+1}"))
    kb.row(*nav)
    kb.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="back_menu"))
    kb.row(InlineKeyboardButton(text="Добавить бота в группу", callback_data="add_to_group"))
    return kb.as_markup()
def bot_link_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💋Бот с темками 👉", url="https://t.me/TT_temki_bot")]
    ])
def add_group_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить бота в группу", url="https://t.me/TT_temki_bot?startgroup&admin=post_messages+delete_messages")]
    ])
# =========================
# ОБРАБОТЧИКИ
# =========================
@dp.message(Command("start"))
async def start(message: Message):
    args = message.text.split(maxsplit=1)
    if message.chat.type in ("group", "supergroup"):
        if len(args) > 1 and args[1] == "temki":
            await message.answer(
                "У меня есть команды которые ты можешь использовать в групповом чате 😋 \n\nМои команды:\n/randomtheme - 🔖 Рандомная тема\n/randomlanguage - 📝 Рандомный язык",
                reply_markup=bot_link_keyboard()
            )
        return
    
    campaign = args[1] if len(args) > 1 else "organic"
    if campaign not in db["campaigns"]:
        campaign = "organic"
    ensure_user(message.from_user, campaign)
    await message.answer(f"Привет, {message.from_user.first_name}!")
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, message.from_user.id)
        is_subscribed = member.status in ("member", "administrator", "creator")
    except Exception:
        is_subscribed = False
    if is_subscribed:
        db["users"][str(message.from_user.id)]["subscribed"] = True
        save_users()
        await message.answer("😋 Выбери нужное:", reply_markup=menu_keyboard())
    else:
        await message.answer("❣️ Подпишись:", reply_markup=subscribe_keyboard())
    await message.delete()

@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id not in ADMINS:
        return
    await message.answer("выбери:", reply_markup=admin_keyboard())

@dp.message(Command("randomtheme"))
async def random_theme(message: Message, state: FSMContext):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда работает только в группах.")
        return
    if not await ensure_subscribed(message.from_user.id):
        await message.answer("❣️ Подпишись на канал для использования команды.")
        return
    await message.answer("С какого девайса? Выбери:", reply_markup=device_keyboard("random_"))
    await state.set_state(RandomThemeStates.waiting_for_device)

@dp.callback_query(F.data.startswith("random_"), RandomThemeStates.waiting_for_device)
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
    ext = theme_extension(device)
    themes = [f for f in os.listdir(folder) if not f.startswith(".") and f.endswith(ext)]
    if not themes:
        await call.message.edit_text("❌ Темы не найдены")
        await state.clear()
        return
    theme_file = random.choice(themes)
    filename_no_ext = os.path.splitext(theme_file)[0]
    preview_file = find_theme_preview(folder, filename_no_ext)
    theme_path = os.path.join(folder, f"{filename_no_ext}{ext}")
    if preview_file:
        await bot.send_photo(call.from_user.id, photo=FSInputFile(preview_file), caption="📌 Предпросмотр случайной темы")
    if os.path.exists(theme_path):
        await bot.send_document(call.from_user.id, document=FSInputFile(theme_path),
                                caption="Нажми для установки случайной темы!\n\nТема создана в @TT_temki_bot 😉")
    else:
        await call.answer("❌ Файл темы не найден", show_alert=True)
    await state.clear()

@dp.message(Command("randomlanguage"))
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
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить", url=lang["link"])]
    ])
    await message.answer(f"Случайный язык: {lang['name']}", reply_markup=kb)

@dp.message(F.photo & F.caption.startswith("/bg"))
async def set_bg(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    temp_photo = "temp_bg.jpg"
    await bot.download_file(file.file_path, temp_photo)
    await state.update_data(photo_path=temp_photo)
    await message.answer("На каком устройстве установить тему?", reply_markup=device_keyboard("bg_"))
    await state.set_state(CustomThemeStates.waiting_for_device)

@dp.callback_query(F.data == "make_theme_photo")
async def make_theme_photo(call: CallbackQuery, state: FSMContext):
    if not await ensure_subscribed(call.from_user.id):
        await call.answer("❣️ Подпишись на канал для использования.")
        return
    await call.message.answer("Пришли фото для темы.")
    await state.set_state(CustomThemeStates.waiting_for_photo)
    await call.answer()

@dp.message(F.photo, CustomThemeStates.waiting_for_photo)
async def receive_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    temp_photo = "temp_bg.jpg"
    await bot.download_file(file.file_path, temp_photo)
    await state.update_data(photo_path=temp_photo)
    await message.answer("На каком устройстве установить тему?", reply_markup=device_keyboard("bg_"))
    await state.set_state(CustomThemeStates.waiting_for_device)

@dp.callback_query(F.data.startswith("bg_"), CustomThemeStates.waiting_for_device)
async def process_bg_device(call: CallbackQuery, state: FSMContext):
    device = call.data.replace("bg_", "")
    data = await state.get_data()
    photo_path = data.get("photo_path")
    if not photo_path or not os.path.exists(photo_path):
        await call.answer("Ошибка с фото.")
        await state.clear()
        return
    # Конвертируем в PNG для base64
    png_path = "temp_bg.png"
    with Image.open(photo_path) as img:
        img.save(png_path, "PNG")
    with open(png_path, "rb") as f:
        bg_base64 = base64.b64encode(f.read()).decode("utf-8")
    theme_file = f"custom_bg{theme_extension(device) or '.attheme'}"
    if device == "windows":
        # Для desktop - zip с background.jpg и palette.tdesktop-palette (пустой)
        palette_content = ""  # Пустая палитра
        with open("palette.tdesktop-palette", "w") as p:
            p.write(palette_content)
        with zipfile.ZipFile(theme_file, "w") as zipf:
            zipf.write("temp_bg.jpg", "background.jpg")
            zipf.write("palette.tdesktop-palette", "tiled.png")  # Или background.jpg, but for wallpaper
        os.remove("palette.tdesktop-palette")
    else:
        # Для Android/iOS - text with wallpaper base64
        theme_content = f"wallPaper={bg_base64}\n"
        with open(theme_file, "w") as f:
            f.write(theme_content)
    
    await bot.send_document(call.from_user.id, document=FSInputFile(theme_file),
                            caption="Вот тема с твоим фото на фоне! Установи её.")
    await asyncio.sleep(0.5)
    await bot.send_message(call.from_user.id, "😋 Выбери нужное:", reply_markup=menu_keyboard())
    os.remove(photo_path)
    os.remove(png_path)
    os.remove(theme_file)
    await state.clear()
    await call.answer()

# =========================
# CALLBACKS
# =========================
@dp.callback_query(F.data == "add_to_group")
async def show_group_info(call: CallbackQuery):
    await bot.send_photo(
        call.from_user.id,
        photo=FSInputFile(GROUP_START_IMAGE),
        caption="Отправь в чат картинку с подписью \"/bg\" и я сделаю из нее фон для твоего Telegram или переходи в бот, там много интересного😉.",
        reply_markup=add_group_keyboard()
    )
    await bot.send_message(
        call.from_user.id,
        "У меня есть команды которые ты можешь использовать здесь 😋 Мои команды:\n/randomtheme - 🔖 Рандомная тема\n/randomlanguage - 📝 Рандомный язык",
        reply_markup=add_group_keyboard()
    )
    await call.answer()

@dp.callback_query(F.data == "back_menu")
async def back_menu(call: CallbackQuery):
    await call.message.edit_text("😋 Выбери нужное:", reply_markup=menu_keyboard())

@dp.callback_query(F.data.startswith("device_"))
async def select_device(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    device = call.data.replace("device_", "")
    await call.message.edit_text("Выбери категорию:", reply_markup=categories_keyboard(device))

@dp.callback_query(F.data.startswith("cat_page_"))
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

@dp.callback_query(F.data.startswith("category_"))
async def select_category(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    _, device, slug = call.data.split("_", 2)
    category = SLUG_TO_CATEGORY.get(slug)
    if not category:
        await call.answer("❌ Категория не найдена")
        return
    await call.message.edit_text(f"🎨 {category}:", reply_markup=themes_keyboard_for_category(device, category))

@dp.callback_query(F.data.startswith("back_to_devices_"))
async def back_to_devices(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    device = call.data.replace("back_to_devices_", "")
    await call.message.edit_text("С какого девайса ты?", reply_markup=device_keyboard())

@dp.callback_query(F.data.startswith("back_to_categories_"))
async def back_to_categories(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    device = call.data.replace("back_to_categories_", "")
    await call.message.edit_text("Выбери категорию:", reply_markup=categories_keyboard(device))

@dp.callback_query(F.data == "themes")
async def choose_device(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    await call.message.edit_text("С какого девайса ты?", reply_markup=device_keyboard())

@dp.callback_query(F.data.startswith("random_theme_"))
async def random_theme_callback(call: CallbackQuery, state: FSMContext):
    device = call.data.replace("random_theme_", "")
    category_row = random.choice(CATEGORIES)
    _, category_slug = random.choice(category_row)
    category = SLUG_TO_CATEGORY[category_slug]
    folder = os.path.join(resolve_device_folder(device), category)
    if not os.path.exists(folder):
        await call.answer("❌ Темы не найдены")
        return
    ext = theme_extension(device)
    themes = [f for f in os.listdir(folder) if not f.startswith(".") and f.endswith(ext)]
    if not themes:
        await call.answer("❌ Темы не найдены")
        return
    theme_file = random.choice(themes)
    filename_no_ext = os.path.splitext(theme_file)[0]
    preview_file = find_theme_preview(folder, filename_no_ext)
    theme_path = os.path.join(folder, f"{filename_no_ext}{ext}")
    if preview_file:
        await bot.send_photo(call.from_user.id, photo=FSInputFile(preview_file), caption="📌 Предпросмотр случайной темы")
    if os.path.exists(theme_path):
        await bot.send_document(call.from_user.id, document=FSInputFile(theme_path),
                                caption="Нажми для установки случайной темы!\n\nТема создана в @TT_temki_bot 😉")
    else:
        await call.answer("❌ Файл темы не найден", show_alert=True)
    await call.answer()

@dp.callback_query(F.data.startswith("install_"))
async def install_theme(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    _, device, category, filename = call.data.split("_", 3)
    ext = theme_extension(device)
    base_dir = os.path.join(resolve_device_folder(device), category)
    theme_file = os.path.join(base_dir, f"{filename}{ext}")
    preview_file = find_theme_preview(base_dir, filename)
    if preview_file:
        await bot.send_photo(call.from_user.id, photo=FSInputFile(preview_file), caption="📌 Предпросмотр темы")
    if os.path.exists(theme_file):
        await bot.send_document(call.from_user.id, document=FSInputFile(theme_file),
                                caption="Нажми для установки!\n\nТема создана в @TT_temki_bot 😉")
    else:
        await call.answer("❌ Файл темы не найден", show_alert=True)

@dp.callback_query(F.data == "check_sub")
async def check_subscription(call: CallbackQuery):
    uid = ensure_user(call.from_user)
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, call.from_user.id)
        if member.status in ("member", "administrator", "creator"):
            db["users"][uid]["subscribed"] = True
            save_users()
            await call.message.edit_text("😋 Выбери нужное:", reply_markup=menu_keyboard())
            return
    except:
        pass
    await call.answer("❌ Ты ещё не подписан", show_alert=True)

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return
    users = db["users"]
    total = len(users)
    subs = sum(1 for u in users.values() if u["subscribed"])
    camp_stats = {}
    for u in users.values():
        camp_stats[u["campaign"]] = camp_stats.get(u["campaign"], 0) + 1
    text = f"📊 <b>Статистика</b>\n\n👤 Пользователей: {total}\n✅ Подписались: {subs}\n\n<b>Кампании:</b>\n"
    for k, v in camp_stats.items():
        text += f"\n{k}: {v}"
    await call.message.edit_text(text, reply_markup=admin_keyboard())

@dp.callback_query(F.data == "campaigns")
async def campaigns(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return
    text = "<b>Кампании:</b>\n"
    for c in db["campaigns"]:
        text += f"\n• {c}\nhttps://t.me/{BOT_USERNAME}?start={c}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать кампанию", callback_data="new_campaign")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_admin")]
    ])
    await call.message.edit_text(text, reply_markup=kb)

@dp.callback_query(F.data == "back_admin")
async def back_admin(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return
    await call.message.edit_text("выбери:", reply_markup=admin_keyboard())

@dp.callback_query(F.data == "new_campaign")
async def new_campaign(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return
    await call.message.edit_text("Введи название кампании (латиница, без пробелов):")
    await state.set_state(CampaignStates.waiting_for_name)

@dp.message(CampaignStates.waiting_for_name)
async def save_campaign(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    name = message.text.strip()
    if name in db["campaigns"]:
        await message.answer("❌ Такая кампания уже есть")
        return
    db["campaigns"].append(name)
    save_users()
    await state.clear()
    await message.answer(f"✅ Кампания создана:\nhttps://t.me/{BOT_USERNAME}?start={name}", reply_markup=admin_keyboard())

@dp.callback_query(F.data == "start_broadcast")
async def start_broadcast(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return
    await call.message.edit_text("📤 Пришли сообщение для рассылки")
    await state.set_state(BroadcastStates.waiting_for_message)

@dp.message(BroadcastStates.waiting_for_message)
async def do_broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    await state.clear()
    sent = 0
    total = len(db["users"])
    for uid in db["users"]:
        try:
            await bot.copy_message(
                chat_id=int(uid),
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                parse_mode="HTML"
            )
            sent += 1
        except:
            continue
    await message.answer(f"✅ Рассылка завершена ({sent}/{total})")
    await message.answer("выбери:", reply_markup=admin_keyboard())

@dp.callback_query(F.data == "languages")
async def choose_language_category(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    await call.message.edit_text("Выбери категорию языков:", reply_markup=languages_categories_keyboard())

@dp.callback_query(F.data.startswith("lang_cat_page_"))
async def paginate_languages_categories(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    page = int(call.data.replace("lang_cat_page_", ""))
    await call.message.edit_text("Выбери категорию языков:", reply_markup=languages_categories_keyboard(page))

@dp.callback_query(F.data.startswith("lang_category_"))
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
    description = current_lang.get('description', '')
    await call.message.edit_text(f"🎨 {category_name}: {current_lang['name']}\n{description}", reply_markup=languages_pagination_keyboard(slug, page))

@dp.callback_query(F.data.startswith("lang_page_"))
async def paginate_languages(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    parts = call.data.split("_")
    slug = parts[2]
    page = int(parts[3])
    category_name = SLUG_TO_LANG_CATEGORY.get(slug)
    current_lang = next((cat for cat in languages_db["categories"] if cat["slug"] == slug), None)["languages"][page]
    description = current_lang.get('description', '')
    await call.message.edit_text(f"🎨 {category_name}: {current_lang['name']}\n{description}", reply_markup=languages_pagination_keyboard(slug, page))

@dp.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()

@dp.callback_query(F.data == "random_language")
async def random_language_callback(call: CallbackQuery):
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
    description = lang.get('description', '')
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить", url=lang["link"])]
    ])
    await bot.send_message(call.from_user.id, f"Случайный язык: {lang['name']}\n{description}", reply_markup=kb)
    await call.answer()

# =========================
# ЗАПУСК
# =========================
async def main():
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
