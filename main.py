import traceback
from aiogram import Bot, Dispatcher, types
from google.oauth2 import service_account
from google.oauth2 import service_account
import gspread_asyncio
from aiogram.fsm.storage.redis import (RedisStorage, DefaultKeyBuilder)
from google_connections import init_redis, load_szoreg_values, load_yandex_2023_values, load_pokazatel_504p_values, load_ucn2_values, load_schools_values, load_votes_values, load_survey_values, load_values, load_otpusk_data, SPREADSHEET_ID
from aiogram import types
from google.oauth2 import service_account
from config import bot_token
#from handlers import handle_szoreg_info, handle_schools_info, handle_survey_chart
from aiogram import Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage, BaseStorage
import re
import json
import time
import logging
import asyncio
import sys



response_storage = {}
info_text_storage = {}
is_main_menu_button_active = {}
user_messages = {}


storage = RedisStorage.from_url("redis://localhost:6379/2")
#storage = BaseStorage
bot = Bot(bot_token)


SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SERVICE_ACCOUNT_FILE = 'credentials.json'
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)






def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


async def on_startup():
    try:
        print('Initializing Redis...')
        #load_szoreg_values
        redis = await init_redis()

        agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: creds)
        gc = await agcm.authorize()
        spreadsheet = await gc.open_by_key(SPREADSHEET_ID)
        await load_values(spreadsheet, redis)
        await load_szoreg_values(spreadsheet, redis)
        await load_pokazatel_504p_values(spreadsheet, redis)
        await load_schools_values(spreadsheet, redis)
        #await load_yandex_2023_values(spreadsheet, redis)
        #await load_ucn2_values(spreadsheet, redis)
        #await load_survey_values(spreadsheet, redis)
        await load_votes_values(spreadsheet, redis)
          
        print('Initialization and data loading complete.')
    except Exception as e:
        print('Failed to initialize and load data:', str(e))
        traceback.print_exc()

async def main():
    
    dp = Dispatcher(storage = storage)
    from handlers import main_router
    from staff_directory import staff_router
    dp.include_router(main_router)
    dp.include_router(staff_router)
    
    await on_startup()
    print('Бот запущен и готов к приему сообщений')

  
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    #logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(main())

    

    



