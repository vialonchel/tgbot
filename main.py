import asyncio
import json
import os
import io
import subprocess
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
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
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()


# =========================
# ХРАНИЛИЩЕ
# =========================
def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_users(data: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


users = load_users()


# =========================
# КЛАВИАТУРЫ
# =========================
def subscribe_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Подписаться", url="https://t.me/wursix")],
            [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")]
        ]
    )


def menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="темки", callback_data="themes_0"),
                InlineKeyboardButton(text="язычки", callback_data="langs_0")
            ],
            [
                InlineKeyboardButton(text="обои", callback_data="walls_0"),
                InlineKeyboardButton(text="стики", callback_data="stickers_0"),
                InlineKeyboardButton(text="эмодзики", callback_data="emojis_0")
            ],
        ]
    )


def navigation_keyboard(section: str, index: int, total: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="назад", callback_data=f"{section}_{index - 1}"),
            InlineKeyboardButton(text="меню", callback_data="back_menu"),
            InlineKeyboardButton(text="вперед", callback_data=f"{section}_{index + 1}")
        ]]
    )


def get_daily_stats(users: dict, days: int = 7) -> dict:
    """
    Статистика по последним N дням (по дате first_start)
    """
    today = datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=days - 1)

    daily = {}

    for user in users.values():
        day = datetime.strptime(user["first_start"], "%Y-%m-%d").date()

        if day < cutoff:
            continue

        key = day.isoformat()

        if key not in daily:
            daily[key] = {
                "started": 0,
                "subscribed": 0
            }

        daily[key]["started"] += 1

        if user.get("subscribed"):
            daily[key]["subscribed"] += 1

    # конверсия
    for data in daily.values():
        s = data["started"]
        data["conversion"] = round(data["subscribed"] / s * 100, 2) if s else 0.0

    return dict(sorted(daily.items()))



# =========================
# /start
# =========================
@dp.message(CommandStart())
async def start(message: Message):
    user_id = str(message.from_user.id)

    # payload
    payload = "organic"
    if message.text and "=" in message.text:
        payload = message.text.split("=", 1)[1]

    # первый старт
    if user_id not in users:
        users[user_id] = {
            "first_start": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "campaign": payload,
            "subscribed": False
        }
        save_users(users)

    # проверка подписки
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, message.from_user.id)
        if member.status in ("member", "administrator", "creator"):
            users[user_id]["subscribed"] = True
            save_users(users)

            await message.answer(
                "😋 выбери что хочешь поменять:",
                reply_markup=menu_keyboard()
            )
            return
    except Exception:
        pass

    await message.answer(
        "❣️ Для доступа к боту необходимо подписаться:",
        reply_markup=subscribe_keyboard()
    )


# =========================
# ПРОВЕРКА ПОДПИСКИ
# =========================
@dp.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery):
    user_id = str(call.from_user.id)

    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, call.from_user.id)
        if member.status in ("member", "administrator", "creator"):
            users[user_id]["subscribed"] = True
            save_users(users)

            await call.message.delete()
            await call.message.answer(
                "😋 выбери что хочешь поменять:",
                reply_markup=menu_keyboard()
            )
        else:
            await call.answer("ты ещё не подписался :(", show_alert=True)
    except Exception:
        await call.answer("ошибка проверки подписки", show_alert=True)


# =========================
# КОНТЕНТ
# =========================
THEMES = [{"title": "Love Dark", "url": "https://t.me"}]
LANGS = [{"title": "Русский", "url": "https://t.me"}]
WALLS = [{"title": "Обои", "url": "https://t.me"}]
STICKERS = [{"title": "Stickers", "url": "https://t.me"}]
EMOJIS = [{"title": "Emoji", "url": "https://t.me"}]

DATA_MAP = {
    "themes": THEMES,
    "langs": LANGS,
    "walls": WALLS,
    "stickers": STICKERS,
    "emojis": EMOJIS
}


@dp.callback_query(F.data.startswith(tuple(DATA_MAP.keys())))
async def show_section(call: CallbackQuery):
    section, index = call.data.split("_")
    index = int(index)

    items = DATA_MAP[section]
    index %= len(items)

    item = items[index]
    text = f"<b>{item['title']}</b>\n{index + 1} из {len(items)}\n<a href='{item['url']}'>установить</a>"

    await call.message.edit_text(
        text,
        reply_markup=navigation_keyboard(section, index, len(items))
    )


@dp.callback_query(F.data == "back_menu")
async def back_menu(call: CallbackQuery):
    await call.message.edit_text(
        "😋 выбери что хочешь поменять:",
        reply_markup=menu_keyboard()
    )


# =========================
# АДМИН
# =========================
@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id not in ADMINS:
        return

    total_users = len(users)
    total_subscribed = sum(1 for u in users.values() if u["subscribed"])
    total_conv = round(total_subscribed / total_users * 100, 2) if total_users else 0

    daily_stats = get_daily_stats(users)

    text = (
        "📊 <b>Общая статистика</b>\n\n"
        f"👤 Запустили бота: {total_users}\n"
        f"✅ Подписались: {total_subscribed}\n"
        f"🎯 Общая конверсия: {total_conv}%\n\n"
        "📅 <b>По дням:</b>\n"
    )

    for day, data in daily_stats.items():
        text += (
            f"\n<b>{day}</b>\n"
            f"Запуски: {data['started']}\n"
            f"Подписки: {data['subscribed']}\n"
            f"Конверсия: {data['conversion']}%\n"
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
