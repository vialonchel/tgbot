import asyncio
import json
import os
from datetime import datetime, timezone, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

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

class BroadcastStates(StatesGroup):
    waiting_for_message = State()

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
# ПРОВЕРКА ПОДПИСКИ
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
# ДАННЫЕ ТЕМ ПО УСТРОЙСТВАМ
# =========================
SECTION_DATA_IOS = {
    "аниме": [{"title": "Anime Theme 1", "file": "themes/ios/anime1.ttheme", "note": "Нажми для установки!\nТема создана в <a href='https://t.me/TT_temki_bot'>@TT_temki_bot</a> 😉"}],
    "котики": [{"title": "Cats Theme 1", "file": "themes/ios/cat1.ttheme", "note": "Нажми для установки!\nТема создана в <a href='https://t.me/TT_temki_bot'>@TT_temki_bot</a> 😉"}],
}

SECTION_DATA_ANDROID = {
    "аниме": [{"title": "Anime Theme 1", "file": "themes/android/anime1.atheme", "note": "Нажми для установки!\nТема создана в <a href='https://t.me/TT_temki_bot'>@TT_temki_bot</a> 😉"}],
    "котики": [{"title": "Cats Theme 1", "file": "themes/android/cat1.atheme", "note": "Нажми для установки!\nТема создана в <a href='https://t.me/TT_temki_bot'>@TT_temki_bot</a> 😉"}],
}

SECTION_DATA_PC = {
    "аниме": [{"title": "Anime Theme 1", "file": "themes/pc/anime1.pctheme", "note": "Нажми для установки!\nТема создана в <a href='https://t.me/TT_temki_bot'>@TT_temki_bot</a> 😉"}],
    "котики": [{"title": "Cats Theme 1", "file": "themes/pc/cat1.pctheme", "note": "Нажми для установки!\nТема создана в <a href='https://t.me/TT_temki_bot'>@TT_temki_bot</a> 😉"}],
}

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

def device_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="iPhone", callback_data="device_iphone")],
        [InlineKeyboardButton(text="Android", callback_data="device_android")],
        [InlineKeyboardButton(text="Компьютер", callback_data="device_pc")]
    ])

def sections_keyboard(device):
    if device == "iphone":
        data = SECTION_DATA_IOS
    elif device == "android":
        data = SECTION_DATA_ANDROID
    else:
        data = SECTION_DATA_PC
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=s, callback_data=f"section_{s}_0")] for s in data]
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
    user_name = message.from_user.first_name or "друг"

    await message.answer(f"Привет, {user_name}!")

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
    ensure_user(call.from_user)
    if not await ensure_subscribed(call):
        return
    await call.message.edit_text("С какого девайса?", reply_markup=device_keyboard())

@dp.callback_query(F.data.startswith("device_"))
async def choose_section(call: CallbackQuery):
    user_id = ensure_user(call.from_user)
    if not await ensure_subscribed(call):
        return
    device = call.data.split("_")[1]
    users[user_id]["device"] = device
    save_users()
    await call.message.edit_text("Выбери раздел:", reply_markup=sections_keyboard(device))

# =========================
# ПОКАЗ ТЕМ
# =========================
@dp.callback_query(F.data.startswith(("section_", "nav_")))
async def show_theme(call: CallbackQuery):
    user_id = ensure_user(call.from_user)
    if not await ensure_subscribed(call):
        return
    device = users[user_id].get("device", "pc")
    if device == "iphone":
        section_data = SECTION_DATA_IOS
    elif device == "android":
        section_data = SECTION_DATA_ANDROID
    else:
        section_data = SECTION_DATA_PC

    parts = call.data.split("_")
    section = parts[1]
    index = int(parts[2])
    items = section_data[section]
    index %= len(items)
    item = items[index]
    text = f"<b>{item['title']}</b>\n{index+1} из {len(items)}"

    await call.message.edit_text(text, reply_markup=theme_keyboard(section, index, len(items)))

# =========================
# УСТАНОВКА
# =========================
@dp.callback_query(F.data.startswith("install_"))
async def install(call: CallbackQuery):
    user_id = ensure_user(call.from_user)
    if not await ensure_subscribed(call):
        return

    device = users[user_id].get("device", "pc")
    if device == "iphone":
        section_data = SECTION_DATA_IOS
    elif device == "android":
        section_data = SECTION_DATA_ANDROID
    else:
        section_data = SECTION_DATA_PC

    parts = call.data.split("_")
    section = parts[1]
    index = int(parts[2])
    item = section_data[section][index]
    file_path = item["file"]
    note = item["note"]

    if os.path.exists(file_path):
        await call.message.answer_document(open(file_path, "rb"), caption=note, parse_mode="HTML")
        await call.answer("Тема отправлена ✅", show_alert=True)
    else:
        await call.message.answer(f"❌ Файл {file_path} не найден!")

# =========================
# РАССЫЛКА
# =========================
@dp.callback_query(F.data == "start_broadcast")
async def broadcast_button(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return
    await call.message.edit_text("📤 Отправь сообщение для рассылки. Можно текст, эмодзи, ссылки, фото.")
    await state.set_state(BroadcastStates.waiting_for_message)

@dp.message(BroadcastStates.waiting_for_message)
async def process_broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    await state.clear()

    users_list = list(users.keys())
    sent_count = 0
    photo = message.photo[-1] if message.photo else None
    caption = message.caption or message.text

    for user_id in users_list:
        try:
            if photo:
                await bot.send_photo(chat_id=int(user_id), photo=photo.file_id, caption=caption, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=int(user_id), text=caption, parse_mode="HTML")
            sent_count += 1
        except Exception as e:
            print(f"Не удалось отправить {user_id}: {e}")

    await message.answer(f"✅ Рассылка завершена. Отправлено пользователям: {sent_count}/{len(users_list)}")

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

    stats_text = f"📊 <b>Статистика</b>\n\n👤 Пользователей: {total}\n✅ Подписались: {subs}\n\n<b>По дням:</b>\n"
    for d, v in sorted(daily.items()):
        conv = round(v["sub"] / v["started"] * 100, 2) if v["started"] else 0
        stats_text += f"\n<b>{d}</b>\nЗапуски: {v['started']}\nПодписки: {v['sub']}\nКонверсия: {conv}%\n"

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сделать рассылку", callback_data="start_broadcast")]
    ])
    await message.answer(stats_text, reply_markup=admin_kb)

# =========================
# ЗАПУСК
# =========================
async def main():
    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
