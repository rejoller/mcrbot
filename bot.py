import asyncio
import logging
import time
from zoneinfo import ZoneInfo
import os

from aiogram import Dispatcher, Bot

from config import BOT_TOKEN, INTERVAL_MIN, UCN_INTERVAL_MIN
from aiogram.fsm.storage.redis import RedisStorage

from data_sources.yandex_disk import load_subsidies_file
from data_sources.ucn2025 import ucn_votes_updater
from data_sources.googlesheets import city_saver
from database.db import DataBaseSession
from database.engine import create_db, session_maker
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from cities import get_city_dict
from logger.logging_config import setup_logging
from logger.logging_middleware import LoggingMiddleware
from middlewares.citiesmiddleware import CitiesMiddleware
from handlers import setup_routers


redis_url = 'redis://localhost:6379/6'
storage = RedisStorage.from_url(redis_url)




async def on_startup():
    from database.engine import session_maker 
    from data_sources.googlesheets import szoreg_saver, schools_saver

    async with session_maker() as session:
        try:
            start_time = time.time()
            # await drop_db()
            await create_db()
            await city_saver(session)
            await szoreg_saver(session)
            await schools_saver(session)
            
            logging.info(f'on_startup завершена за {time.time() - start_time} секунд')
        except Exception as e:
            logging.error(f'Failed to initialize and load data: {e}', exc_info=True)
            


async def scheduled_ucn_votes_updater():
    async with session_maker() as session:
        await load_subsidies_file(session)
        await ucn_votes_updater(session)




async def main():
    setup_logging()
    city_dict = get_city_dict()
    cities = city_dict
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher(storage=storage)
    dp.update.middleware(DataBaseSession(session_pool=session_maker))
    dp.message.middleware(LoggingMiddleware())
    dp.update.middleware(CitiesMiddleware(session_pool=session_maker, cities=cities))
    scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Krasnoyarsk"))
    scheduler.add_job(on_startup, 'interval', minutes=INTERVAL_MIN)
    scheduler.add_job(scheduled_ucn_votes_updater, 'interval', minutes=UCN_INTERVAL_MIN)
    scheduler.start()
    router = setup_routers()
    dp.include_router(router)
    print('Бот запущен и готов к приему сообщений')
    await bot.delete_webhook(drop_pending_updates=True)
    await on_startup()
    await scheduled_ucn_votes_updater()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), skip_updates=True)
    

if __name__ == "__main__":
    asyncio.run(main())
    
