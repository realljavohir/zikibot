import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN .env faylida topilmadi!")

# ADMIN_IDS ni to'g'ri o'qish
ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]

RATE_LIMIT = 25
MAX_PLAYERS = 40
JOIN_TIMEOUT = 60
DAY_DURATION = 120
NIGHT_DURATION = 60

SHOP_PRICES = {
    "himoya":           {"price": 100, "currency": "coin"},
    "hujjat":           {"price": 190, "currency": "coin"},
    "ovozdan_himoya":   {"price": 1,   "currency": "diamond"},
    "miltiq":           {"price": 1,   "currency": "diamond"},
    "doridan_himoya":   {"price": 100, "currency": "coin"},
    "maska":            {"price": 100, "currency": "coin"},
    "qotildan_himoya":  {"price": 2,   "currency": "diamond"},
    "sirpanish_himoya": {"price": 300, "currency": "coin"},
    "geroydan_himoya":  {"price": 5,   "currency": "diamond"},
    "profil_almashish": {"price": 5,   "currency": "diamond"},
    "geroy":            {"price": 90,  "currency": "diamond"},
}

PREMIUM_GROUPS: set = set()

CARD_NUMBER = os.getenv("CARD_NUMBER", "0000 0000 0000 0000")
CARD_OWNER  = os.getenv("CARD_OWNER", "Karta egasi")
