from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from tgbot.config import CHANNEL_USERNAME, REPEAT_MENU_TEXT, START_MENU_TEXT
from tgbot.keyboards import bot_link_keyboard, menu_keyboard, subscribe_keyboard
from tgbot.runtime import bot
from tgbot.storage import db, ensure_user, save_users

from .shared import replace_message_with_text


router = Router(name="start_handlers")


@router.message(Command("start"))
async def start(message: Message):
    args = message.text.split(maxsplit=1)
    if message.chat.type in ("group", "supergroup"):
        await message.answer(
            "У меня есть команды которые ты можешь использовать в групповом чате 😋 \n\nМои команды:\n/randomtheme - 🔖 Рандомная тема\n/randomlanguage - 📝 Рандомный язык",
            reply_markup=bot_link_keyboard(),
        )
        return

    campaign = args[1] if len(args) > 1 else "organic"
    if campaign not in db["campaigns"]:
        campaign = "organic"
    ensure_user(db, message.from_user, campaign)
    await message.answer(f"Приветик, {message.from_user.first_name}!")
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, message.from_user.id)
        is_subscribed = member.status in ("member", "administrator", "creator")
    except Exception:
        is_subscribed = False
    if is_subscribed:
        db["users"][str(message.from_user.id)]["subscribed"] = True
        save_users(db)
        await message.answer(START_MENU_TEXT, reply_markup=menu_keyboard())
    else:
        await message.answer("❣️ Подпишись:", reply_markup=subscribe_keyboard())
    try:
        await message.delete()
    except Exception:
        pass


@router.callback_query(F.data == "back_menu")
async def back_menu(call: CallbackQuery):
    await replace_message_with_text(call, REPEAT_MENU_TEXT, menu_keyboard())
    await call.answer()


@router.callback_query(F.data == "check_sub")
async def check_subscription(call: CallbackQuery):
    uid = ensure_user(db, call.from_user)
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, call.from_user.id)
        if member.status in ("member", "administrator", "creator"):
            db["users"][uid]["subscribed"] = True
            save_users(db)
            await call.message.edit_text(REPEAT_MENU_TEXT, reply_markup=menu_keyboard())
            return
    except Exception:
        pass
    await call.answer("❌ Ты ещё не подписан", show_alert=True)
