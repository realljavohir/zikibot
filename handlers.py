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

games: dict[int, Game] = {}
rate_limit: dict[int, list] = defaultdict(list)

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
    return "\n".join(lines) if lines else "Hali hech kim yoq"

def night_target_keyboard(game: Game, exclude_id: int = None) -> InlineKeyboardMarkup:
    buttons = []
    for p in game.alive_players():
        if p.user_id == exclude_id:
            continue
        buttons.append([InlineKeyboardButton(
            text=p.display_name,
            callback_data="night:" + str(p.user_id)
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def shop_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for key, item in SHOP_ITEMS.items():
        cur = "💵" if item["currency"] == "coin" else "💎"
        label = item["name"] + " — " + str(item["price"]) + cur
        buttons.append([InlineKeyboardButton(text=label, callback_data="buy:" + key)])
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
                mafia_team = "\n\n👥 Jamoa: " + ", ".join(teammates)
        text = "🎭 Sizning rolingiz:\n\n<b>" + role_name + "</b>\n\n" + role_desc + mafia_team
        try:
            await bot.send_message(player.user_id, text, parse_mode="HTML")
        except Exception:
            pass

async def run_day(bot: Bot, game: Game, chat_id: int):
    game.phase = Phase.DAY
    game.day_number += 1
    game.reset_votes()

    alive_lines = ["• " + p.display_name for p in game.alive_players()]
    alive_list = "\n".join(alive_lines)
    text = (
        "☀️ <b>Kun " + str(game.day_number) + " boshlandi!</b>\n\n"
        "Tirik oyinchilar:\n" + alive_list + "\n\n"
        "Muhokama qiling. " + str(config.DAY_DURATION) + " soniyadan song ovoz berish boshlanadi."
    )
    await bot.send_message(chat_id, text, parse_mode="HTML")
    await asyncio.sleep(config.DAY_DURATION)

    winner = game.check_winner()
    if winner:
        await end_game(bot, game, chat_id, winner)
        return

    game.phase = Phase.VOTING
    await bot.send_message(
        chat_id,
        "🗳 <b>Ovoz berish boshlandi!</b>\nKimni osib oldiramiz? /vote @username",
        parse_mode="HTML"
    )
    await asyncio.sleep(60)

    target_id = game.tally_votes()
    if target_id:
        target = game.players.get(target_id)
        if target:
            if target.has_item("ovozdan_himoya"):
                target.use_item("ovozdan_himoya")
                await bot.send_message(chat_id, "⚖️ " + target.display_name + " ovozdan himoya bilan qutuldi!")
            else:
                killed = game.kill_player(target_id)
                if killed:
                    role_name = ROLE_NAMES.get(killed.role, "?")
                    await bot.send_message(
                        chat_id,
                        "⚰️ <b>" + killed.display_name + "</b> osib oldirildi!\nRoli: " + role_name,
                        parse_mode="HTML"
                    )
                else:
                    await bot.send_message(chat_id, "🛡 " + target.display_name + " himoya bilan qutuldi!")
    else:
        await bot.send_message(chat_id, "🤝 Tenglik — bugun hech kim olmadi.")

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
        "🌙 <b>Tun boshlandi!</b>\n\nGuruhda gaplasha olmaysiz.\n"
        "(Faqat <code>!</code> bilan boshlanadigan xabarlar otadi)\n\n"
        "Kechalik harakatlar amalga oshirilmoqda...",
        parse_mode="HTML"
    )

    for player in game.alive_players():
        if player.role in MAFIA_ROLES:
            kb = night_target_keyboard(game, exclude_id=player.user_id)
            try:
                await bot.send_message(player.user_id, "🌙 Kimni oldiramiz?", reply_markup=kb)
            except Exception:
                pass
        elif player.role == Role.KOMISSAR:
            kb = night_target_keyboard(game, exclude_id=player.user_id)
            try:
                await bot.send_message(player.user_id, "🔍 Kimni tekshirasiz?", reply_markup=kb)
            except Exception:
                pass
        elif player.role == Role.SHIFOKOR:
            kb = night_target_keyboard(game)
            try:
                await bot.send_message(player.user_id, "💊 Kimni davolaysiz?", reply_markup=kb)
            except Exception:
                pass

    await asyncio.sleep(config.NIGHT_DURATION)

    results = []
    mafia_votes: dict[int, int] = {}
    for uid, target in game.night_kills.items():
        mafia_votes[target] = mafia_votes.get(target, 0) + 1

    if mafia_votes:
        top_target = max(mafia_votes, key=mafia_votes.get)
        if game.night_heal == top_target:
            results.append("💊 Shifokor kimnidir davoladi — u tirik qoldi!")
        else:
            killed = game.kill_player(top_target)
            if killed:
                role_name = ROLE_NAMES.get(killed.role, "?")
                results.append("⚰️ " + killed.display_name + " (" + role_name + ") oldirildi")
                if killed.role == Role.KAMIKAZE:
                    for uid in game.night_kills:
                        attacker = game.players.get(uid)
                        if attacker and attacker.is_alive:
                            attacker.is_alive = False
                            results.append("💣 Kamikaze! " + attacker.display_name + " ham halok boldi!")
            else:
                results.append("🛡 Hech kim olmadi (himoya)")

    if not results:
        results.append("😴 Tun tinch otti — hech kim olmadi")

    result_text = "☀️ <b>Tun tugadi!</b>\n\n" + "\n".join(results)
    await bot.send_message(chat_id, result_text, parse_mode="HTML")

    winner = game.check_winner()
    if winner:
        await end_game(bot, game, chat_id, winner)
        return

    await run_day(bot, game, chat_id)

async def end_game(bot: Bot, game: Game, chat_id: int, winner: str):
    game.phase = Phase.ENDED
    msgs = {
        "town":  "🏙 <b>Shahar galaba qildi!</b> Barcha mafia yoq qilindi!",
        "mafia": "🕴 <b>Mafia galaba qildi!</b> Shahar qolga tushdi!",
        "qotil": "🔪 <b>Qotil galaba qildi!</b> U yolgiz qoldi!",
        "draw":  "🤝 <b>Durrang!</b> Hamma oldi.",
    }
    role_lines = []
    for p in game.players.values():
        role_lines.append("• " + p.display_name + " — " + ROLE_NAMES.get(p.role, "?"))
    role_list = "\n".join(role_lines)
    winner_msg = msgs.get(winner, "Oyin tugadi!")
    await bot.send_message(
        chat_id,
        winner_msg + "\n\n<b>Rollar:</b>\n" + role_list,
        parse_mode="HTML"
    )
    del games[chat_id]

# ──────────────────────────────
# REGISTER
# ──────────────────────────────

def register(dp: Dispatcher):

    @dp.message(Command("join"))
    async def cmd_join(message: types.Message, bot: Bot):
        if not check_rate(message.from_user.id):
            return
        chat_id = message.chat.id
        if message.chat.type == "private":
            await message.answer("Bu komanda faqat guruhda ishlaydi.")
            return

        if chat_id not in games:
            games[chat_id] = Game(chat_id=chat_id)
        game = games[chat_id]

        if game.phase != Phase.JOINING:
            await message.answer("Oyin allaqachon boshlangan!")
            return

        added = game.add_player(message.from_user)
        if not added:
            if message.from_user.id in game.players:
                await message.answer("Siz allaqachon royxatdasiz!")
            else:
                await message.answer("Oyinchilar soni toldi! (Max: " + str(config.MAX_PLAYERS) + ")")
            return

        player_list = players_list_text(game)
        text = (
            "🎭 <b>Oyinga qoshilish boshlandi!</b>\n\n"
            "Oyinchilar royxati:\n" + player_list + "\n\n"
            "/game — oyinni boshlash\n"
            "/stop — bekor qilish"
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

    @dp.message(Command("game"))
    async def cmd_game(message: types.Message, bot: Bot):
        if not check_rate(message.from_user.id):
            return
        chat_id = message.chat.id
        game = games.get(chat_id)

        if not game or game.phase != Phase.JOINING:
            await message.answer("Avval /join bilan oyin oching.")
            return
        if len(game.players) < 4:
            await message.answer("Kamida 4 oyinchi kerak!")
            return

        game.assign_roles()
        await message.answer(
            "🎭 <b>Oyin boshlandi!</b>\n"
            "Oyinchilar: " + str(len(game.players)) + " kishi\n\n"
            "Rollar DM orqali yuborilmoqda...",
            parse_mode="HTML"
        )
        await announce_roles(bot, game)
        await asyncio.sleep(3)
        asyncio.create_task(run_day(bot, game, chat_id))

    @dp.message(Command("stop"))
    async def cmd_stop(message: types.Message):
        if not check_rate(message.from_user.id):
            return
        chat_id = message.chat.id
        if chat_id in games:
            del games[chat_id]
            await message.answer("🛑 Oyin toxtatildi.")
        else:
            await message.answer("Hozir faol oyin yoq.")

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
            await message.answer("Bunday oyinchi topilmadi.")
            return
        if target.user_id == message.from_user.id:
            await message.answer("Ozingizga ovoz bera olmaysiz.")
            return

        game.votes[message.from_user.id] = target.user_id
        await message.answer("✅ " + target.display_name + " uchun ovoz berdingiz.")

    @dp.message(Command("shop"))
    async def cmd_shop(message: types.Message):
        if not check_rate(message.from_user.id):
            return
        await message.answer(
            "🛒 <b>Dokon</b>\n\nBiror narsani tanlang:",
            reply_markup=shop_keyboard(),
            parse_mode="HTML"
        )

    @dp.message(Command("mybalance"))
    async def cmd_balance(message: types.Message):
        if not check_rate(message.from_user.id):
            return
        chat_id = message.chat.id
        game = games.get(chat_id)
        player = game.players.get(message.from_user.id) if game else None
        if not player:
            await message.answer("Siz hozir oyinda emassiz.")
            return
        await message.answer(
            "💰 <b>Balansingiz:</b>\n\n💵 Pul: " + str(player.coins) + "\n💎 Olmoz: " + str(player.diamonds),
            parse_mode="HTML"
        )

    @dp.message(Command("myrole"))
    async def cmd_myrole(message: types.Message, bot: Bot):
        if not check_rate(message.from_user.id):
            return
        chat_id = message.chat.id
        game = games.get(chat_id)
        player = game.players.get(message.from_user.id) if game else None
        if not player or not player.role:
            await message.answer("Siz hozir oyinda emassiz.")
            return
        try:
            role_name = ROLE_NAMES.get(player.role, "?")
            role_desc = ROLE_DESCRIPTIONS.get(player.role, "")
            await bot.send_message(
                message.from_user.id,
                "🎭 Sizning rolingiz: <b>" + role_name + "</b>\n\n" + role_desc,
                parse_mode="HTML"
            )
            await message.answer("✅ Rolingiz DM ga yuborildi.")
        except Exception:
            await message.answer("❌ DM ga yoza olmadim. Botga DM oching.")

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

    @dp.callback_query(F.data.startswith("vote:"))
    async def cb_vote(call: types.CallbackQuery):
        chat_id = call.message.chat.id
        game = games.get(chat_id)
        if not game or game.phase != Phase.VOTING:
            await call.answer("Ovoz berish vaqti emas.")
            return
        voter = game.players.get(call.from_user.id)
        if not voter or not voter.is_alive:
            await call.answer("Siz oyinda emassiz.")
            return
        target_id = int(call.data.split(":")[1])
        game.votes[call.from_user.id] = target_id
        target = game.players.get(target_id)
        await call.answer("✅ " + target.display_name + " uchun ovoz berdingiz.")

    @dp.callback_query(F.data.startswith("night:"))
    async def cb_night(call: types.CallbackQuery):
        user_id = call.from_user.id
        target_id = int(call.data.split(":")[1])

        game = next(
            (g for g in games.values() if user_id in g.players and g.phase == Phase.NIGHT),
            None
        )
        if not game:
            await call.answer("Oyin topilmadi.")
            return

        player = game.players.get(user_id)
        if not player or not player.is_alive or player.night_action_done:
            await call.answer("Siz bu kecha harakat qildingiz.")
            return

        target = game.players.get(target_id)
        if not target or not target.is_alive:
            await call.answer("Bu oyinchi tirik emas.")
            return

        player.night_action_done = True

        if player.role in MAFIA_ROLES:
            game.night_kills[user_id] = target_id
            await call.answer("🎯 Nishon: " + target.display_name)
            await call.message.edit_text("✅ Nishon tanlandi: " + target.display_name)
        elif player.role == Role.SHIFOKOR:
            game.night_heal = target_id
            await call.answer("💊 Davolandi: " + target.display_name)
            await call.message.edit_text("✅ Davolanuvchi: " + target.display_name)
        elif player.role == Role.KOMISSAR:
            game.night_check = target_id
            is_mafia = target.role in MAFIA_ROLES
            result = "🔴 MAFIA!" if is_mafia else "🟢 Tinch"
            await call.answer(result, show_alert=True)
            await call.message.edit_text("Tekshiruv natijasi: " + target.display_name + " — " + result)

    @dp.callback_query(F.data.startswith("buy:"))
    async def cb_buy(call: types.CallbackQuery):
        item_key = call.data.split(":")[1]
        item = SHOP_ITEMS.get(item_key)
        if not item:
            await call.answer("Mahsulot topilmadi.")
            return
        await call.answer(
            "✅ " + item["name"] + " sotib olindi!\n" + item["desc"],
            show_alert=True
        )
