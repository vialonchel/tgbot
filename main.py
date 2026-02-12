import asyncio
import random
import json
import os
from PIL import Image
from datetime import datetime, timezone
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.types import ChatMemberUpdated
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =========================
# Категории
# =========================
CATEGORIES = [
    [("Аниме", "anime"), ("Дед инсайд", "ded_insayd"), ("Котики", "kotiki")],
    [("Милые", "milye"), ("Зимние", "zimnie"), ("Пошлые", "poshlye")],
    [("Кино", "kino"), ("Сердечки", "serdechki"), ("K-Pop", "k_pop")],
    [("Автомобили", "avtomobili"), ("Парные", "parnye")]
]
SLUG_TO_CATEGORY = {slug: name for row in CATEGORIES for name, slug in row}
# =========================
# Настройки
# =========================
BOT_TOKEN = "8554128234:AAHI-fEZi-B2C58O8ZKvg2oipDNcYcXYUvY"
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
class RandomLanguageStates(StatesGroup):
    waiting_for_choice = State()
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
            db["users"][uid]["subscribed"] = True
            save_users()
            return True
    except Exception:
        pass
    return False
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
        [InlineKeyboardButton(text="Добавить в группу", url="https://t.me/TT_temki_bot?startgroup&admin=post_messages+delete_messages")]
    ])

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📤 Сделать рассылку", callback_data="start_broadcast")],
        [InlineKeyboardButton(text="📣 Кампании", callback_data="campaigns")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_menu")]
    ])

def device_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 iOS", callback_data="device_ios"),
            InlineKeyboardButton(text="🤖 Android", callback_data="device_android"),
            InlineKeyboardButton(text="💻 Windows", callback_data="device_windows")
        ],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_menu")]
    ])

def categories_keyboard(device: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for row in CATEGORIES:
        row_buttons = [InlineKeyboardButton(text=name, callback_data=f"category_{device}_{slug}") for name, slug in row]
        kb.row(*row_buttons)
    kb.add(InlineKeyboardButton(text="⬅️ Главное меню", callback_data=f"back_to_devices_{device}"))
    kb.add(InlineKeyboardButton(text="Добавить в группу", url="https://t.me/TT_temki_bot?startgroup&admin=post_messages+delete_messages"))
    return kb.as_markup()

def themes_keyboard_for_category(device: str, category: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    folder = f"themes/{device}/{category}/"
    if not os.path.exists(folder):
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Темы не найдены", callback_data=f"back_to_categories_{device}")]])
   
    for file in os.listdir(folder):
        if file.startswith("."):
            continue
        filename_no_ext = os.path.splitext(file)[0]
        kb.add(InlineKeyboardButton(text=filename_no_ext, callback_data=f"install_{device}_{category}_{filename_no_ext}"))
    kb.add(InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data=f"back_to_categories_{device}"))
    kb.add(InlineKeyboardButton(text="Добавить в группу", url="https://t.me/TT_temki_bot?startgroup&admin=post_messages+delete_messages"))
    return kb.as_markup()

def languages_categories_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    categories = languages_db["categories"]
    if not categories:
        kb.add(InlineKeyboardButton(text="❌ Нет категорий языков", callback_data="noop"))
    else:
        for i in range(0, len(categories), 3):
            row = []
            for cat in categories[i:i+3]:
                row.append(InlineKeyboardButton(text=cat["name"], callback_data=f"lang_category_{cat['slug']}"))
            kb.row(*row)
    kb.add(InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_menu"))
    kb.add(InlineKeyboardButton(text="Добавить в группу", url="https://t.me/TT_temki_bot?startgroup&admin=post_messages+delete_messages"))
    return kb.as_markup()

def languages_pagination_keyboard(category_slug: str, page: int = 0) -> InlineKeyboardMarkup:
    categories = languages_db["categories"]
    category = next((cat for cat in categories if cat["slug"] == category_slug), None)
    if not category:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Категория не найдена", callback_data="languages")]])
    
    langs = category["languages"]
    total = len(langs)
    if total == 0:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Языки не найдены", callback_data="languages")]])
    
    if page < 0:
        page = 0
    if page >= total:
        page = total - 1
    
    current_lang = langs[page]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Установить", url=current_lang["link"]))
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"lang_page_{category_slug}_{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page+1}/{total}", callback_data="noop"))
    if page < total - 1:
        nav_row.append(InlineKeyboardButton(text="▶️ Вперед", callback_data=f"lang_page_{category_slug}_{page+1}"))
    kb.row(*nav_row)
    kb.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="back_menu"))
    kb.add(InlineKeyboardButton(text="Добавить в группу", url="https://t.me/TT_temki_bot?startgroup&admin=post_messages+delete_messages"))
    return kb.as_markup()

def bot_link_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💋Бот с темками 👉", url="https://t.me/TT_temki_bot")]
    ])
