import json
import os
from datetime import datetime, timezone

from tgbot.config import STICKER_PACKS_FILE, USERS_FILE


def load_users():
    if not os.path.exists(USERS_FILE):
        return {"users": {}, "campaigns": ["organic"], "sticker_packs": []}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "users" not in data:
        data["users"] = {}
    if "campaigns" not in data:
        data["campaigns"] = ["organic"]
    if "sticker_packs" not in data:
        data["sticker_packs"] = []
    return data


def save_users(db: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def ensure_user(db: dict, tg_user, campaign: str = "organic") -> str:
    uid = str(tg_user.id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "first_start": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "subscribed": False,
            "device": None,
            "campaign": campaign,
            "sticker_packs": [],
            "sticker_pack_seq": 0,
        }
        save_users(db)
    else:
        if "sticker_packs" not in db["users"][uid]:
            db["users"][uid]["sticker_packs"] = []
        if "sticker_pack_seq" not in db["users"][uid]:
            db["users"][uid]["sticker_pack_seq"] = 0
    return uid


def load_languages():
    if not os.path.exists("languages.json"):
        return {"categories": []}
    with open("languages.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_stickerpacks():
    if not os.path.exists(STICKER_PACKS_FILE):
        return {"packs": []}
    with open(STICKER_PACKS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "packs" not in data or not isinstance(data["packs"], list):
        return {"packs": []}
    return data


languages_db = load_languages()
SLUG_TO_LANG_CATEGORY = {cat["slug"]: cat["name"] for cat in languages_db["categories"]}
ALL_LANG_CATEGORIES = languages_db["categories"]

db = load_users()
