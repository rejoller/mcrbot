import asyncio
import logging
from zoneinfo import ZoneInfo
from aiogram import Dispatcher, Bot
import aiomonitor
import gspread_asyncio
import pandas as pd

from config import BOT_TOKEN, INTERVAL_MIN
from aiogram.fsm.storage.redis import RedisStorage

from data_sources.googlesheets import city_saver, szoreg_saver
from data_sources.yandex_disk import load_subsidies_file
from database.db import DataBaseSession
from database.engine import create_db, session_maker, drop_db
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from handlers.start_command import main_router
from handlers.city_searcher import city_router
from handlers.waiting_for_number import waiting_of_number_router
from logger.logging_config import setup_logging
from logger.logging_middleware import LoggingMiddleware
from middlewares.citiesmiddleware import CitiesMiddleware
from callbacks.espd import espd_router
from callbacks.schools import schools_router
from callbacks.survey.survey_tele2 import survey_tele2
from callbacks.survey.survey_beeline import survey_beeline
from callbacks.survey.survey_mts import survey_mts
from callbacks.survey.survey_megafon import survey_megafon

storage = RedisStorage.from_url("redis://localhost:6379/3")




async def on_startup():
    from database.engine import session_maker 
    from data_sources.googlesheets import szoreg_saver, schools_saver

    async with session_maker() as session:
        try:
            #await drop_db()
            #await create_db()
            #await city_saver(session)
            #await szoreg_saver(session)
            await schools_saver(session)
            #await load_subsidies_file(session)
        except Exception as e:
            logging.error(f'Failed to initialize and load data: {e}', exc_info=True)




async def main():
    setup_logging()
    cities = pd.read_json('cities.json')
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher(storage=storage)
    dp.update.middleware(DataBaseSession(session_pool=session_maker))
    dp.message.middleware(LoggingMiddleware())
    #dp.update.middleware(CitiesMiddleware(session_pool=session_maker, cities=cities))
    scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Krasnoyarsk"))
    scheduler.add_job(on_startup, 'interval', minutes=INTERVAL_MIN)
    scheduler.start()
    dp.include_router(main_router)
    dp.include_router(city_router)
    dp.include_router(waiting_of_number_router)
    dp.include_router(espd_router)
    dp.include_router(schools_router)
    dp.include_router(survey_tele2)
    dp.include_router(survey_mts)
    dp.include_router(survey_megafon)
    dp.include_router(survey_beeline)
    
    
    print('Бот запущен и готов к приему сообщений')
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())