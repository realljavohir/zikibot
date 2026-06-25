import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
RATE_LIMIT = 25  # max xabar per minute
MAX_PLAYERS = 40
JOIN_TIMEOUT = 60  # sekund, /join dan /game gacha kutish
DAY_DURATION = 120  # sekund
NIGHT_DURATION = 60  # sekund
