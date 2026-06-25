import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

RATE_LIMIT = 25   # max xabar per minute
MAX_PLAYERS = 40
JOIN_TIMEOUT = 60  # sekund, /join dan /game gacha kutish
DAY_DURATION = 120  # sekund
NIGHT_DURATION = 60  # sekund

# Do'kon narxlari (admin panel orqali o'zgartiriladi)
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

# Premium guruhlar (admin panel orqali boshqariladi)
PREMIUM_GROUPS: set = set()

# Karta rekvizitlari
CARD_NUMBER = os.getenv("CARD_NUMBER", "0000 0000 0000 0000")
CARD_OWNER  = os.getenv("CARD_OWNER", "Karta egasi")
