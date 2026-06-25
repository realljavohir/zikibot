import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

import config
import handlers
import admin

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    try:
        # Token tekshiruvi
        if not config.BOT_TOKEN:
            logger.error("❌ BOT_TOKEN topilmadi! .env faylini tekshiring.")
            return
        
        logger.info("🤖 Bot ishga tushmoqda...")
        
        bot = Bot(
            token=config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode="HTML")
        )
        dp = Dispatcher(storage=MemoryStorage())
        
        # Handlerlarni ro'yxatdan o'tkazish
        admin.register(dp)
        handlers.register(dp)
        logger.info("✅ Handlerlar ro'yxatdan o'tdi")
        
        # Webhookni o'chirish (POLLING ishlatilganda)
        await bot.delete_webhook()
        logger.info("🔗 Webhook o'chirildi")
        
        # Bot haqida ma'lumot
        me = await bot.get_me()
        logger.info(f"✅ Bot ishga tushdi: @{me.username} (ID: {me.id})")
        
        # Pollingni boshlash
        logger.info("📡 Polling boshlandi...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Xatolik: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot to'xtatildi")
    except Exception as e:
        logger.error(f"❌ Bot ishga tushmadi: {e}")
