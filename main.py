import asyncio
import json
import os
from datetime import datetime, timezone, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties

# =========================
# НАСТРОЙКИ
# =========================
BOT_TOKEN = "8554128234:AAHI-fEZi-B2C58O8ZKvg2oipDNcYcXYUvY"
CHANNEL_USERNAME = "@wursix"
USERS_FILE = "users.json"
ADMINS = {913949366}

# =========================
# BOT
# =========================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# =========================
# ХРАНИЛИЩЕ
# =========================
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

users = load_users()

def ensure_user(tg_user):
    user_id = str(tg_user.id)
    if user_id not in users:
        users[user_id] = {
            "first_start": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "subscribed": False,
            "device": None
        }
        save_users()
    return user_id

# =========================
# ПРОВЕРКА ПОДПИСКИ (БЕЗ ХЕНДЛЕРА!)
# =========================
async def ensure_subscribed(call: CallbackQuery) -> bool:
    user_id = ensure_user(call.from_user)

    if users[user_id]["subscribed"]:
        return True

    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, call.from_user.id)
        if member.status in ("member", "administrator", "creator"):
            users[user_id]["subscribed"] = True
            save_users()
            return True
    except:
        pass

    await call.message.edit_text(
        "❣️ Для доступа подпишись на канал:",
        reply_markup=subscribe_keyboard()
    )
    return False

# =========================
# ДАННЫЕ ТЕМ
# =========================
SECTION_DATA = {
    "аниме": [{"title": "Anime Theme 1", "url": "https://t.me"}],
    "котики": [{"title": "Cats Theme 1", "url": "https://t.me"}],
    "пошлые": [{"title": "Hot Theme 1", "url": "https://t.me"}],
}

# =========================
# КЛАВИАТУРЫ
# =========================
def subscribe_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Подписаться", url="https://t.me/wursix")],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")]
    ])

def menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="темки", callback_data="themes")]
    ])

def device_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="iPhone", callback_data="device_iphone")],
        [InlineKeyboardButton(text="Android", callback_data="device_android")],
        [InlineKeyboardButton(text="Компьютер", callback_data="device_pc")]
    ])

def sections_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=s, callback_data=f"section_{s}_0")]
            for s in SECTION_DATA
        ]
    )

def theme_keyboard(section, index, total):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить", callback_data=f"install_{section}_{index}")],
        [
            InlineKeyboardButton(text="⬅️", callback_data=f"nav_{section}_{index-1}"),
            InlineKeyboardButton(text=f"{index+1}/{total}", callback_data="noop"),
            InlineKeyboardButton(text="➡️", callback_data=f"nav_{section}_{index+1}")
        ],
        [InlineKeyboardButton(text="Добавить бота в группу", callback_data="add_bot")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="back_menu")]
    ])

# =========================
# /start
# =========================
@dp.message(CommandStart())
async def start(message: Message):
    user_id = ensure_user(message.from_user)

    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, message.from_user.id)
        if member.status in ("member", "administrator", "creator"):
            users[user_id]["subscribed"] = True
            save_users()
            await message.answer("😋 выбери:", reply_markup=menu_keyboard())
            return
    except:
        pass

    await message.answer("❣️ Подпишись:", reply_markup=subscribe_keyboard())

# =========================
# ПРОВЕРКА ПОДПИСКИ
# =========================
@dp.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery):
    user_id = ensure_user(call.from_user)

    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, call.from_user.id)
        if member.status in ("member", "administrator", "creator"):
            users[user_id]["subscribed"] = True
            save_users()
            await call.message.edit_text("😋 выбери:", reply_markup=menu_keyboard())
            return
    except:
        pass

    await call.answer("Ты ещё не подписался 😢", show_alert=True)

# =========================
# ТЕМЫ → УСТРОЙСТВО
# =========================
@dp.callback_query(F.data == "themes")
async def choose_device(call: CallbackQuery):
    if not await ensure_subscribed(call):
        return

    await call.message.edit_text(
        "С какого девайса?",
        reply_markup=device_keyboard()
    )

@dp.callback_query(F.data.startswith("device_"))
async def choose_section(call: CallbackQuery):
    if not await ensure_subscribed(call):
        return

    user_id = ensure_user(call.from_user)
    users[user_id]["device"] = call.data.split("_")[1]
    save_users()

    await call.message.edit_text(
        "Выбери раздел:",
        reply_markup=sections_keyboard()
    )

# =========================
# ПОКАЗ ТЕМ
# =========================
@dp.callback_query(F.data.startswith("section_"))
@dp.callback_query(F.data.startswith("nav_"))
async def show_theme(call: CallbackQuery):
    if not await ensure_subscribed(call):
        return

    _, section, index = call.data.split("_")
    index = int(index)

    items = SECTION_DATA[section]
    index %= len(items)

    item = items[index]
    text = f"<b>{item['title']}</b>\n{index+1} из {len(items)}"

    await call.message.edit_text(
        text,
        reply_markup=theme_keyboard(section, index, len(items))
    )

# =========================
# УСТАНОВКА
# =========================
@dp.callback_query(F.data.startswith("install_"))
async def install(call: CallbackQuery):
    if not await ensure_subscribed(call):
        return

    await call.answer("Тема установлена ✅", show_alert=True)

@dp.callback_query(F.data == "add_bot")
async def add_bot(call: CallbackQuery):
    await call.answer("Скоро 😏", show_alert=True)

@dp.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer(cache_time=1)

@dp.callback_query(F.data == "back_menu")
async def back_to_menu(call: CallbackQuery):
    await call.message.edit_text(
        "😋 выбери:",
        reply_markup=menu_keyboard()
    )

# =========================
# АДМИН ПАНЕЛЬ
# =========================
@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id not in ADMINS:
        return

    total = len(users)
    subs = sum(1 for u in users.values() if u["subscribed"])

    today = datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=6)

    daily = {}
    for u in users.values():
        d = datetime.strptime(u["first_start"], "%Y-%m-%d").date()
        if d < cutoff:
            continue
        k = d.isoformat()
        daily.setdefault(k, {"started": 0, "sub": 0})
        daily[k]["started"] += 1
        if u["subscribed"]:
            daily[k]["sub"] += 1

    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"👤 Пользователей: {total}\n"
        f"✅ Подписались: {subs}\n\n"
        f"<b>По дням:</b>\n"
    )

    for d, v in sorted(daily.items()):
        conv = round(v["sub"] / v["started"] * 100, 2) if v["started"] else 0
        text += (
            f"\n<b>{d}</b>\n"
            f"Запуски: {v['started']}\n"
            f"Подписки: {v['sub']}\n"
            f"Конверсия: {conv}%\n"
        )

    await message.answer(text)

# =========================
# ЗАПУСК
# =========================
async def main():
    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
