from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from tgbot.config import BOT_TOKEN


bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
