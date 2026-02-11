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