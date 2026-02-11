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
# ДАННЫЕ ТЕМ
# =========================
SECTION_DATA = {
    "аниме": [{"title": "Anime Theme 1", "url": "https://t.me"}],
    "дед инсайд": [{"title": "Dead Inside 1", "url": "https://t.me"}],
    "котики": [{"title": "Cute Cats 1", "url": "https://t.me"}],
    "милые": [{"title": "Cute Theme 1", "url": "https://t.me"}],
    "зимние": [{"title": "Winter Theme 1", "url": "https://t.me"}],
    "пошлые": [{"title": "Naughty Theme 1", "url": "https://t.me"}],
    "фильмы и сериалы": [{"title": "Movies Theme 1", "url": "https://t.me"}],
    "сердечки": [{"title": "Hearts Theme 1", "url": "https://t.me"}],
    "k-pop": [{"title": "K-Pop Theme 1", "url": "https://t.me"}],
    "автомобили": [{"title": "Cars Theme 1", "url": "https://t.me"}],
    "парные": [{"title": "Couple Theme 1", "url": "https://t.me"}]
}

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
                InlineKeyboardButton(text="темки", callback_data="themes_0")
            ]
        ]
    )


def theme_navigation_keyboard(section: str, index: int, total: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить", callback_data=f"install_{section}_{index}")],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"{section}_{index - 1}"),
            InlineKeyboardButton(text=f"{index + 1}/{total}", callback_data="noop"),
            InlineKeyboardButton(text="Вперед ➡️", callback_data=f"{section}_{index + 1}")
        ],
        [InlineKeyboardButton(text="Добавить бота в группу", callback_data="add_bot")]
    ])


# =========================
# /start
# =========================
@dp.message(CommandStart())
async def start(message: Message):
    user_id = str(message.from_user.id)

    if user_id not in users:
        users[user_id] = {
            "first_start": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "subscribed": False
        }
        save_users(users)

    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, message.from_user.id)
        if member.status in ("member", "administrator", "creator"):
            users[user_id]["subscribed"] = True
            save_users(users)
            await message.answer("😋 выбери что хочешь поменять:", reply_markup=menu_keyboard())
            return
    except Exception:
        pass

    await message.answer("❣️ Для доступа к боту необходимо подписаться:", reply_markup=subscribe_keyboard())


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
            await call.message.answer("😋 выбери что хочешь поменять:", reply_markup=menu_keyboard())
        else:
            await call.answer("Ты ещё не подписался :(", show_alert=True)
    except Exception:
        await call.answer("Ошибка проверки подписки", show_alert=True)


# =========================
# ВЫБОР УСТРОЙСТВА
# =========================
@dp.callback_query(F.data == "themes_0")
async def choose_device(call: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="iPhone", callback_data="device_iphone")],
        [InlineKeyboardButton(text="Android", callback_data="device_android")],
        [InlineKeyboardButton(text="Компьютер", callback_data="device_pc")]
    ])
    await call.message.edit_text("С какого девайса ты?", reply_markup=keyboard)


@dp.callback_query(F.data.startswith("device_"))
async def choose_section(call: CallbackQuery):
    user_id = str(call.from_user.id)
    device = call.data.split("_")[1]
    users[user_id]["device"] = device
    save_users(users)

    sections = list(SECTION_DATA.keys())
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=sec, callback_data=f"section_{sec}_0")] for sec in sections
        ]
    )
    await call.message.edit_text("Выбери раздел:", reply_markup=keyboard)


# =========================
# ПОКАЗ ТЕМЫ
# =========================
@dp.callback_query(F.data.startswith("section_"))
async def show_theme(call: CallbackQuery):
    _, section, index = call.data.split("_")
    index = int(index)

    items = SECTION_DATA.get(section, [])
    if not items:
        await call.message.edit_text("Темы пока нет 😢")
        return

    index %= len(items)
    item = items[index]

    text = f"<b>{item['title']}</b>\n{index + 1} из {len(items)}"
    await call.message.edit_text(
        text,
        reply_markup=theme_navigation_keyboard(section, index, len(items))
    )


# =========================
# НАВИГАЦИЯ ПО ТЕМАМ
# =========================
@dp.callback_query(F.data.startswith(tuple(SECTION_DATA.keys())))
async def navigate_theme(call: CallbackQuery):
    # Обработка кнопок назад/вперед
    for section in SECTION_DATA.keys():
        if call.data.startswith(section):
            try:
                index = int(call.data.split("_")[1])
            except:
                return
            items = SECTION_DATA[section]
            index %= len(items)
            item = items[index]
            text = f"<b>{item['title']}</b>\n{index + 1} из {len(items)}"
            await call.message.edit_text(
                text,
                reply_markup=theme_navigation_keyboard(section, index, len(items))
            )


# =========================
# УСТАНОВКА ТЕМЫ
# =========================
@dp.callback_query(F.data.startswith("install_"))
async def install_theme(call: CallbackQuery):
    _, section, index = call.data.split("_")
    index = int(index)
    await call.answer(f"Тема {section} #{index + 1} установлена ✅", show_alert=True)


# =========================
# ПУСТАЯ КНОПКА / ДОБАВИТЬ БОТА
# =========================
@dp.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer(cache_time=1)


@dp.callback_query(F.data == "add_bot")
async def add_bot(call: CallbackQuery):
    await call.answer("Функционал добавления пока не реализован", show_alert=True)
from datetime import timedelta, datetime, timezone

# =========================
# АДМИН
# =========================
@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id not in ADMINS:
        return

    total_users = len(users)
    total_subscribed = sum(1 for u in users.values() if u.get("subscribed"))
    total_conv = round(total_subscribed / total_users * 100, 2) if total_users else 0

    # Статистика по устройствам
    devices = {}
    for u in users.values():
        d = u.get("device")
        if d:
            devices[d] = devices.get(d, 0) + 1

    # Статистика по последним 7 дням
    today = datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=6)  # последние 7 дней
    daily = {}
    for u in users.values():
        day = datetime.strptime(u["first_start"], "%Y-%m-%d").date()
        if day < cutoff:
            continue
        key = day.isoformat()
        if key not in daily:
            daily[key] = {"started": 0, "subscribed": 0}
        daily[key]["started"] += 1
        if u.get("subscribed"):
            daily[key]["subscribed"] += 1
    # Конверсия по дням
    for data in daily.values():
        s = data["started"]
        data["conversion"] = round(data["subscribed"] / s * 100, 2) if s else 0.0

    # Формируем текст
    text = (
        f"📊 <b>Общая статистика</b>\n\n"
        f"👤 Всего пользователей: {total_users}\n"
        f"✅ Подписались: {total_subscribed}\n"
        f"🎯 Конверсия: {total_conv}%\n\n"
    )

    if devices:
        text += "<b>По устройствам:</b>\n"
        for d, count in devices.items():
            text += f"{d}: {count}\n"
        text += "\n"

    if daily:
        text += "<b>Статистика по дням (последние 7 дней):</b>\n"
        for day, data in sorted(daily.items()):
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