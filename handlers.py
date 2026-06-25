import asyncio
import time
from collections import defaultdict
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
from game import Game, Phase, ROLE_NAMES, ROLE_DESCRIPTIONS, SHOP_ITEMS, MAFIA_ROLES, Role

# ──────────────────────────────
# STATE (xotirada)
# ──────────────────────────────

games: dict[int, Game] = {}          # chat_id -> Game
rate_limit: dict[int, list] = defaultdict(list)  # user_id -> [timestamps]

# ──────────────────────────────
# RATE LIMIT
# ──────────────────────────────

def check_rate(user_id: int) -> bool:
    now = time.time()
    timestamps = rate_limit[user_id]
    rate_limit[user_id] = [t for t in timestamps if now - t < 60]
    if len(rate_limit[user_id]) >= config.RATE_LIMIT:
        return False
    rate_limit[user_id].append(now)
    return True

# ──────────────────────────────
# HELPERS
# ──────────────────────────────

def players_list_text(game: Game) -> str:
    lines = []
    for i, p in enumerate(game.players.values(), 1):
        lines.append(f"{i}. {p.display_name}")
    return "\n".join(lines) if lines else "Hali hech kim yo'q"

def alive_keyboard(game: Game, exclude_id: int = None) -> InlineKeyboardMarkup:
    buttons = []
    for p in game.alive_players():
        if p.user_id == exclude_id:
            continue
        buttons.append([InlineKeyboardButton(
            text=p.display_name,
            callback_data=f"vote:{p.user_id}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def night_target_keyboard(game: Game, exclude_id: int = None) -> InlineKeyboardMarkup:
    buttons = []
    for p in game.alive_players():
        if p.user_id == exclude_id:
            continue
        buttons.append([InlineKeyboardButton(
            text=p.display_name,
            callback_data=f"night:{p.user_id}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def shop_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for key, item in SHOP_ITEMS.items():
        cur = "💵" if item["currency"] == "coin" else "💎"
        buttons.append([InlineKeyboardButton(
            text=f"{item['name']} — {item['price']}{cur}",
            callback_data=f"buy:{key}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def announce_roles(bot: Bot, game: Game):
    for player in game.players.values():
        role_name = ROLE_NAMES.get(player.role, "Noma'lum")
        role_desc = ROLE_DESCRIPTIONS.get(player.role, "")
        mafia_team = ""
        if player.role in MAFIA_ROLES:
            teammates = [
                p.display_name for p in game.players.values()
                if p.role in MAFIA_ROLES and p.user_id != player.user_id
            ]
            if teammates:
                mafia_team = f"\n\n👥 Jamoa: {', '.join(teammates)}"
        try:
            await bot.send_message(
                player.user_id,
                f"🎭 Sizning rolingiz:\n\n"
                f"<b>{role_name}</b>\n\n"
                f"{role_desc}"
                f"{mafia_team}",
                parse_mode="HTML"
            )
        except Exception:
            pass

async def run_day(bot: Bot, game: Game, chat_id: int):
    game.phase = Phase.DAY
    game.day_number += 1
    game.reset_votes()

    alive_list = "\n".join(f"• {p.display_name}" for p in game.alive_players())
    await bot.send_message(
        chat_id,
        f"☀️ <b>Kun {game.day_number} boshlandi!</b>\n\n"
        f"Tirik o'yinchilar:\n{alive_list}\n\n"
        f"Muhokama qiling. {config.DAY_DURATION} soniyadan so'ng ovoz berish boshlanadi.",
        parse_mode="HTML"
    )
    await asyncio.sleep(config.DAY_DURATION)

    winner = game.check_winner()
    if winner:
        await end_game(bot, game, chat_id, winner)
        return

    game.phase = Phase.VOTING
    await bot.send_message(
        chat_id,
        "🗳 <b>Ovoz berish boshlanди!</b>\n"
        "Kimni osib o'ldiramiz? /vote @username",
        parse_mode="HTML"
    )
    await asyncio.sleep(60)

    target_id = game.tally_votes()
    if target_id:
        target = game.players.get(target_id)
        if target:
            if target.has_item("ovozdan_himoya"):
                target.use_item("ovozdan_himoya")
                await bot.send_message(chat_id, f"⚖️ {target.display_name} ovozdan himoya bilan qutuldi!")
            else:
                killed = game.kill_player(target_id)
                if killed:
                    await bot.send_message(
                        chat_id,
                        f"⚰️ <b>{killed.display_name}</b> osib o'ldirildi!\n"
                        f"Roli: {ROLE_NAMES.get(killed.role, '?')}",
                        parse_mode="HTML"
                    )
                else:
                    await bot.send_message(chat_id, f"🛡 {target.display_name} himoya bilan qutuldi!")
    else:
        await bot.send_message(chat_id, "🤝 Tenglik — bugun hech kim o'lmadi.")

    winner = game.check_winner()
    if winner:
        await end_game(bot, game, chat_id, winner)
        return

    await run_night(bot, game, chat_id)

async def run_night(bot: Bot, game: Game, chat_id: int):
    game.phase = Phase.NIGHT
    game.reset_night()

    await bot.send_message(
        chat_id,
        "🌙 <b>Tun boshlandi!</b>\n\n"
        "Guruhda gaplasha olmaysiz.\n"
        "(Faqat <code>!</code> bilan boshlanadigan xabarlar o'tadi)\n\n"
        "Kechalik harakatlar amalga oshirilmoqda...",
        parse_mode="HTML"
    )

    for player in game.alive_players():
        if player.role in MAFIA_ROLES:
            kb = night_target_keyboard(game, exclude_id=player.user_id)
            try:
                await bot.send_message(
                    player.user_id,
                    "🌙 Kimni o'ldiramiz?",
                    reply_markup=kb
                )
            except Exception:
                pass
        elif player.role == Role.KOMISSAR:
            kb = night_target_keyboard(game, exclude_id=player.user_id)
            try:
                await bot.send_message(
                    player.user_id,
                    "🔍 Kimni tekshirasiz?",
                    reply_markup=kb
                )
            except Exception:
                pass
        elif player.role == Role.SHIFOKOR:
            kb = night_target_keyboard(game)
            try:
                await bot.send_message(
                    player.user_id,
                    "💊 Kimni davolaysiz?",
                    reply_markup=kb
                )
            except Exception:
                pass

    await asyncio.sleep(config.NIGHT_DURATION)

    # Tun natijalari
    results = []

    # Mafia o'ldiradi
    mafia_votes: dict[int, int] = {}
    for uid, target in game.night_kills.items():
        mafia_votes[target] = mafia_votes.get(target, 0) + 1

    killed_tonight = []
    if mafia_votes:
        top_target = max(mafia_votes, key=mafia_votes.get)
        if game.night_heal == top_target:
            results.append(f"💊 Shifokor kimnidir davoladi — u tirik qoldi!")
        else:
            killed = game.kill_player(top_target)
            if killed:
                killed_tonight.append(killed)
                results.append(f"⚰️ {killed.display_name} ({ROLE_NAMES.get(killed.role, '?')}) o'ldirildi")
                # Kamikaze tekshiruvi
                if killed.role == Role.KAMIKAZE:
                    for uid in game.night_kills:
                        attacker = game.players.get(uid)
                        if attacker and attacker.is_alive:
                            attacker.is_alive = False
                            results.append(f"💣 Kamikaze! {attacker.display_name} ham halok bo'ldi!")
            else:
                results.append("🛡 Hech kim o'lmadi (himoya)")

    if not results:
        results.append("😴 Tun tinch o'tdi — hech kim o'lmadi")

    await bot.send_message(
        chat_id,
        "☀️ <b>Tun tugadi!</b>\n\n" + "\n".join(results),
        parse_mode="HTML"
    )

    winner = game.check_winner()
    if winner:
        await end_game(bot, game, chat_id, winner)
        return

    await run_day(bot, game, chat_id)

async def end_game(bot: Bot, game: Game, chat_id: int, winner: str):
    game.phase = Phase.ENDED
    msgs = {
        "town":  "🏙 <b>Shahar g'alaba qildi!</b> Barcha mafiya yo'q qilindi!",
        "mafia": "🕴 <b>Mafia g'alaba qildi!</b> Shahar qo'lga tushdi!",
        "qotil": "🔪 <b>Qotil g'alaba qildi!</b> U yolg'iz qoldi!",
        "draw":  "🤝 <b>Durrang!</b> Hamma o'ldi.",
    }
    role_list = "\n".join(
        f"• {p.display_name} — {ROLE_NAMES.get(p.role, '?')}"
        for p in game.players.values()
    )
    await bot.send_message(
        chat_id,
        f"{msgs.get(winner, 'O\'yin tugadi!')}\n\n"
        f"<b>Rollar:</b>\n{role_list}",
        parse_mode="HTML"
    )
    del games[chat_id]

# ──────────────────────────────
# ROUTER SETUP
# ──────────────────────────────

def register(dp: Dispatcher):

    # ── /join ──────────────────────────────────────────────
    @dp.message(Command("join"))
    async def cmd_join(message: types.Message, bot: Bot):
        if not check_rate(message.from_user.id):
            return
        chat_id = message.chat.id
        if message.chat.type == "private":
            await message.answer("Bu komanda faqat guruhda ishlaydi.")
            return

        if chat_id not in games:
            game = Game(chat_id=chat_id)
            games[chat_id] = game
        else:
            game = games[chat_id]

        if game.phase not in (Phase.JOINING,):
            await message.answer("O'yin allaqachon boshlangan!")
            return

        added = game.add_player(message.from_user)
        if not added:
            if message.from_user.id in game.players:
                await message.answer("Siz allaqachon ro'yxatdasiz!")
            else:
                await message.answer(f"O'yinchilar soni to'ldi! (Max: {config.MAX_PLAYERS})")
            return

        text = (
            f"🎭 <b>O'yinga qo'shilish boshlandi!</b>\n\n"
            f"O'yinchilar ro'yxati:\n{players_list_text(game)}\n\n"
            f"/game — o'yinni boshlash\n"
            f"/stop — bekor qilish"
        )

        if game.message_id:
            try:
                await bot.edit_message_text(
                    text,
                    chat_id=chat_id,
                    message_id=game.message_id,
                    parse_mode="HTML"
                )
                await message.delete()
                return
            except Exception:
                pass

        sent = await message.answer(text, parse_mode="HTML")
        game.message_id = sent.message_id

    # ── /game ──────────────────────────────────────────────
    @dp.message(Command("game"))
    async def cmd_game(message: types.Message, bot: Bot):
        if not check_rate(message.from_user.id):
            return
        chat_id = message.chat.id
        game = games.get(chat_id)

        if not game or game.phase != Phase.JOINING:
            await message.answer("Avval /join bilan o'yin oching.")
            return
        if len(game.players) < 4:
            await message.answer("Kamida 4 o'yinchi kerak!")
            return

        game.assign_roles()
        await message.answer(
            f"🎭 <b>O'yin boshlanди!</b>\n"
            f"O'yinchilar: {len(game.players)} kishi\n\n"
            f"Rollar DM orqali yuborilmoqda...",
            parse_mode="HTML"
        )
        await announce_roles(bot, game)
        await asyncio.sleep(3)
        asyncio.create_task(run_day(bot, game, chat_id))

    # ── /stop ──────────────────────────────────────────────
    @dp.message(Command("stop"))
    async def cmd_stop(message: types.Message):
        if not check_rate(message.from_user.id):
            return
        chat_id = message.chat.id
        if chat_id in games:
            del games[chat_id]
            await message.answer("🛑 O'yin to'xtatildi.")
        else:
            await message.answer("Hozir faol o'yin yo'q.")

    # ── /vote ──────────────────────────────────────────────
    @dp.message(Command("vote"))
    async def cmd_vote(message: types.Message):
        if not check_rate(message.from_user.id):
            return
        chat_id = message.chat.id
        game = games.get(chat_id)
        if not game or game.phase != Phase.VOTING:
            return
        voter = game.players.get(message.from_user.id)
        if not voter or not voter.is_alive:
            return

        args = message.text.split()
        if len(args) < 2:
            await message.answer("Foydalanish: /vote @username")
            return

        username = args[1].lstrip("@").lower()
        target = next(
            (p for p in game.alive_players() if p.username.lower() == username),
            None
        )
        if not target:
            await message.answer("Bunday o'yinchi topilmadi.")
            return
        if target.user_id == message.from_user.id:
            await message.answer("O'zingizga ovoz bera olmaysiz.")
            return

        game.votes[message.from_user.id] = target.user_id
        await message.answer(f"✅ {target.display_name} uchun ovoz berdingiz.")

    # ── /shop ──────────────────────────────────────────────
    @dp.message(Command("shop"))
    async def cmd_shop(message: types.Message):
        if not check_rate(message.from_user.id):
            return
        await message.answer(
            "🛒 <b>Do'kon</b>\n\nBiror narsani tanlang:",
            reply_markup=shop_keyboard(),
            parse_mode="HTML"
        )

    # ── /mybalance ─────────────────────────────────────────
    @dp.message(Command("mybalance"))
    async def cmd_balance(message: types.Message):
        if not check_rate(message.from_user.id):
            return
        chat_id = message.chat.id
        game = games.get(chat_id)
        player = game.players.get(message.from_user.id) if game else None
        if not player:
            await message.answer("Siz hozir o'yinda emassiz.")
            return
        await message.answer(
            f"💰 <b>Balansingiz:</b>\n\n"
            f"💵 Pul: {player.coins}\n"
            f"💎 Olmoz: {player.diamonds}",
            parse_mode="HTML"
        )

    # ── /myrole ────────────────────────────────────────────
    @dp.message(Command("myrole"))
    async def cmd_myrole(message: types.Message, bot: Bot):
        if not check_rate(message.from_user.id):
            return
        chat_id = message.chat.id
        game = games.get(chat_id)
        player = game.players.get(message.from_user.id) if game else None
        if not player or not player.role:
            await message.answer("Siz hozir o'yinda emassiz.")
            return
        try:
            await bot.send_message(
                message.from_user.id,
                f"🎭 Sizning rolingiz: <b>{ROLE_NAMES.get(player.role, '?')}</b>\n\n"
                f"{ROLE_DESCRIPTIONS.get(player.role, '')}",
                parse_mode="HTML"
            )
            await message.answer("✅ Rolingiz DM ga yuborildi.")
        except Exception:
            await message.answer("❌ DM ga yoza olmadim. Botga DM oching.")

    # ── TUNDA XABARLARNI FILTRLASH ─────────────────────────
    @dp.message(F.chat.type.in_({"group", "supergroup"}))
    async def night_filter(message: types.Message):
        chat_id = message.chat.id
        game = games.get(chat_id)
        if not game or game.phase != Phase.NIGHT:
            return
        text = message.text or ""
        if not text.startswith("!"):
            try:
                await message.delete()
            except Exception:
                pass

    # ── CALLBACK: OVOZ BERISH (INLINE) ────────────────────
    @dp.callback_query(F.data.startswith("vote:"))
    async def cb_vote(call: types.CallbackQuery):
        chat_id = call.message.chat.id
        game = games.get(chat_id)
        if not game or game.phase != Phase.VOTING:
            await call.answer("Ovoz berish vaqti emas.")
            return
        voter = game.players.get(call.from_user.id)
        if not voter or not voter.is_alive:
            await call.answer("Siz o'yinda emassiz.")
            return
        target_id = int(call.data.split(":")[1])
        game.votes[call.from_user.id] = target_id
        target = game.players.get(target_id)
        await call.answer(f"✅ {target.display_name} uchun ovoz berdingiz.")

    # ── CALLBACK: TUN HARAKATI ─────────────────────────────
    @dp.callback_query(F.data.startswith("night:"))
    async def cb_night(call: types.CallbackQuery):
        user_id = call.from_user.id
        target_id = int(call.data.split(":")[1])

        # Qaysi o'yinda bu o'yinchi bor?
        game = next(
            (g for g in games.values() if user_id in g.players and g.phase == Phase.NIGHT),
            None
        )
        if not game:
            await call.answer("O'yin topilmadi.")
            return

        player = game.players.get(user_id)
        if not player or not player.is_alive or player.night_action_done:
            await call.answer("Siz bu kecha harakat qildingiz.")
            return

        target = game.players.get(target_id)
        if not target or not target.is_alive:
            await call.answer("Bu o'yinchi tirik emas.")
            return

        player.night_action_done = True

        if player.role in MAFIA_ROLES:
            game.night_kills[user_id] = target_id
            await call.answer(f"🎯 Nishon: {target.display_name}")
            await call.message.edit_text(f"✅ Nishon tanlandi: {target.display_name}")
        elif player.role == Role.SHIFOKOR:
            game.night_heal = target_id
            await call.answer(f"💊 Davolandi: {target.display_name}")
            await call.message.edit_text(f"✅ Davolanuvchi: {target.display_name}")
        elif player.role == Role.KOMISSAR:
            game.night_check = target_id
            is_mafia = target.role in MAFIA_ROLES
            result = "🔴 MAFIA!" if is_mafia else "🟢 Tinch"
            await call.answer(result, show_alert=True)
            await call.message.edit_text(f"Tekshiruv natijasi: {target.display_name} — {result}")

    # ── CALLBACK: DO'KON XARID ────────────────────────────
    @dp.callback_query(F.data.startswith("buy:"))
    async def cb_buy(call: types.CallbackQuery):
        item_key = call.data.split(":")[1]
        item = SHOP_ITEMS.get(item_key)
        if not item:
            await call.answer("Mahsulot topilmadi.")
            return

        # Hozircha bepul demo (to'lov tizimi keyinroq)
        await call.answer(
            f"✅ {item['name']} sotib olindi!\n{item['desc']}",
            show_alert=True
        )
