from aiogram import Dispatcher, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
from game import SHOP_ITEMS

# ──────────────────────────────
# ADMIN TEKSHIRUVI
# ──────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

# ──────────────────────────────
# FSM STATES
# ──────────────────────────────

class AdminStates(StatesGroup):
    waiting_user_id    = State()
    waiting_coin_amount   = State()
    waiting_diamond_amount = State()
    waiting_price_item = State()
    waiting_price_value = State()
    waiting_card       = State()
    waiting_max_players = State()
    waiting_group_id   = State()

# ──────────────────────────────
# FOYDALANUVCHILAR (handlers.py dan import qilinadi)
# Bu yerda global users dict ishlatiladi
# ──────────────────────────────

users: dict = {}   # user_id -> {"coins": int, "diamonds": int, "username": str}
selected_user: dict = {}  # admin_id -> target user_id

def get_or_create_user(user_id: int, username: str = ""):
    if user_id not in users:
        users[user_id] = {"coins": 0, "diamonds": 0, "username": username}
    return users[user_id]

# ──────────────────────────────
# ADMIN PANEL KLAVIATURA
# ──────────────────────────────

def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Foydalanuvchi boshqaruvi", callback_data="adm:users")],
        [InlineKeyboardButton(text="🛒 Do'kon narxlari",          callback_data="adm:prices")],
        [InlineKeyboardButton(text="⭐ Premium guruhlar",          callback_data="adm:premium")],
        [InlineKeyboardButton(text="💳 Karta rekvizitlari",       callback_data="adm:card")],
        [InlineKeyboardButton(text="⚙️ O'yin sozlamalari",        callback_data="adm:settings")],
    ])

def admin_user_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Pul berish",    callback_data="adm:give_coin")],
        [InlineKeyboardButton(text="💎 Olmoz berish",  callback_data="adm:give_diamond")],
        [InlineKeyboardButton(text="💵 Pul olish",     callback_data="adm:take_coin")],
        [InlineKeyboardButton(text="💎 Olmoz olish",   callback_data="adm:take_diamond")],
        [InlineKeyboardButton(text="🔙 Orqaga",        callback_data="adm:back")],
    ])

def prices_kb() -> InlineKeyboardMarkup:
    buttons = []
    for key, item in SHOP_ITEMS.items():
        cur = "💵" if item["currency"] == "coin" else "💎"
        price = config.SHOP_PRICES.get(key, {}).get("price", item["price"])
        buttons.append([InlineKeyboardButton(
            text=f"{item['name']} — {price}{cur}",
            callback_data=f"adm:price:{key}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="adm:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"👥 Max o'yinchilar: {config.MAX_PLAYERS}",
            callback_data="adm:max_players"
        )],
        [InlineKeyboardButton(
            text=f"☀️ Kun davomiyligi: {config.DAY_DURATION}s",
            callback_data="adm:day_dur"
        )],
        [InlineKeyboardButton(
            text=f"🌙 Tun davomiyligi: {config.NIGHT_DURATION}s",
            callback_data="adm:night_dur"
        )],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="adm:back")],
    ])

def premium_kb() -> InlineKeyboardMarkup:
    buttons = []
    for gid in config.PREMIUM_GROUPS:
        buttons.append([InlineKeyboardButton(
            text=f"❌ {gid}",
            callback_data=f"adm:rm_premium:{gid}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ Guruh qo'shish", callback_data="adm:add_premium")])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga",         callback_data="adm:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ──────────────────────────────
# REGISTER
# ──────────────────────────────

