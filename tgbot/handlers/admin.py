from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from tgbot.config import ADMINS, BOT_USERNAME
from tgbot.keyboards import admin_keyboard
from tgbot.runtime import bot
from tgbot.states import BroadcastStates, CampaignStates
from tgbot.storage import db, save_users


router = Router(name="admin_handlers")


@router.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id not in ADMINS:
        return
    await message.answer("выбери:", reply_markup=admin_keyboard())


@router.callback_query(F.data == "admin_stats")
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
    for key, value in camp_stats.items():
        text += f"\n{key}: {value}"
    await call.message.edit_text(text, reply_markup=admin_keyboard())


@router.callback_query(F.data == "campaigns")
async def campaigns(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return
    text = "<b>Кампании:</b>\n"
    for campaign in db["campaigns"]:
        text += f"\n• {campaign}\nhttps://t.me/{BOT_USERNAME}?start={campaign}"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать кампанию", callback_data="new_campaign")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_admin")],
        ]
    )
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "back_admin")
async def back_admin(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return
    await call.message.edit_text("выбери:", reply_markup=admin_keyboard())


@router.callback_query(F.data == "new_campaign")
async def new_campaign(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return
    await call.message.edit_text("Введи название кампании (латиница, без пробелов):")
    await state.set_state(CampaignStates.waiting_for_name)


@router.message(CampaignStates.waiting_for_name)
async def save_campaign(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    name = message.text.strip()
    if name in db["campaigns"]:
        await message.answer("❌ Такая кампания уже есть")
        return
    db["campaigns"].append(name)
    save_users(db)
    await state.clear()
    await message.answer(f"✅ Кампания создана:\nhttps://t.me/{BOT_USERNAME}?start={name}", reply_markup=admin_keyboard())


@router.callback_query(F.data == "start_broadcast")
async def start_broadcast(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return
    await call.message.edit_text("📤 Пришли сообщение для рассылки")
    await state.set_state(BroadcastStates.waiting_for_message)


@router.message(BroadcastStates.waiting_for_message)
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
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            continue
    await message.answer(f"✅ Рассылка завершена ({sent}/{total})")
    await message.answer("выбери:", reply_markup=admin_keyboard())
