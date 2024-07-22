import asyncio
import logging
from zoneinfo import ZoneInfo
from aiogram import Dispatcher, Bot
import aiomonitor
import gspread_asyncio

from config import BOT_TOKEN, INTERVAL_MIN
from aiogram.fsm.storage.redis import RedisStorage

from data_sources.googlesheets import city_saver, szoreg_saver
from database.db import DataBaseSession
from database.engine import create_db, session_maker, drop_db
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from handlers.start_command import main_router
from logger.logging_config import setup_logging
from logger.logging_middleware import LoggingMiddleware

storage = RedisStorage.from_url("redis://localhost:6379/3")




async def on_startup():
    from database.engine import session_maker 
    from data_sources.googlesheets import szoreg_saver, schools_saver

    async with session_maker() as session:
        try:
            await drop_db()
            await create_db()
            await city_saver(session)
            await szoreg_saver(session)
            await schools_saver(session)
        except Exception as e:
            logging.error(f'Failed to initialize and load data: {e}', exc_info=True)




async def main():
    setup_logging()
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher(storage=storage)
    dp.update.middleware(DataBaseSession(session_pool=session_maker))
    dp.message.middleware(LoggingMiddleware())
    scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Krasnoyarsk"))
    scheduler.add_job(on_startup, 'interval', minutes=INTERVAL_MIN)
    scheduler.start()
    dp.include_router(main_router)
    print('Бот запущен и готов к приему сообщений')
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())