import os

CATEGORIES = [
    [("Аниме", "anime"), ("Дед инсайд", "ded_insayd"), ("Котики", "kotiki")],
    [("Милые", "milye"), ("Зимние", "zimnie"), ("Пошлые", "poshlye")],
    [("Кино", "kino"), ("Сердечки", "serdechki"), ("K-Pop", "k_pop")],
    [("Автомобили", "avtomobili"), ("Парные", "parnye")],
]
SLUG_TO_CATEGORY = {slug: name for row in CATEGORIES for name, slug in row}
ALL_THEME_CATEGORIES = [item for sublist in CATEGORIES for item in sublist]
THEMES_PER_PAGE = 9
THEMES_IN_CATEGORY_PER_PAGE = 9

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Environment variable BOT_TOKEN is required")

CHANNEL_USERNAME = "@wursix"
USERS_FILE = "users.json"
STICKER_PACKS_FILE = "stickerpacks.json"
ADMINS = {913949366}
BOT_USERNAME = "TT_temki_bot"
GROUP_START_IMAGE = "groupstart.jpg"
START_MENU_TEXT = "Тут ты можешь можешь настроить свой Telegram 💞\n\nСкорее выбирай:"
REPEAT_MENU_TEXT = "Выберай пункт меню:  💞💞"

LANG_PER_PAGE = 3