def register(dp: Dispatcher):

    # ── /admin ────────────────────────────────────────────
    @dp.message(Command("admin"))
    async def cmd_admin(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            await message.answer("❌ Sizda admin huquqi yo'q.")
            return
        await state.clear()
        await message.answer(
            "🔧 <b>Admin panel</b>\n\nNimani boshqarmoqchisiz?",
            reply_markup=admin_main_kb(),
            parse_mode="HTML"
        )

    # ── CALLBACK: ASOSIY MENYU ────────────────────────────
    @dp.callback_query(F.data == "adm:back")
    async def cb_back(call: types.CallbackQuery, state: FSMContext):
        if not is_admin(call.from_user.id):
            return
        await state.clear()
        await call.message.edit_text(
            "🔧 <b>Admin panel</b>\n\nNimani boshqarmoqchisiz?",
            reply_markup=admin_main_kb(),
            parse_mode="HTML"
        )

    # ── FOYDALANUVCHI BOSHQARUVI ──────────────────────────
    @dp.callback_query(F.data == "adm:users")
    async def cb_users(call: types.CallbackQuery, state: FSMContext):
        if not is_admin(call.from_user.id):
            return
        await state.set_state(AdminStates.waiting_user_id)
        await call.message.edit_text(
            "👤 Foydalanuvchi ID yoki @username yuboring:",
            parse_mode="HTML"
        )

    @dp.message(AdminStates.waiting_user_id)
    async def get_user_id(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        text = message.text.strip().lstrip("@")
        target = None

        if text.isdigit():
            uid = int(text)
            target = users.get(uid)
            if target:
                selected_user[message.from_user.id] = uid
        else:
            for uid, u in users.items():
                if u.get("username", "").lower() == text.lower():
                    target = u
                    selected_user[message.from_user.id] = uid
                    break

        if not target:
            await message.answer("❌ Foydalanuvchi topilmadi. Avval botga yozishi kerak.")
            return

        uid = selected_user[message.from_user.id]
        await state.clear()
        await message.answer(
            f"👤 <b>Foydalanuvchi:</b> @{target.get('username', uid)}\n"
            f"💵 Pul: {target['coins']}\n"
            f"💎 Olmoz: {target['diamonds']}\n\n"
            f"Nima qilmoqchisiz?",
            reply_markup=admin_user_kb(),
            parse_mode="HTML"
        )

    # ── PUL BERISH ────────────────────────────────────────
    @dp.callback_query(F.data == "adm:give_coin")
    async def cb_give_coin(call: types.CallbackQuery, state: FSMContext):
        if not is_admin(call.from_user.id):
            return
        await state.set_state(AdminStates.waiting_coin_amount)
        await state.update_data(action="give_coin")
        await call.message.edit_text("💵 Qancha pul bermoqchisiz? (son kiriting)")

    @dp.callback_query(F.data == "adm:take_coin")
    async def cb_take_coin(call: types.CallbackQuery, state: FSMContext):
        if not is_admin(call.from_user.id):
            return
        await state.set_state(AdminStates.waiting_coin_amount)
        await state.update_data(action="take_coin")
        await call.message.edit_text("💵 Qancha pul olmoqchisiz? (son kiriting)")

    @dp.message(AdminStates.waiting_coin_amount)
    async def process_coin(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        if not message.text.isdigit():
            await message.answer("❌ Faqat son kiriting.")
            return
        amount = int(message.text)
        data = await state.get_data()
        action = data.get("action")
        uid = selected_user.get(message.from_user.id)
        if not uid or uid not in users:
            await message.answer("❌ Foydalanuvchi tanlanmagan.")
            await state.clear()
            return

        if action == "give_coin":
            users[uid]["coins"] += amount
            await message.answer(f"✅ {amount} 💵 pul berildi.")
        else:
            users[uid]["coins"] = max(0, users[uid]["coins"] - amount)
            await message.answer(f"✅ {amount} 💵 pul olindi.")
        await state.clear()

    # ── OLMOZ BERISH ──────────────────────────────────────
    @dp.callback_query(F.data == "adm:give_diamond")
    async def cb_give_diamond(call: types.CallbackQuery, state: FSMContext):
        if not is_admin(call.from_user.id):
            return
        await state.set_state(AdminStates.waiting_diamond_amount)
        await state.update_data(action="give_diamond")
        await call.message.edit_text("💎 Qancha olmoz bermoqchisiz? (son kiriting)")

    @dp.callback_query(F.data == "adm:take_diamond")
    async def cb_take_diamond(call: types.CallbackQuery, state: FSMContext):
        if not is_admin(call.from_user.id):
            return
        await state.set_state(AdminStates.waiting_diamond_amount)
        await state.update_data(action="take_diamond")
        await call.message.edit_text("💎 Qancha olmoz olmoqchisiz? (son kiriting)")

    @dp.message(AdminStates.waiting_diamond_amount)
    async def process_diamond(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        if not message.text.isdigit():
            await message.answer("❌ Faqat son kiriting.")
            return
        amount = int(message.text)
        data = await state.get_data()
        action = data.get("action")
        uid = selected_user.get(message.from_user.id)
        if not uid or uid not in users:
            await message.answer("❌ Foydalanuvchi tanlanmagan.")
            await state.clear()
            return

        if action == "give_diamond":
            users[uid]["diamonds"] += amount
            await message.answer(f"✅ {amount} 💎 olmoz berildi.")
        else:
            users[uid]["diamonds"] = max(0, users[uid]["diamonds"] - amount)
            await message.answer(f"✅ {amount} 💎 olmoz olindi.")
        await state.clear()

    # ── DO'KON NARXLARI ───────────────────────────────────
    @dp.callback_query(F.data == "adm:prices")
    async def cb_prices(call: types.CallbackQuery):
        if not is_admin(call.from_user.id):
            return
        await call.message.edit_text(
            "🛒 <b>Do'kon narxlari</b>\nO'zgartirish uchun bosing:",
            reply_markup=prices_kb(),
            parse_mode="HTML"
        )

    @dp.callback_query(F.data.startswith("adm:price:"))
    async def cb_price_item(call: types.CallbackQuery, state: FSMContext):
        if not is_admin(call.from_user.id):
            return
        item_key = call.data.split(":")[2]
        await state.set_state(AdminStates.waiting_price_value)
        await state.update_data(item_key=item_key)
        item = SHOP_ITEMS.get(item_key, {})
        cur = "💵" if item.get("currency") == "coin" else "💎"
        current = config.SHOP_PRICES.get(item_key, {}).get("price", item.get("price", "?"))
        await call.message.edit_text(
            f"🛒 <b>{item.get('name', item_key)}</b>\n"
            f"Hozirgi narx: {current}{cur}\n\n"
            f"Yangi narxni kiriting:",
            parse_mode="HTML"
        )

    @dp.message(AdminStates.waiting_price_value)
    async def process_price(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        if not message.text.isdigit():
            await message.answer("❌ Faqat son kiriting.")
            return
        data = await state.get_data()
        item_key = data.get("item_key")
        config.SHOP_PRICES[item_key]["price"] = int(message.text)
        item = SHOP_ITEMS.get(item_key, {})
        await message.answer(f"✅ {item.get('name', item_key)} narxi {message.text} ga o'zgartirildi.")
        await state.clear()

    # ── KARTA REKVIZITLARI ────────────────────────────────
    @dp.callback_query(F.data == "adm:card")
    async def cb_card(call: types.CallbackQuery, state: FSMContext):
        if not is_admin(call.from_user.id):
            return
        await state.set_state(AdminStates.waiting_card)
        await call.message.edit_text(
            f"💳 <b>Hozirgi karta:</b>\n"
            f"{config.CARD_NUMBER}\n"
            f"{config.CARD_OWNER}\n\n"
            f"Yangi kartani kiriting:\n"
            f"<i>Format: 8600 1234 5678 9012 Ism Familiya</i>",
            parse_mode="HTML"
        )

    @dp.message(AdminStates.waiting_card)
    async def process_card(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        parts = message.text.strip().split()
        if len(parts) < 5:
            await message.answer("❌ Format: 8600 1234 5678 9012 Ism Familiya")
            return
        config.CARD_NUMBER = " ".join(parts[:4])
        config.CARD_OWNER  = " ".join(parts[4:])
        await message.answer(
            f"✅ Karta yangilandi:\n"
            f"💳 {config.CARD_NUMBER}\n"
            f"👤 {config.CARD_OWNER}"
        )
        await state.clear()

    # ── O'YIN SOZLAMALARI ─────────────────────────────────
    @dp.callback_query(F.data == "adm:settings")
    async def cb_settings(call: types.CallbackQuery):
        if not is_admin(call.from_user.id):
            return
        await call.message.edit_text(
            "⚙️ <b>O'yin sozlamalari</b>",
            reply_markup=settings_kb(),
            parse_mode="HTML"
        )

    @dp.callback_query(F.data == "adm:max_players")
    async def cb_max_players(call: types.CallbackQuery, state: FSMContext):
        if not is_admin(call.from_user.id):
            return
        await state.set_state(AdminStates.waiting_max_players)
        await state.update_data(setting="max_players")
        await call.message.edit_text(
            f"👥 Hozirgi max o'yinchilar: {config.MAX_PLAYERS}\n\nYangi sonni kiriting:"
        )

    @dp.callback_query(F.data == "adm:day_dur")
    async def cb_day_dur(call: types.CallbackQuery, state: FSMContext):
        if not is_admin(call.from_user.id):
            return
        await state.set_state(AdminStates.waiting_max_players)
        await state.update_data(setting="day_dur")
        await call.message.edit_text(
            f"☀️ Hozirgi kun davomiyligi: {config.DAY_DURATION} sekund\n\nYangi sonni kiriting:"
        )

    @dp.callback_query(F.data == "adm:night_dur")
    async def cb_night_dur(call: types.CallbackQuery, state: FSMContext):
        if not is_admin(call.from_user.id):
            return
        await state.set_state(AdminStates.waiting_max_players)
        await state.update_data(setting="night_dur")
        await call.message.edit_text(
            f"🌙 Hozirgi tun davomiyligi: {config.NIGHT_DURATION} sekund\n\nYangi sonni kiriting:"
        )

    @dp.message(AdminStates.waiting_max_players)
    async def process_setting(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        if not message.text.isdigit():
            await message.answer("❌ Faqat son kiriting.")
            return
        data = await state.get_data()
        setting = data.get("setting")
        val = int(message.text)

        if setting == "max_players":
            config.MAX_PLAYERS = val
            await message.answer(f"✅ Max o'yinchilar: {val} ga o'zgartirildi.")
        elif setting == "day_dur":
            config.DAY_DURATION = val
            await message.answer(f"✅ Kun davomiyligi: {val} sekund.")
        elif setting == "night_dur":
            config.NIGHT_DURATION = val
            await message.answer(f"✅ Tun davomiyligi: {val} sekund.")
        await state.clear()

    # ── PREMIUM GURUHLAR ──────────────────────────────────
    @dp.callback_query(F.data == "adm:premium")
    async def cb_premium(call: types.CallbackQuery):
        if not is_admin(call.from_user.id):
            return
        text = (
            f"⭐ <b>Premium guruhlar</b>\n"
            f"Jami: {len(config.PREMIUM_GROUPS)} ta\n\n"
            f"O'chirish uchun ID ni bosing:"
        ) if config.PREMIUM_GROUPS else "⭐ <b>Premium guruhlar yo'q</b>"
        await call.message.edit_text(text, reply_markup=premium_kb(), parse_mode="HTML")

    @dp.callback_query(F.data == "adm:add_premium")
    async def cb_add_premium(call: types.CallbackQuery, state: FSMContext):
        if not is_admin(call.from_user.id):
            return
        await state.set_state(AdminStates.waiting_group_id)
        await call.message.edit_text(
            "➕ Guruh ID sini kiriting:\n"
            "<i>(Guruhda /id buyrug'ini bering yoki guruh ID sini kiriting)</i>",
            parse_mode="HTML"
        )

    @dp.message(AdminStates.waiting_group_id)
    async def process_group_id(message: types.Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        text = message.text.strip()
        if not (text.lstrip("-").isdigit()):
            await message.answer("❌ Noto'g'ri ID. Faqat raqam kiriting (masalan: -1001234567890)")
            return
        gid = int(text)
        config.PREMIUM_GROUPS.add(gid)
        await message.answer(f"✅ {gid} premium guruhlar ro'yxatiga qo'shildi.")
        await state.clear()

    @dp.callback_query(F.data.startswith("adm:rm_premium:"))
    async def cb_rm_premium(call: types.CallbackQuery):
        if not is_admin(call.from_user.id):
            return
        gid = int(call.data.split(":")[2])
        config.PREMIUM_GROUPS.discard(gid)
        await call.answer(f"✅ {gid} o'chirildi.")
        text = (
            f"⭐ <b>Premium guruhlar</b>\n"
            f"Jami: {len(config.PREMIUM_GROUPS)} ta"
        ) if config.PREMIUM_GROUPS else "⭐ <b>Premium guruhlar yo'q</b>"
        await call.message.edit_text(text, reply_markup=premium_kb(), parse_mode="HTML")

    # ── /stats — umumiy statistika ────────────────────────
    @dp.message(Command("stats"))
    async def cmd_stats(message: types.Message):
        if not is_admin(message.from_user.id):
            return
        from handlers import games
        await message.answer(
            f"📊 <b>Statistika</b>\n\n"
            f"👥 Foydalanuvchilar: {len(users)}\n"
            f"🎮 Faol o'yinlar: {len(games)}\n"
            f"⭐ Premium guruhlar: {len(config.PREMIUM_GROUPS)}\n"
            f"💳 Karta: {config.CARD_NUMBER}",
            parse_mode="HTML"
        )
