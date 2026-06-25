import random
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

# ──────────────────────────────
# ROLLAR
# ──────────────────────────────

class Role(str, Enum):
    TINCH_AXOLI  = "tinch_axoli"
    DON          = "don"
    MAFIA        = "mafia"
    KOMISSAR     = "komissar"
    SERJANT      = "serjant"
    SHIFOKOR     = "shifokor"
    QOTIL        = "qotil"
    MASHUQA      = "mashuqa"
    ADVOKAT      = "advokat"
    SUIDSID      = "suidsid"
    DAYDI        = "daydi"
    OMADLI       = "omadli"
    KAMIKAZE     = "kamikaze"

ROLE_NAMES = {
    Role.TINCH_AXOLI: "👨 Tinch axoli",
    Role.DON:         "🤵 Don",
    Role.MAFIA:       "👨‍💼 Mafia",
    Role.KOMISSAR:    "👮 Komissar Katani",
    Role.SERJANT:     "👮 Serjant",
    Role.SHIFOKOR:    "🧑‍⚕️ Shifokor",
    Role.QOTIL:       "🔪 Qotil",
    Role.MASHUQA:     "💃 Ma'shuqa",
    Role.ADVOKAT:     "👨‍⚖️ Advokat",
    Role.SUIDSID:     "🧑 Suidsid",
    Role.DAYDI:       "🧟 Daydi",
    Role.OMADLI:      "☝️ Omadli",
    Role.KAMIKAZE:    "💣 Kamikaze",
}

ROLE_DESCRIPTIONS = {
    Role.TINCH_AXOLI: "Siz oddiy fuqarosiz. Shaharni mafiyadan himoya qiling!",
    Role.DON:         "Siz Don — mafia boshlig'isiz. Kechalari mafia bilan birga harakat qiling.",
    Role.MAFIA:       "Siz mafiyasiz. Don bilan birga ishlang.",
    Role.KOMISSAR:    "Har kecha bir kishini tekshira olasiz. Mafia bo'lsa bilib olasiz.",
    Role.SERJANT:     "Siz politsiya tomondasiz. Tinch axoli bilan birga ishlang.",
    Role.SHIFOKOR:    "Har kecha bir kishini davolaysiz. Agar o'sha kishi o'ldirilsa — tirik qoladi.",
    Role.QOTIL:       "Siz mustaqil qotilsiz. Hamma sizning dushmaningiz.",
    Role.MASHUQA:     "Siz komissar va serjantni ishdan chiqara olasiz.",
    Role.ADVOKAT:     "Kunduz osish paytida bir kishini himoya qila olasiz.",
    Role.SUIDSID:     "Siz o'zingizni o'ldira olasiz. Bu strategik qaror bo'lishi mumkin.",
    Role.DAYDI:       "Har kecha kimgadir kirasiz va uning roliga aylanasiz.",
    Role.OMADLI:      "Sizga qilgan qotillik urinishi amalga oshmaydi.",
    Role.KAMIKAZE:    "Agar o'ldirilsangiz, sizni o'ldirgan ham o'ladi!",
}

MAFIA_ROLES = {Role.DON, Role.MAFIA}
TOWN_ROLES  = {Role.TINCH_AXOLI, Role.KOMISSAR, Role.SERJANT, Role.SHIFOKOR,
               Role.ADVOKAT, Role.MASHUQA, Role.OMADLI, Role.KAMIKAZE, Role.DAYDI, Role.SUIDSID}

# ──────────────────────────────
# DO'KON
# ──────────────────────────────

SHOP_ITEMS = {
    "himoya":            {"name": "🛡 Himoya",             "price": 100, "currency": "coin",    "desc": "Bir marta hayotingizni saqlaydi"},
    "hujjat":            {"name": "📁 Hujjat",             "price": 190, "currency": "coin",    "desc": "Soxta hujjat — rolingizni yashiradi"},
    "ovozdan_himoya":    {"name": "⚖️ Ovozdan himoya",     "price": 1,   "currency": "diamond", "desc": "Kunduz osishdan bir marta qutqaradi"},
    "miltiq":            {"name": "🔫 Miltiq",             "price": 1,   "currency": "diamond", "desc": "Himoyali kishini ham o'ldiradi"},
    "doridan_himoya":    {"name": "💊 Doridan himoya",     "price": 100, "currency": "coin",    "desc": "Shifokor dorisidan himoya"},
    "maska":             {"name": "🎭 Maska",              "price": 100, "currency": "coin",    "desc": "Daydi sizni taniy olmaydi"},
    "qotildan_himoya":   {"name": "⛑️ Qotildan himoya",   "price": 2,   "currency": "diamond", "desc": "Qotildan cheksiz himoya"},
    "sirpanish_himoya":  {"name": "🪤 Sirpanishdan himoya","price": 300, "currency": "coin",    "desc": "Konchi roldagi sirpanishdan saqlaydi"},
    "geroydan_himoya":   {"name": "🔰 Geroydan himoya",    "price": 5,   "currency": "diamond", "desc": "Geroy hujumidan himoya"},
    "profil_almashish":  {"name": "🔄 Profil almashish",  "price": 5,   "currency": "diamond", "desc": "Profilingizni almashtiring"},
    "geroy":             {"name": "🥷 Geroy",              "price": 90,  "currency": "diamond", "desc": "Tong vaqtida ham otish imkoni"},
}

