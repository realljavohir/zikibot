import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

import config
import handlers
import admin

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher(storage=MemoryStorage())
    admin.register(dp)
    handlers.register(dp)

    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
