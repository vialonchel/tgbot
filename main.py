import asyncio
import json
import os
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
# =========================1
BOT_TOKEN = "8554128234:AAHI-fEZi-B2C58O8ZKvg2oipDNcYcXYUvY"
CHANNEL_USERNAME = "@LoveToYou3"
USERS_FILE = "users.json"
ADMINS = {913949366}
BOT_USERNAME = "TT_temki_bot"

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

# =========================
# ХРАНИЛИЩЕ
# =========================
def load_users():
    if not os.path.exists(USERS_FILE):
        return {"users": {}, "campaigns": ["organic"]}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Ensure required keys exist
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

# =========================
# ПРОВЕРКА ПОДПИСКИ
# =========================
async def ensure_subscribed(call: CallbackQuery):
    uid = ensure_user(call.from_user)
    if db["users"][uid]["subscribed"]:
        return True
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, call.from_user.id)
        if member.status in ("member", "administrator", "creator"):
            db["users"][uid]["subscribed"] = True
            save_users()
            return True
    except Exception:
        pass
    # Не редактируем сообщение, просто показываем алерт
    await call.answer("❣️ Подпишись на канал и нажми кнопку снова", show_alert=True)
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
        [InlineKeyboardButton(text="темки", callback_data="themes")]
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
    return kb.as_markup()

# =========================
# ОБРАБОТЧИКИ
# =========================
@dp.message(Command("start"))
async def start(message: Message):
    args = message.text.split(maxsplit=1)
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

# =========================
# CALLBACKS
# =========================
@dp.callback_query(F.data == "back_menu")
async def back_menu(call: CallbackQuery):
    await call.message.edit_text("😋 Выбери нужное:", reply_markup=menu_keyboard())

@dp.callback_query(F.data.startswith("device_"))
async def select_device(call: CallbackQuery):
    if not await ensure_subscribed(call):
        return
    device = call.data.replace("device_", "")
    await call.message.edit_text("Выбери категорию:", reply_markup=categories_keyboard(device))

@dp.callback_query(F.data.startswith("category_"))
async def select_category(call: CallbackQuery):
    if not await ensure_subscribed(call):
        return
    _, device, slug = call.data.split("_", 2)
    category = SLUG_TO_CATEGORY.get(slug)
    if not category:
        await call.answer("❌ Категория не найдена")
        return
    await call.message.edit_text(f"🎨 {category}:", reply_markup=themes_keyboard_for_category(device, category))

@dp.callback_query(F.data.startswith("back_to_devices_"))
async def back_to_devices(call: CallbackQuery):
    if not await ensure_subscribed(call):
        return
    device = call.data.replace("back_to_devices_", "")
    await call.message.edit_text("С какого девайса ты?", reply_markup=device_keyboard())

@dp.callback_query(F.data.startswith("back_to_categories_"))
async def back_to_categories(call: CallbackQuery):
    if not await ensure_subscribed(call):
        return
    device = call.data.replace("back_to_categories_", "")
    await call.message.edit_text("Выбери категорию:", reply_markup=categories_keyboard(device))

@dp.callback_query(F.data == "themes")
async def choose_device(call: CallbackQuery):
    if not await ensure_subscribed(call):
        return
    await call.message.edit_text("С какого девайса ты?", reply_markup=device_keyboard())

@dp.callback_query(F.data.startswith("install_"))
async def install_theme(call: CallbackQuery):
    if not await ensure_subscribed(call):
        return

    _, device, category, filename = call.data.split("_", 3)
    theme_file = f"themes/{device}/{category}/{filename}{extensions.get(device, '')}"
    preview_file = f"themes/{device}/{category}/{filename}_preview.jpg"

    extensions = {"ios": ".tgios-theme", "android": ".attheme", "windows": ".tgdesktop-theme"}
    theme_file = f"themes/{device}/{filename}{extensions.get(device, '')}"
    preview_file = f"themes/{device}/{filename}_preview.jpg"
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
# =========================
# ЗАПУСК
# =========================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
