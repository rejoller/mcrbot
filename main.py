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
from handlers import handle_additional_info, handle_szoreg_info, handle_schools_info, handle_survey_chart
from aiogram import Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.types import Message
import re
import json
import time
import logging
import asyncio
import sys
from handlers import main_group, main_router


response_storage = {}
info_text_storage = {}
is_main_menu_button_active = {}
user_messages = {}

bot = Bot(bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = RedisStorage.from_url("redis://localhost:6379/5")




SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SERVICE_ACCOUNT_FILE = 'credentials.json'
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)


def escape_markdown(text):
    markdown_escape_characters = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    return re.sub('([{}])'.format(''.join(markdown_escape_characters)), r'\\\1', text)


main_router.callback_query.register(handle_additional_info, lambda query: json.loads(query.data)["type"] == "additional_info")
main_router.callback_query.register(handle_szoreg_info, lambda query: json.loads(query.data)["type"] == "szoreg_info")

main_router.callback_query.register(handle_schools_info, lambda query: json.loads(query.data)["type"] == "schools_info")
main_router.callback_query.register(handle_survey_chart, lambda query: json.loads(query.data)["type"] == "survey_chart")






@main_router.message(Command('help'))
async def handle_help_command(message: types.Message):
    await log_user_data_from_message(message)
    help_text = (
        'Введи название населенного пункта или муниципального образования, чтобы получить информацию о связи'
        'Чтобы узнать, кто сегодня в отпуске, жми /otpusk\n\n'
        'Если остались вопросы, пиши @rejoller.')
    await message.reply(help_text)



@main_router.message(Command('otpusk'))
async def handle_otpusk_command(message: types.Message):
    await message.answer('Загружаю данные')
    otpusk_data = await load_otpusk_data()
    await filter_and_send_data(message, otpusk_data)


@main_router.message(Command('employees_vacation'))
async def handle_employees_vacation_command(message: types.Message):
    await message.answer('Загружаю данные')
    otpusk_data = await load_otpusk_data()
    employees_on_vacation, employees_starting_vacation_soon = get_employees_on_vacation(otpusk_data)

    if employees_on_vacation:
        await message.answer('Сотрудники, находящиеся в отпуске:')
        await message.answer('\n'.join(['\t'.join(row) for row in employees_on_vacation]), parse_mode=types.ParseMode.MARKDOWN)
    else:
        await message.answer('Сотрудников в отпуске нет.')

    if employees_starting_vacation_soon:
        await message.answer('Сотрудники, начинающие отпуск в ближайшие дни:')
        await message.answer('\n'.join(['\t'.join(row) for row in employees_starting_vacation_soon]), parse_mode=types.ParseMode.MARKDOWN)
    else:
        await message.answer('Сотрудников, начинающих отпуск в ближайшие дни, нет.')



async def handler_otpusk_message(message, employees_on_vacation):
    if len(employees_on_vacation) > 0:
        response = "Сотрудники, которые сегодня в отпуске:\n\n"
        for employee in employees_on_vacation:
            response += f"{employee[0]} ({employee[1]})\n"
        time.sleep(2)
        await message.reply(response)
    else:
        time.sleep(2)
        await message.reply("Сегодня никто не в отпуске.")



async def on_startup():
    try:
        print('Initializing Redis...')
        redis = await init_redis()
        agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: creds)
        gc = await agcm.authorize()
        spreadsheet = await gc.open_by_key(SPREADSHEET_ID)
        
        await load_values(spreadsheet, redis)
        await load_szoreg_values(spreadsheet, redis)
        await load_pokazatel_504p_values(spreadsheet, redis)
        await load_schools_values(spreadsheet, redis)
        await load_yandex_2023_values(spreadsheet, redis)
        await load_ucn2_values(spreadsheet, redis)
        await load_survey_values(spreadsheet, redis)
        await load_votes_values(spreadsheet, redis)
        
        


        print('Initialization and data loading complete.')
        
    except Exception as e:
        print('Failed to initialize and load data:', str(e))
        traceback.print_exc()


async def main():
    bot = Bot(bot_token)
    dp = Dispatcher()
    main_group(main_router) 
    dp.include_router(main_router)
    await on_startup()
    print('Бот запущен и готов к приему сообщений')

    # Запуск прослушивания обновлений
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    

    