# =========================
# ОБРАБОТЧИКИ
# =========================
@dp.message(Command("start"))
async def start(message: Message):
    args = message.text.split(maxsplit=1)
    if message.chat.type in ("group", "supergroup"):
        if len(args) > 1 and args[1] == "temki":
            await message.answer_photo(
                photo=FSInputFile(GROUP_START_IMAGE),
                caption="Отправь в чат картинку с подписью \"/bg\" и я сделаю из нее фон для твоего Telegram или переходи в бот, там много интересного😉.",
                reply_markup=bot_link_keyboard()
            )
            await message.answer(
                "У меня есть команды которые ты можешь использовать здесь 😋 Мои команды:\n/randomtheme - 🔖 Рандомная тема\n/randomlanguage - 📝 Рандомный язык",
                reply_markup=bot_link_keyboard()
            )
        return  # Игнорируем простой /start в группе или неверный arg
    
    # Обычный /start только в личке
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
    await message.answer("С какого девайса? Выбери:", reply_markup=device_keyboard())
    await state.set_state(RandomThemeStates.waiting_for_device)

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
async def set_bg(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда работает только в группах.")
        return
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    await bot.download_file(file.file_path, "temp_bg.jpg")
    with Image.open("temp_bg.jpg") as img:
        img = img.resize((1, 1))
        r, g, b = img.getpixel((0, 0))
        bg_color = f"#{r:02x}{g:02x}{b:02x}"
    theme_content = f"chat_background_color={bg_color}\naccent_color={bg_color}"
    theme_file = "custom_bg.attheme"
    with open(theme_file, "w") as f:
        f.write(theme_content)
    await message.answer_document(document=FSInputFile(theme_file), caption="Вот тема на основе твоего изображения! Установи её.")
    os.remove("temp_bg.jpg")
    os.remove(theme_file)
# =========================
# CALLBACKS
# =========================
@dp.callback_query(F.data == "back_menu")
async def back_menu(call: CallbackQuery):
    await call.message.edit_text("😋 Выбери нужное:", reply_markup=menu_keyboard())

@dp.callback_query(F.data.startswith("device_"))
async def select_device(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    device = call.data.replace("device_", "")
    await call.message.edit_text("Выбери категорию:", reply_markup=categories_keyboard(device))

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

@dp.callback_query(F.data.startswith("install_"))
async def install_theme(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    _, device, category, filename = call.data.split("_", 3)
    extensions = {"ios": ".tgios-theme", "android": ".attheme", "windows": ".tgdesktop-theme"}
    theme_file = f"themes/{device}/{category}/{filename}{extensions.get(device, '')}"
    preview_file = f"themes/{device}/{category}/{filename}_preview.jpg"
    if os.path.exists(preview_file):
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
    await call.message.edit_text(f"🎨 {category_name}: {current_lang['name']}", reply_markup=languages_pagination_keyboard(slug, page))

@dp.callback_query(F.data.startswith("lang_page_"))
async def paginate_languages(call: CallbackQuery):
    if not await ensure_subscribed(call.from_user.id):
        return
    parts = call.data.split("_")
    slug = parts[2]
    page_str = parts[3]
    page = int(page_str)
    category_name = SLUG_TO_LANG_CATEGORY.get(slug)
    current_lang = next((cat for cat in languages_db["categories"] if cat["slug"] == slug), None)["languages"][page]
    await call.message.edit_text(f"🎨 {category_name}: {current_lang['name']}", reply_markup=languages_pagination_keyboard(slug, page))

@dp.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()

@dp.callback_query(F.data.startswith("device_"), RandomThemeStates.waiting_for_device)
async def process_random_theme_device(call: CallbackQuery, state: FSMContext):
    device = call.data.replace("device_", "")
    category_row = random.choice(CATEGORIES)
    _, category_slug = random.choice(category_row)
    category = SLUG_TO_CATEGORY[category_slug]
    folder = f"themes/{device}/{category}/"
    if not os.path.exists(folder):
        await call.message.edit_text("❌ Темы не найдены")
        await state.clear()
        return
    themes = [f for f in os.listdir(folder) if not f.startswith(".") and not f.endswith("_preview.jpg")]
    if not themes:
        await call.message.edit_text("❌ Темы не найдены")
        await state.clear()
        return
    theme_file = random.choice(themes)
    filename_no_ext = os.path.splitext(theme_file)[0]
    preview_file = f"{folder}{filename_no_ext}_preview.jpg"
    extensions = {"ios": ".tgios-theme", "android": ".attheme", "windows": ".tgdesktop-theme"}
    theme_path = f"{folder}{filename_no_ext}{extensions.get(device, '')}"
    if os.path.exists(preview_file):
        await bot.send_photo(call.from_user.id, photo=FSInputFile(preview_file), caption="📌 Предпросмотр случайной темы")
    if os.path.exists(theme_path):
        await bot.send_document(call.from_user.id, document=FSInputFile(theme_path),
                                caption="Нажми для установки случайной темы!\n\nТема создана в @TT_temki_bot 😉")
    else:
        await call.answer("❌ Файл темы не найден", show_alert=True)
    await state.clear()
# =========================
# ОБРАБОТКА ДОБАВЛЕНИЯ В ГРУППУ
# =========================
@dp.my_chat_member()
async def bot_added_to_group(update: ChatMemberUpdated):
    if update.new_chat_member.status == "member" and update.chat.type in ("group", "supergroup"):
        user_id = update.from_user.id
        try:
            await bot.send_message(user_id, "Нажмите кнопку добавить бота в группу, выберите группу в которую нужно добавить бота и нажмите Сохранить. в группе напишите /start temki")
        except Exception as e:
            print(f"Ошибка отправки инструкции: {e}")
# =========================
# ЗАПУСК
# =========================
async def main():
    await dp.start_polling(bot, allowed_updates=["message", "callback_query", "my_chat_member"])

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
