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
BOT_TOKEN = "TOKEN"
CHANNEL_USERNAME = "@wursix"
USERS_FILE = "users.json"
ADMINS = {913949366}
BOT_USERNAME = "TT_temki_bot"

# =========================
# BOT
# =========================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

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
        return json.load(f)

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
        m = await bot.get_chat_member(CHANNEL_USERNAME, call.from_user.id)
        if m.status in ("member", "administrator", "creator"):
            db["users"][uid]["subscribed"] = True
            save_users()
            return True
    except:
        pass
    await call.message.edit_text("❣️ Подпишись:", reply_markup=subscribe_keyboard())
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

# =========================
# /start (кампании)
# =========================
@dp.message(CommandStart(deep_link=True))
async def start_deep(message: Message, command: CommandStart):
    campaign = command.args or "organic"
    if campaign not in db["campaigns"]:
        campaign = "organic"
    ensure_user(message.from_user, campaign)
    await start_common(message)

@dp.message(CommandStart())
async def start_plain(message: Message):
    ensure_user(message.from_user)
    await start_common(message)

async def start_common(message: Message):
    await message.answer(f"Привет, {message.from_user.first_name}!")
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, message.from_user.id)
        if m.status in ("member", "administrator", "creator"):
            uid = str(message.from_user.id)
            db["users"][uid]["subscribed"] = True
            save_users()
            await message.answer("😋 выбери:", reply_markup=menu_keyboard())
            return
    except:
        pass
    await message.answer("❣️ Подпишись:", reply_markup=subscribe_keyboard())

# =========================
# ADMIN
# =========================
@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id not in ADMINS:
        return
    await message.answer("выбери:", reply_markup=admin_keyboard())

# =========================
# СТАТИСТИКА
# =========================
@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    users = db["users"]
    total = len(users)
    subs = sum(1 for u in users.values() if u["subscribed"])

    camp_stats = {}
    for u in users.values():
        camp = u["campaign"]
        camp_stats.setdefault(camp, 0)
        camp_stats[camp] += 1

    text = f"📊 <b>Статистика</b>\n\n👤 Пользователей: {total}\n✅ Подписались: {subs}\n\n<b>Кампании:</b>\n"
    for k, v in camp_stats.items():
        text += f"\n{k}: {v}"

    await call.message.edit_text(text, reply_markup=admin_keyboard())

# =========================
# КАМПАНИИ
# =========================
@dp.callback_query(F.data == "campaigns")
async def campaigns(call: CallbackQuery):
    text = "<b>Кампании:</b>\n"
    for c in db["campaigns"]:
        text += f"\n• {c}\nhttps://t.me/{BOT_USERNAME}?start={c}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать кампанию", callback_data="new_campaign")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin")]
    ])
    await call.message.edit_text(text, reply_markup=kb)

@dp.callback_query(F.data == "new_campaign")
async def new_campaign(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Введи название кампании (латиница, без пробелов):")
    await state.set_state(CampaignStates.waiting_for_name)

@dp.message(CampaignStates.waiting_for_name)
async def save_campaign(message: Message, state: FSMContext):
    name = message.text.strip()
    if name in db["campaigns"]:
        await message.answer("❌ Такая кампания уже есть")
        return
    db["campaigns"].append(name)
    save_users()
    await state.clear()
    await message.answer(
        f"✅ Кампания создана:\nhttps://t.me/{BOT_USERNAME}?start={name}",
        reply_markup=admin_keyboard()
    )

# =========================
# РАССЫЛКА
# =========================
@dp.callback_query(F.data == "start_broadcast")
async def start_broadcast(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return
    await call.message.edit_text("📤 Пришли сообщение для рассылки")
    await state.set_state(BroadcastStates.waiting_for_message)

@dp.message(BroadcastStates.waiting_for_message)
async def do_broadcast(message: Message, state: FSMContext):
    await state.clear()
    sent = 0
    for uid in db["users"]:
        try:
            if message.photo:
                await bot.send_photo(int(uid), message.photo[-1].file_id,
                                     caption=message.caption, parse_mode="HTML")
            else:
                await bot.send_message(int(uid), message.text, parse_mode="HTML")
            sent += 1
        except:
            pass
    await message.answer(f"✅ Рассылка завершена ({sent})")

# =========================
# ЗАПУСК
# =========================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