# ──────────────────────────────
# O'YINCHI
# ──────────────────────────────

@dataclass
class Player:
    user_id: int
    username: str
    full_name: str
    role: Optional[Role] = None
    is_alive: bool = True
    items: list = field(default_factory=list)
    coins: int = 0
    diamonds: int = 0
    night_action_done: bool = False
    protected: bool = False       # himoya predmeti bor
    vote_protected: bool = False  # ovozdan himoya

    @property
    def display_name(self):
        if self.username:
            return f"@{self.username}"
        return self.full_name

    def has_item(self, item_key: str) -> bool:
        return item_key in self.items

    def use_item(self, item_key: str) -> bool:
        if item_key in self.items:
            self.items.remove(item_key)
            return True
        return False

# ──────────────────────────────
# GAME PHASE
# ──────────────────────────────

class Phase(str, Enum):
    IDLE    = "idle"
    JOINING = "joining"
    DAY     = "day"
    VOTING  = "voting"
    NIGHT   = "night"
    ENDED   = "ended"

# ──────────────────────────────
# O'YIN
# ──────────────────────────────

@dataclass
class Game:
    chat_id: int
    phase: Phase = Phase.JOINING
    players: dict = field(default_factory=dict)  # user_id -> Player
    day_number: int = 0
    votes: dict = field(default_factory=dict)    # voter_id -> target_id
    night_kills: dict = field(default_factory=dict)  # role -> target_id
    night_heal: Optional[int] = None
    night_check: Optional[int] = None
    message_id: Optional[int] = None  # /join xabari ID

    def add_player(self, user: "types.User") -> bool:  # noqa
        if user.id in self.players:
            return False
        if len(self.players) >= 40:
            return False
        self.players[user.id] = Player(
            user_id=user.id,
            username=user.username or "",
            full_name=user.full_name,
        )
        return True

    def alive_players(self) -> list[Player]:
        return [p for p in self.players.values() if p.is_alive]

    def assign_roles(self):
        alive = list(self.players.values())
        random.shuffle(alive)
        n = len(alive)

        # Rol taqsimlash nisbati
        roles = []
        mafia_count = max(1, n // 4)
        roles += [Role.DON] + [Role.MAFIA] * (mafia_count - 1)
        if n >= 6:
            roles.append(Role.KOMISSAR)
        if n >= 8:
            roles.append(Role.SHIFOKOR)
        if n >= 10:
            roles.append(Role.QOTIL)
        if n >= 12:
            roles.append(Role.MASHUQA)
        if n >= 14:
            roles.append(Role.DAYDI)
        roles += [Role.TINCH_AXOLI] * (n - len(roles))

        random.shuffle(roles)
        for player, role in zip(alive, roles):
            player.role = role

    def check_winner(self) -> Optional[str]:
        alive = self.alive_players()
        mafia_alive = [p for p in alive if p.role in MAFIA_ROLES]
        town_alive  = [p for p in alive if p.role in TOWN_ROLES]
        qotil_alive = [p for p in alive if p.role == Role.QOTIL]

        if not mafia_alive and not qotil_alive:
            return "town"
        if len(mafia_alive) >= len(town_alive) and not qotil_alive:
            return "mafia"
        if len(alive) == 1 and qotil_alive:
            return "qotil"
        if not alive:
            return "draw"
        return None

    def reset_night(self):
        self.night_kills.clear()
        self.night_heal = None
        self.night_check = None
        for p in self.players.values():
            p.night_action_done = False
            p.protected = False

    def reset_votes(self):
        self.votes.clear()

    def tally_votes(self) -> Optional[int]:
        if not self.votes:
            return None
        count: dict[int, int] = {}
        for target in self.votes.values():
            count[target] = count.get(target, 0) + 1
        max_votes = max(count.values())
        candidates = [uid for uid, v in count.items() if v == max_votes]
        if len(candidates) == 1:
            return candidates[0]
        return None  # tenglik

    def kill_player(self, user_id: int) -> Optional[Player]:
        p = self.players.get(user_id)
        if not p or not p.is_alive:
            return None
        # Himoya tekshiruvi
        if p.has_item("himoya"):
            p.use_item("himoya")
            return None  # saqlanib qoldi
        if p.role == Role.OMADLI:
            return None
        if p.role == Role.KAMIKAZE:
            p.is_alive = False
            return p  # kamikaze triggeri handlers.py da qayta ishlaydi
        p.is_alive = False
        return p
