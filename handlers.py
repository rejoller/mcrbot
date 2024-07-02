import functools
from icecream import ic
from io import BytesIO
from zoneinfo import ZoneInfo
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReactionTypeEmoji, InputFile, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types, Router, F
from aiogram.types.web_app_data import WebAppData
from aiogram.types.web_app_info import WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import Message
from datetime import datetime, time, timedelta, timezone
import csv
from pandas.plotting import table
from matplotlib import pyplot as plt
from images import default_profile, tower, complete_uploading_vacations
from mongo_connect import save_staff_dict, save_survey_results
from google_connections import get_authorized_client_and_spreadsheet, search_subsidies_info, search_yandex_2023_values, search_in_pokazatel_504p, search_in_ucn2, search_schools_values, load_otpusk_data, search_values, search_values_levenshtein, search_szoreg_values, get_value, init_redis
from mongo_connect import search_survey_results
from openai_file import handle_digital_ministry_info
import asyncio
from additional import split_message, create_excel_file_2
import json
import html
import re
import logging
import os
import traceback
import tempfile
import shutil
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import json
from animations_providers import (megafon_id, mts_id, tele2_id, beeline_id)
from main import bot
from google_connections import init_redis



info_text_storage = {}
user_messages = {}
additional_info_storage = {}
szoreg_info_storage = {}
schools_info_storage = {}
message_storage = {}
survey_data_storage = {}
response_storage = {}
main_router = Router()


def log_user_data(user_id, first_name, last_name, username, message_text):
    file_path = 'users_data.csv'
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Проверяем, существует ли файл. Если нет, создаем его с заголовками
    try:
        with open(file_path, 'x', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'User ID', 'First Name',
                            'Last Name', 'Username', 'Message'])
    except FileExistsError:
        pass

    # Записываем данные пользователя в файл
    with open(file_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([current_time, user_id, first_name,
                        last_name, username, message_text])


async def log_user_data_from_message(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username
    message_text = message.text

    log_user_data(user_id, first_name, last_name, username, message_text)


class Form(StatesGroup):
    default = State()
    waiting_for_number = State()
    development = State()


class Survey(StatesGroup):
    tele2_level = State()
    tele2_quality = State()
    megafon_level = State()
    megafon_quality = State()
    mts_level = State()
    mts_quality = State()
    beeline_level = State()
    beeline_quality = State()


def get_employees_on_vacation(otpusk_data, days_ahead=3):
    today = datetime.today().date()
    
    future_vacation_start = today + timedelta(days=days_ahead)
    employees_on_vacation = []
    employees_starting_vacation_soon = []

    for index, row in otpusk_data.iterrows():
        start_date = datetime.strptime(
            row['Дата начала фактического отпуска'], "%d.%m.%Y").date()
        
        end_date = datetime.strptime(
            row['Дата конца фактического отпуска'], "%d.%m.%Y").date()

        if start_date <= today <= end_date:
            employees_on_vacation.append(row)

        if today < start_date <= future_vacation_start:
            employees_starting_vacation_soon.append(row)

    
    return employees_on_vacation, employees_starting_vacation_soon



@main_router.message(Command('development'))
async def handle_development(message: types.Message, state: FSMContext):
    await state.set_state(Form.development)
    await log_user_data_from_message(message)
    builder = InlineKeyboardBuilder()

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"Субсидия", callback_data='subsidies')],
        [InlineKeyboardButton(
            text=f"Главное меню", callback_data='main_menu')]
        
    ])
    builder.attach(InlineKeyboardBuilder.from_markup(markup))


    await message.answer_photo(photo=tower, caption=f'Вы находитесь в меню реализации проектов.\n'
                               'Выберите проект или можете выйти в главное меню', reply_markup=markup)
    
@functools.lru_cache(maxsize=10)
@main_router.callback_query(F.data.contains("subsidies"), StateFilter(Form.development))
async def handle_subsidies_query(query: types.CallbackQuery, state: FSMContext):
    
    from main import bot
    await bot.send_chat_action(action='upload_photo', chat_id = query.from_user.id)
    subsidies_df = await search_subsidies_info()
    
    
    subsidies_df = subsidies_df.dropna(subset=['МО', 'Н.п.'])
    def format_date(date_str):
        try:
            return pd.to_datetime(date_str).strftime('%d.%m')
        except ValueError:
            return date_str

    # Применение функции форматирования к столбцам с датами
    date_columns = ['Установка \nАМС', 'Монтаж \nБС', 'Запуск \nуслуг']
    for col in date_columns:
        subsidies_df[col] = subsidies_df[col].apply(format_date)

    subsidies_df['Волна'] = subsidies_df.apply(lambda x: '1' if x['НПА'] == '1013-п' else '2', axis=1)
    
    subsidies_df = subsidies_df.fillna('нет данных')
    subsidies_df = subsidies_df.rename(columns ={'МО':'Муниципалитет', 'Н.п.':'Населенный пункт','Установка \nАМС':'Установка АМС', 'Монтаж \nБС':'Монтаж БС', 'Запуск \nуслуг':'Запуск услуг'})
    subsidies_df.style.set_properties(subset=['Волна'], **{'width': '20px'})
    subsidies_response = subsidies_df[['Волна','Муниципалитет', 'Населенный пункт','Аренда земли', 'Установка АМС', 'Монтаж БС', 'Запуск услуг']]
    
    
    subsidies_response.style.hide(axis='index')
    subsidies_response = subsidies_response.reset_index(drop=True)
    
    subsidies_response.to_excel('subsid.xlsx')
    
    
    fig, ax = plt.subplots()
    ax.axis('tight')
    ax.axis('off')
    
    column_widths = [0.5 if col in ['Муниципалитет', 'Населенный пункт'] else 0.1 if col == 'Волна' else 0.4 for col in subsidies_response.columns]
    

    tbl = table(ax, subsidies_response, loc='center', colWidths=column_widths, cellLoc='center')  # Сначала задаем общее выравнивание для всех ячеек

    # Настраиваем выравнивание для отдельных столбцов
    for i, col in enumerate(subsidies_response.columns):
        cell = tbl[(0, i)]
        cell.set_text_props(weight='bold', color='white')
        cell.set_facecolor('#40466e')
        cell.set_fontsize(10)

    # Настраиваем выравнивание для отдельных ячеек
    columns_to_align_left = ['Муниципалитет', 'Населенный пункт']
    for key, cell in tbl.get_celld().items():
        row, col = key
        if col == -1:  # Пропускаем заголовок строк
            continue
        column_name = subsidies_response.columns[col]
        if column_name in columns_to_align_left:
            cell.set_text_props(ha='left')
        # Добавляем границы ячеек
        cell.set_edgecolor('black')
        cell.set_linewidth(0.5)

    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.3, 1.3)

    fig.savefig('mytable.png', bbox_inches='tight', dpi=400)
    plt.close(fig) 

    # Отправка изображения с помощью aiogram
    photo = FSInputFile('mytable.png')
    subs_table = FSInputFile('subsid.xlsx')


    builder = InlineKeyboardBuilder()

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"Главное меню", callback_data='main_menu')]
        
    ])
    builder.attach(InlineKeyboardBuilder.from_markup(markup))

    
    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
    await query.message.answer_photo(photo, caption='Реализация предоставления субсидии малочисленным населенным пунктам', reply_markup=markup)



@main_router.callback_query(F.data.contains("main_menu"))
async def handle_subsidies_query(query: types.CallbackQuery, state: FSMContext):
    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
    await state.clear()
    await query.message.answer(f'Вы в главном меню. \nВведите название населенного пункта, чтобы получить '
                               'информацию о качестве связи или пройти опрос\n\n**Также есть команды:** \n/otpusk - узнать кто в отпуске\n'
                               '/development - информация о проектах министерства', parse_mode='Markdown')


@main_router.message(Command('help'))
async def handle_help(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(f'\nВведите название населенного пункта, чтобы получить '
                               'информацию о качестве связи или пройти опрос\n\n**Также есть команды:** \n/otpusk - узнать кто в отпуске\n'
                               '/development - информация о проектах министерства', parse_mode='Markdown')


@main_router.message(Command('bi'))
async def handle_bi_command(message: types.Message):

    builder = InlineKeyboardBuilder()

    builder.button(text="test webapp", web_app=WebAppInfo(
        url="https://rejoller.pythonanywhere.com/"))

    keyboard = builder.as_markup()

    await message.answer(text='BI', reply_markup=keyboard)


@main_router.message(Command('otpusk'))
async def handle_otpusk_command(message: types.Message, days_ahead=14):

    await log_user_data_from_message(message)
    otpusk_data = await load_otpusk_data()

    employees_on_vacation, employees_starting_vacation_soon = get_employees_on_vacation(
        otpusk_data, days_ahead)

    response = ""

    if employees_on_vacation:
        response += f'<i>Сегодня в отпуске</i>🏝\n\n'
        for row in employees_on_vacation:
            response += f"<b>{row.iloc[0]}</b>\n"
            response += f"начало отпуска: {row.iloc[1]}\n"
            response += f"окончание отпуска: {row.iloc[2]}\n\n"

    if employees_starting_vacation_soon:
        response += f"\n<i>Сотрудники, уходящие в отпуск в ближайшие <b>{days_ahead}</b> дней</i>\n\n"
        for emp_row in employees_starting_vacation_soon:
            response += f"<b>{emp_row.iloc[0]}</b>\n"
            response += f"начало отпуска: {emp_row.iloc[1]}\n"
            response += f"окончание отпуска: {emp_row.iloc[2]}\n\n"

    if not response:
        response = f"Сегодня никто не в отпуске, и никто не уходит в отпуск в ближайшие {days_ahead} дней."

    messages = split_message(response)

    for msg in messages:

        await bot.send_message(message.chat.id, msg, parse_mode='HTML')


@main_router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    await state.clear()

    user_first_name = message.from_user.first_name
    await message.answer(
        f'Я бот министерства цифрового развития Красноярского края!'
        '\n Введи наименование любого населенного пункта края, '

        'чтобы получить информацию о связи в нем или оставить обратную связь о качестве услуг\n\n'
        'Также есть команды: /otpusk - узнать кто в отпуске\n'
                               '/development - информация о проектах министерства'
        )
    
    await state.clear()
    


@main_router.message(F.location)
async def handle_location(message: types.Message, state: FSMContext):
    
    from mongo_connect import save_user_location
    user_id = message.from_user.id
    location_data = {"latitude": message.location.latitude,
                     "longitude": message.location.longitude}
    await message.answer('спасибо😉')
    await save_user_location(user_id, location_data)


@main_router.message(F.contact)
async def handle_contacts(message: types.Message, state: FSMContext):
    
    from mongo_connect import save_user_contact
    user_id = message.from_user.id
    contact_data = {"contact": message.contact.phone_number}
    await message.answer('спасибо😉')
    await save_user_contact(user_id, contact_data)


@main_router.message(F.animation)
async def echo_gif(message: Message):
    file_id = message.animation.file_id
    print(file_id)
    await message.answer(message.animation.file_id)


@main_router.message(F.document)
async def contacts_handler(message: types.Message):
    user_name = message.from_user.first_name
    document = message.document

    
    file_name = document.file_name.lower()
    if "рафик" in file_name:

        directory = 'otpusk'
        if not os.path.exists(directory):
            os.mkdir(directory)

        destination = os.path.join(os.getcwd(), directory, file_name)
        file_info = await bot.get_file(document.file_id)
        await bot.download_file(file_info.file_path, destination)
        await message.answer_photo(caption=f'Файл с отпусками загружен.\nХорошего дня тебе, {user_name}😊',
                                   photo=complete_uploading_vacations)

        

    if "убсид" in file_name:

        directory = 'subsidies'
        if not os.path.exists(directory):
            os.mkdir(directory)

        subs_destination = os.path.join(os.getcwd(), directory, file_name)

        file_info = await bot.get_file(document.file_id)

        await bot.download_file(file_info.file_path, subs_destination)
        await message.answer(f'Файл {file_name} загружен! \nХорошего дня тебе, {user_name} 😊')


@main_router.message(F.photo)
async def get_photo_id(message: Message):
    await message.reply(text=f"{message.photo[-1].file_id}")


@main_router.message(~StateFilter(Form.waiting_for_number), F.text)
async def handle_text(message: Message, state: FSMContext):

    reaction_emoji = ReactionTypeEmoji(emoji='🤓')
    
    await message.react(reaction=[reaction_emoji], is_big=True)
    redis = await init_redis()
    global info_text_storage
    await state.set_state(Form.default)
    await log_user_data_from_message(message)


    votes_response = ""
    response = ''
    ucn2_response = ""
    operators_response = ''
    survey_results_values = ''

    gc, spreadsheet = await get_authorized_client_and_spreadsheet()

    found_values_a = await search_values(message.text, redis)

    if not found_values_a:
        # Проверяем метод Левенштейна с 70% совпадениями
        levenshtein_matches = await search_values_levenshtein(message.text, spreadsheet, threshold=0.4, max_results=5)

        if levenshtein_matches:
            # Используем множество, чтобы убрать повторяющиеся значения
            unique_matches = set(levenshtein_matches)
            first_match = list(unique_matches)  # Преобразуем обратно в список
            # Создаем строки с обратными кавычками для каждого значения
            formatted_matches = "\n".join(
                [f'`{match}`' for match in first_match])
            await bot.send_message(message.chat.id, f'Проверьте правильность написания и попробуйте еще раз. Возможно вы имели в виду:\n(нажмите на населенный пункт, чтобы скопировать)\n\n{formatted_matches}', parse_mode='Markdown')
        else:
            await bot.send_message(message.chat.id, 'Не удалось найти информацию по данному запросу.\nПроверьте, правильно ли введено название населенного пункта и попробуйте еще раз')
        return

    allowed_users = {1}
    if found_values_a:
        found_values = found_values_a
        await state.update_data(found_values=found_values)
        await state.update_data(np=found_values[0][4])

        if len(found_values) == 1:
            # Широта находится в столбце H таблицы goroda2.0
            latitude = found_values[0][7]
            longitude = found_values[0][8]

            yandex_2023_response = ''
            pokazatel_504p_lines = []

            async with asyncio.TaskGroup() as tg:
                yandex_2023_task = tg.create_task(
                    search_yandex_2023_values(found_values[0][4], redis))
                pokazatel_504p_task = tg.create_task(
                    search_in_pokazatel_504p(found_values[0][4]))
                ucn2_task = tg.create_task(
                    search_in_ucn2(found_values[0][4], redis))
                survey_results_task = tg.create_task(
                    search_survey_results(np=found_values[0][4]))
                szoreg_task = tg.create_task(
                    search_szoreg_values(found_values[0][4], redis))
                schools_task = tg.create_task(
                    search_schools_values(found_values[0][4], redis))

                yandex_2023_values = await yandex_2023_task
                pokazatel_504p_values = await pokazatel_504p_task
                
                ucn2_values = await ucn2_task
                survey_results_values = await survey_results_task
                szoreg_values = await szoreg_task
                schools_values = await schools_task

            if found_values_a:
                for row in found_values_a:
                    # Создаем словарь с операторами и их значениями, используя метод get для безопасного обращения к элементам списка
                    operators = {
                        "Tele2": row[39] if len(row) > 39 else None,
                        "Мегафон": row[40] if len(row) > 40 else None,
                        "Билайн": row[41] if len(row) > 41 else None,
                        "МТС": row[42] if len(row) > 42 else None,
                    }

                   # operators_response = '\nОценка жителей:\n'

                    # Список для хранения ответов от операторов
                    operator_responses = []

                    for operator_name, operator_value in operators.items():

                        # Проверка на наличие значения (не None и не пустая строка)
                        if operator_value:
                            # Переводим значение в строку, чтобы избежать ошибок при выполнении метода replace
                            operator_value_str = str(operator_value)

                            # Пытаемся найти качество сигнала
                            signal_quality = re.search(
                                r'Отсутствует|Низкое|Среднее|Хорошее', operator_value_str, re.IGNORECASE)
                            if signal_quality:
                                signal_quality = signal_quality.group()
                                if "Отсутствует" in signal_quality:
                                    signal_level = "🔴Отсутствует"
                                elif "Низкое" in signal_quality:
                                    signal_level = "🟠Низкое"
                                elif "Среднее" in signal_quality:
                                    signal_level = "🟡Среднее"
                                elif "Хорошее" in signal_quality:
                                    signal_level = "🟢Хорошее"
                                else:
                                    signal_level = "❓Неизвестно"

                                # Заменяем найденное качество сигнала на его эмодзи-эквивалент
                                operator_value_str = operator_value_str.replace(
                                    signal_quality, signal_level)
                            else:
                                operator_value_str = operator_value_str

                            operator_value_str = operator_value_str.replace(
                                "(", " ").replace(")", " ")
                            operator_responses.append(
                                f'{operator_name}: {operator_value_str}\n')
                        else:

                            continue

                    if not operator_responses:
                        operators_response += 'Нет данных\n'
                    else:
                        operators_response += ''.join(operator_responses)

                    # response += operators_response

            if yandex_2023_values:
                yandex_2023_response = '\n\n\n<b>Информация из таблицы 2023</b>\n\n'
                for row in yandex_2023_values:
                    yandex_2023_response += f'Тип подключения: {row[4]}\nОператор: {row[15]}\nСоглашение: {row[7]}\nПодписание соглашения с МЦР: {row[8]}\nПодписание соглашения с АГЗ: {row[9]}\nДата подписания контракта: {row[11]}\nДата установки АМС: {row[12]}\nДата монтажа БС: {row[13]}\nЗапуск услуг: {row[14]}\n\n'
            if pokazatel_504p_values is not None and not pokazatel_504p_values.empty:
                pokazatel_504p_lines = []

                for i in range(10, 14):
                    if i < len(pokazatel_504p_values.columns):
                        value = pokazatel_504p_values.iloc[0, i]
                        if pd.notna(value) and value.strip():
                            if "Хорошее" in value:
                                value = value.replace("Хорошее", "🟢Хорошее")
                            if "Низкое" in value:
                                value = value.replace("Низкое", "🟠Низкое")
                            pokazatel_504p_lines.append(value)

                # Выводим обработанные строки для проверки
                print(pokazatel_504p_lines)
            if ucn2_values:
                for row in ucn2_values:
                    ucn2_response = ''

                    if 4 < len(row) and row[4]:  # Проверка наличия значения
                        ucn2_response += '  Информация от Теле2:\n    -СМР: ' + \
                            row[4] + '\n'
                    if 5 < len(row) and row[5]:  # Проверка наличия значения
                        ucn2_response += '    -Запуск: ' + row[5] + '\n'
                    if 6 < len(row) and row[6]:  # Проверка наличия значения
                        ucn2_response += '    -Комментарии: ' + row[6] + '\n'

                    if ucn2_response:  # Если ucn2_response не пуст, добавить вводную строку в начало
                        ucn2_response = '\n\n\n<b>УЦН 2.0 2023</b>\n' + ucn2_response
                        response += ucn2_response

                response += ucn2_response
            pokazatel_504p_response = "\n".join(
                pokazatel_504p_lines) if pokazatel_504p_lines else "🔴отсутствует"

            if "4G" in pokazatel_504p_response:
                votes_response = ""
            else:

                try:
                    # Убедитесь, что у вас достаточно данных в строке
                    if len(found_values[0]) > 38:
                        votes = found_values[0][34] or "неизвестно"
                        update_time = found_values[0][35] or "неизвестно"
                        rank = found_values[0][36] or "неизвестно"
                        same_votes_np = found_values[0][38] or "неизвестно"

                        if votes != "неизвестно" and update_time != "неизвестно" and rank != "неизвестно" and same_votes_np != "неизвестно":
                            votes_response = f'\n\n<b>Голосование УЦН 2.0 2024</b>\n\n📊Количество голосов: <b>{votes}</b> (такое же количество голосов имеют {same_votes_np} населённых пунктов)\n🏆Место в рейтинге: {rank}\nДата обновления информации: {update_time}'
                        else:
                            print(
                                "Debug: Не все данные для блока голосования были найдены.")
                except Exception as e:
                    print(
                        f"Debug: Ошибка при извлечении данных о голосах: {e}")

            response = f'<b>{found_values[0][1]}</b>'

            try:
                selsovet_info, tanya_sub_info_year, tanya_sub_info_provider, taksofony_info, arctic_info, internet_info, population_2010, population_2020, itog_ucn_2023, tv = await asyncio.gather(
                    get_value(found_values[0], 20),
                    get_value(found_values[0], 13),
                    get_value(found_values[0], 14),
                    get_value(found_values[0], 12),
                    get_value(found_values[0], 6),
                    get_value(found_values[0], 9),
                    get_value(found_values[0], 2),
                    get_value(found_values[0], 5),
                    get_value(found_values[0], 24),
                    get_value(found_values[0], 43),
                    return_exceptions=True  # Возврат исключений как объектов
                )
            except Exception as e:
                print(f"Произошла ошибка: {e}")

            if selsovet_info:
                response += f'\n{selsovet_info}'
            if arctic_info:
                response += f'\n❄️️арктическая зона❄️️'
            response += f'\n\n👥население 2010 г:{population_2010} чел.\n👥население 2020 г: {population_2020} чел.'

            if taksofony_info:
                response += f'\n☎️таксофон: {taksofony_info}'

            response += f'\n🌐интернет: {internet_info}️'
            if tv:
                response += f'\n📺телевидение: {tv}\n'
            response += f'⠀'
            response += f'<pre>📱Сотовая связь:\n{pokazatel_504p_response}</pre>\n'

            if tanya_sub_info_year and tanya_sub_info_provider:
                response += f'\n\nнаселенный пункт был подключен в рамках государственной программый "Развитие информационного общества" в {tanya_sub_info_year} году, оператор {tanya_sub_info_provider}'

            if itog_ucn_2023:
                response += f'\n\nкомментарий Минцифры России об УЦН 2024: {itog_ucn_2023}'
           # response += f'\n{operators_response}\n'
            response += f'{yandex_2023_response}{ucn2_response}{votes_response}\n'

            info_text_storage[message.chat.id] = response

            await bot.send_location(message.chat.id, latitude, longitude, heading=10, proximity_alert_radius=200)

            messages = split_message(response)
            survey_builder = InlineKeyboardBuilder()
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"Пройти опрос", callback_data='start_survey')]
            ])
            survey_builder.attach(InlineKeyboardBuilder.from_markup(markup))
            
            response += f'\nУзнать о проектах министерства \n/development'
            await bot.send_message(message.chat.id, response, parse_mode='HTML', disable_web_page_preview=True, reply_markup=survey_builder.as_markup(), message_effect_id='5046509860389126442')

            # if message.from_user.id in allowed_users:
            # button_digital_ministry_info = types.InlineKeyboardButton("😈Подготовить ответ на обращение(БЕТА)", callback_data=json.dumps({"type": "digital_ministry_info", "chat_id": message.chat.id}))
            # inline_keyboard.add(button_digital_ministry_info)
            #   button_digital_ministry_info = types.InlineKeyboardButton("😈Подготовить ответ на обращение(БЕТА)", 'digital_ministry_info')
            #  inline_keyboard.add(button_digital_ministry_info)

            if message.from_user.id in allowed_users:
                button_digital_ministry_info = types.InlineKeyboardButton(
                    "😈Подготовить ответ на обращение(БЕТА)", callback_data="digital_ministry_info")
                inline_keyboard.add(button_digital_ministry_info)

            builder = InlineKeyboardBuilder()
            survey_data_storage[message.chat.id] = survey_results_values

            if survey_results_values:

                callback_data = json.dumps(
                    {"type": "survey_results", "chat_id": message.chat.id})

                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"Показать результаты опроса ({len(survey_results_values)})", callback_data=callback_data)]
                ])
                builder.attach(InlineKeyboardBuilder.from_markup(markup))

            if szoreg_values:
                szoreg_response = '🏢<b>Учреждения, подключенные по госпрограмме</b>\n\n'
                for i, row in enumerate(szoreg_values, 1):
                    if len(row) > 6:

                        szoreg_response += f'\n{i}. <b>Тип:</b> {row[7]}\n<b>аименование:</b> {row[8]}\n<b>Адрес:</b> {row[5]} \n<b>Тип подключения:</b> {row[6]}\n<b>Пропускная способность:</b> {row[9]}\n<b>Контракт:</b> {row[10]}\n'
                    else:
                        print(
                            f'Строка {i} слишком короткая для обработки: {row}')

                szoreg_info_storage[message.chat.id] = szoreg_response
                callback_data = json.dumps(
                    {"type": "szoreg_info", "chat_id": message.chat.id})

                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"🏢Список учреждений ({len(szoreg_values)})", callback_data=callback_data)]
                ])
                builder.attach(InlineKeyboardBuilder.from_markup(markup))

            if schools_values:
                schools_response = '🏫<b>Школы:</b>\n'
                for i, row in enumerate(schools_values, 1):
                    schools_response += f'\n{i} '

                    if len(row) > 7 and row[12] is not None:
                        schools_response += f'<b>{html.escape(row[12])}</b>\n'
                    if len(row) > 12 and row[7] is not None:
                        schools_response += f'\n{html.escape(row[7])}\n'
                    if len(row) > 14 and row[14] is not None:
                        schools_response += f'\n{html.escape(row[14])}, '
                    if len(row) > 13 and row[13] is not None:
                        schools_response += f'{html.escape(row[13])} Мб/с\n'
                    if len(row) > 20 and row[20] is not None:
                        schools_response += f'{html.escape(row[20])}'
                    else:
                        schools_response += ''
                    schools_response += '\n'

                callback_data = json.dumps(
                    {"type": "schools_info", "chat_id": message.chat.id})
                schools_info_storage[message.chat.id] = schools_response
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"🏫Школы({len(schools_values)})", callback_data=callback_data)]
                ])
                builder.attach(InlineKeyboardBuilder.from_markup(markup))

            if schools_values or szoreg_values or survey_results_values:
                await message.answer("Дополнительная информация", reply_markup=builder.as_markup())

            else:
                await bot.send_message(message.chat.id, "Нет дополнительной информации для отображения.")

    if len(found_values) > 1:

        builder_1 = ReplyKeyboardBuilder()

        values = [(await get_value(row, 1), await get_value(row, 2)) for row in found_values]
        values_with_numbers = [
            f"{i + 1}. {value[0]}" for i, value in enumerate(values)]
        msg = '\n'.join(values_with_numbers)

        messages = split_message(
            f'Найдено несколько населенных пунктов с таким названием. \n\n{msg}')

        for msg in messages:
            await bot.send_message(message.chat.id, msg)

        for index in enumerate(found_values, start=1):

            button_text = f"{index[0]}"

            builder_1.button(text=button_text)
        builder_1.button(text="Отмена")
        builder_1.adjust(5)
        keyboard_1 = builder_1.as_markup(
            resize_keyboard=True, one_time_keyboard=True, input_field_placeholder="Выберите населенный пункт")

        saved_data = await state.update_data()
        await state.set_state(Form.waiting_for_number)

        await bot.send_message(message.chat.id, 'Выберите номер необходимого населенного пункта:', reply_markup=keyboard_1)


@main_router.message(StateFilter(Form.waiting_for_number))
async def handle_select_number(message: Message, state: FSMContext):
    from google_connections import init_redis
    redis = await init_redis()
    data = await state.get_data()
    from main import bot

    try:

        found_values = data.get('found_values')

        index_text = message.text


        user_first_name = message.from_user.first_name
        chat_id = message.chat.id
        response = ''
        pokazatel_504p_lines = []
        votes_response = ''
        yandex_2023_response = ''
        ucn2_response = ''

        # Проверки ввода пользователя
        if index_text == "Отмена":
            await bot.send_message(chat_id, 'Поиск отменен.', reply_markup=types.ReplyKeyboardRemove())
            await state.clear()
            return
        if not index_text.isdigit():
            await bot.send_message(chat_id, 'Введено некорректное значение. Пожалуйста, введите число.')
            return

        index = int(index_text)
        

        if index <= 0 or index > len(found_values):
            await bot.send_message(chat_id, f'Введено некорректное значение. Пожалуйста, введите число в диапазоне от 1 до {len(found_values)}.')
            return

        selected_np = found_values[index - 1]
        await state.clear()
        await state.update_data(found_values=selected_np)
        await state.update_data(np=selected_np[4])
        latitude = selected_np[7]
        longitude = selected_np[8]

        async with asyncio.TaskGroup() as tg:
            yandex_2023_task = tg.create_task(
                search_yandex_2023_values(selected_np[4], redis))
            pokazatel_504p_task = tg.create_task(
                search_in_pokazatel_504p(selected_np[4]))
            ucn2_task = tg.create_task(search_in_ucn2(selected_np[4], redis))
            survey_results_task = tg.create_task(
                search_survey_results(np=selected_np[4]))
            szoreg_task = tg.create_task(
                search_szoreg_values(selected_np[4], redis))
            schools_task = tg.create_task(
                search_schools_values(selected_np[4], redis))

            yandex_2023_values = await yandex_2023_task
            pokazatel_504p_values = await pokazatel_504p_task
            ucn2_values = await ucn2_task
            survey_results_values = await survey_results_task
            szoreg_values = await szoreg_task
            schools_values = await schools_task

        operators = {
            "    |Tele2": selected_np[39] if len(selected_np) > 39 else None,
            "    |Мегафон": selected_np[40] if len(selected_np) > 40 else None,
            "    |Билайн": selected_np[41] if len(selected_np) > 41 else None,
            "    |МТС": selected_np[42] if len(selected_np) > 42 else None,
        }

        # operators_response = '\nОценка жителей:\n'

        # Список для хранения ответов от операторов
        operator_responses = []

        for operator_name, operator_value in operators.items():

            # Проверка на наличие значения (не None и не пустая строка)
            if operator_value:
                # Переводим значение в строку, чтобы избежать ошибок при выполнении метода replace
                operator_value_str = str(operator_value)

                # Пытаемся найти качество сигнала
                signal_quality = re.search(
                    r'Отсутствует|Низкое|Среднее|Хорошее', operator_value_str, re.IGNORECASE)
                if signal_quality:
                    signal_quality = signal_quality.group()
                    if "Отсутствует" in signal_quality:
                        signal_level = "🔴Отсутствует"
                    elif "Низкое" in signal_quality:
                        signal_level = "🟠Низкое"
                    elif "Среднее" in signal_quality:
                        signal_level = "🟡Среднее"
                    elif "Хорошее" in signal_quality:
                        signal_level = "🟢Хорошее"
                    else:
                        signal_level = "❓Неизвестно"

                    # Заменяем найденное качество сигнала на его эмодзи-эквивалент
                    operator_value_str = operator_value_str.replace(
                        signal_quality, signal_level)
                else:
                    operator_value_str = operator_value_str

                # Заменяем "(" и ")" на " "
                operator_value_str = operator_value_str.replace(
                    "(", " ").replace(")", " ")
                operator_responses.append(
                    f'{operator_name}: {operator_value_str}\n')
            else:
                # Если нет данных по оператору, не добавляем его в ответ
                continue

        # Если нет данных ни по одному оператору, добавляем сообщение об отсутствии данных
     #   if not operator_responses:
        #    operators_response += 'Нет данных\n'
       # else:
        #    operators_response += ''.join(operator_responses)

        # response += operators_response

        if yandex_2023_values:
            yandex_2023_response = '\n\n<b>Информация из таблицы 2023</b>\n\n'
            for row in yandex_2023_values:
                yandex_2023_response += f'Тип подключения: {row[4]}\nОператор: {row[15]}\nСоглашение: {row[7]}\nПодписание соглашения с МЦР: {row[8]}\nПодписание соглашения с АГЗ: {row[9]}\nДата подписания контракта: {row[11]}\nДата установки АМС: {row[12]}\nДата монтажа БС: {row[13]}\nЗапуск услуг: {row[14]}\n\n'

        if pokazatel_504p_values is not None and not pokazatel_504p_values.empty:
            

            for i in range(10, 14):
                if i < len(pokazatel_504p_values.columns):
                    value = pokazatel_504p_values.iloc[0, i]
                    if pd.notna(value) and value.strip():
                        if "Хорошее" in value:
                            value = value.replace("Хорошее", "🟢Хорошее")
                        if "Низкое" in value:
                            value = value.replace("Низкое", "🟠Низкое")
                        pokazatel_504p_lines.append(value)

            # Выводим обработанные строки для проверки
            print(pokazatel_504p_lines)

        pokazatel_504p_response = "\n".join(
            pokazatel_504p_lines) if pokazatel_504p_lines else "🔴отсутствует"

        if "4G" in pokazatel_504p_response:
            votes_response = ""
        else:
            if len(selected_np) > 38:
                # Количество голосов находится в 35-ом столбце
                votes = selected_np[34] or "неизвестно"
                # Время обновления находится в 36-ом столбце
                update_time = selected_np[35] or "неизвестно"
                # Рейтинг находится в 37-ом столбце
                rank = selected_np[36] or "неизвестно"
                # Количество НП с таким же количеством голосов находится в 39-ом столбце
                same_votes_np = selected_np[38] or "неизвестно"
                if votes != "неизвестно" and update_time != "неизвестно" and rank != "неизвестно" and same_votes_np != "неизвестно":
                    votes_response = f'\n\n<b>Голосование УЦН 2.0 2024</b>\n\n📊Количество голосов: <b>{votes}</b> (такое же количество голосов имеют {same_votes_np} населённых пунктов)\n🏆Место в рейтинге: {rank}\nДата обновления информации: {update_time}'
                else:
                    print("Debug: Не все данные для блока голосования были найдены.")

        response += votes_response

        if ucn2_values:
            for row in ucn2_values:
                ucn2_response = ''

                if 4 < len(row) and row[4]:  # Проверка наличия значения
                    ucn2_response += '  Информация от Теле2:\n    -СМР: ' + \
                        row[4] + '\n'
                if 5 < len(row) and row[5]:  # Проверка наличия значения
                    ucn2_response += '    -Запуск: ' + row[5] + '\n'
                if 6 < len(row) and row[6]:  # Проверка наличия значения
                    ucn2_response += '    -Комментарии: ' + row[6] + '\n'

                if ucn2_response:  # Если ucn2_response не пуст, добавить вводную строку в начало
                    ucn2_response = '\n\n\n<b>УЦН 2.0 2023</b>\n' + ucn2_response
                    response += ucn2_response
        survey_data_storage[message.chat.id] = survey_results_values

        try:
            selsovet_info, tanya_sub_info_year, tanya_sub_info_provider, taksofony_info, arctic_info, internet_info, population_2010, population_2020, itog_ucn_2023, tv = await asyncio.gather(
                get_value(found_values[index - 1], 20),
                get_value(found_values[index - 1], 13),
                get_value(found_values[index - 1], 14),
                get_value(found_values[index - 1], 12),
                get_value(found_values[index - 1], 6),
                get_value(found_values[index - 1], 9),
                get_value(found_values[index - 1], 2),
                get_value(found_values[index - 1], 5),
                get_value(found_values[index - 1], 24),
                get_value(found_values[index - 1], 43),
                return_exceptions=True  # Возврат исключений как объектов
            )
        except Exception as e:
            print(f"Произошла ошибка: {e}")
        
        response = f'<b>{await get_value(found_values[index - 1], 1)}</b>'

        if selsovet_info:
            response += f'\n{selsovet_info}'
        if arctic_info:
            response += f'\n❄️️арктическая зона❄️️'

        response += f'\n\n👥население 2010 г:{population_2010} чел.\n👥население 2020 г: {population_2020} чел.'

        if taksofony_info:
            response += f'\n☎️таксофон: {taksofony_info}'

        response += f'\n🌐интернет: {internet_info}️'
        if tv:
            response += f'\n📺телевидение: {tv}\n'
        response += f'⠀'
        response += f'<pre>📱Сотовая связь:\n{pokazatel_504p_response}</pre>\n'

        if tanya_sub_info_year and tanya_sub_info_provider:
            response += f'\n\nнаселенный пункт был подключен в рамках государственной программый "Развитие информационного общества" в {tanya_sub_info_year} году, оператор {tanya_sub_info_provider}'

        if itog_ucn_2023:
            response += f'\n\nкомментарий Минцифры России об УЦН 2024: {itog_ucn_2023}'

        # response += f'\n{operators_response}\n'

        response += f'{ucn2_response}{yandex_2023_response}{votes_response}\n'

        info_text_storage[message.chat.id] = response

        await bot.send_message(message.chat.id, "<b>Выбранный населенный пункт</b>", parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove())

        await bot.send_location(message.chat.id, latitude, longitude)

        messages = split_message(response)

        # allowed_users = {964635576, 1063749463, 374056328, 572346758, 434872315, 1045874687, 1063749463, 487922464, 371098269, 402748716}
        allowed_users = {1}

        survey_builder = InlineKeyboardBuilder()
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"Пройти опрос", callback_data='start_survey')]
        ])
        survey_builder.attach(InlineKeyboardBuilder.from_markup(markup))
        
        response += f'\nУзнать о проектах министерства \n/development'
        await bot.send_message(message.chat.id, response, parse_mode='HTML', disable_web_page_preview=True, reply_markup=survey_builder.as_markup(), message_effect_id='5046509860389126442')

        builder_2 = InlineKeyboardBuilder()

        if survey_results_values:
            survey_data_storage[message.chat.id] = survey_results_values
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Показать результаты опроса ({len(survey_results_values)})", callback_data=json.dumps(
                    {"type": "survey_results", "chat_id": message.chat.id}))]
            ])
            builder_2.attach(InlineKeyboardBuilder.from_markup(markup))

        '''
        if message.from_user.id in allowed_users:
            button_digital_ministry_info = types.InlineKeyboardButton("😈Подготовить ответ на обращение(БЕТА)", callback_data=json.dumps({"type": "digital_ministry_info", "chat_id": message.chat.id}))
            inline_keyboard.add(button_digital_ministry_info)
        '''
        if szoreg_values:

            szoreg_response = '🏢<b>Учреждения, подключенные по госпрограмме</b>\n\n'
            for i, row in enumerate(szoreg_values, 1):
                if len(row) > 6:

                    szoreg_response += f'\n{i}. <b>Тип:</b> {row[7]}\n<b>Наименование:</b> {row[8]}\n<b>Адрес:</b> {row[5]} \n<b>Тип подключения:</b> {row[6]}\n<b>Пропускная способность:</b> {row[9]}\n<b>Контракт:</b> {row[10]}\n'
                else:
                    print(f'Строка {i} слишком короткая для обработки: {row}')

            szoreg_info_storage[message.chat.id] = szoreg_response
            callback_data = json.dumps(
                {"type": "szoreg_info", "chat_id": message.chat.id})

            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"🏢Список учреждений ({len(szoreg_values)})", callback_data=callback_data)]
            ])
            builder_2.attach(InlineKeyboardBuilder.from_markup(markup))

        if schools_values:
            schools_response = '🏫<b>Школы:</b>\n'
            for i, row in enumerate(schools_values, 1):
                schools_response += f'\n{i} '
                # Проверяем каждую ячейку перед добавлением в ответ
                if len(row) > 7 and row[12] is not None:
                    schools_response += f'<b>{html.escape(row[12])}</b>\n'
                if len(row) > 12 and row[7] is not None:
                    schools_response += f'\n{html.escape(row[7])}\n'
                if len(row) > 14 and row[14] is not None:
                    schools_response += f'\n{html.escape(row[14])}, '
                if len(row) > 13 and row[13] is not None:
                    schools_response += f'{html.escape(row[13])} Мб/с\n'
                if len(row) > 20 and row[20] is not None:
                    schools_response += f'{html.escape(row[20])}'
                else:
                    schools_response += ''
                schools_response += '\n'

            schools_info_storage[message.chat.id] = schools_response
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"🏫Школы ({len(schools_values)})", callback_data=json.dumps(
                    {"type": "schools_info", "chat_id": message.chat.id}))]
            ])
            builder_2.attach(InlineKeyboardBuilder.from_markup(markup))

        if schools_values or szoreg_values or survey_results_values:
            await message.answer("Дополнительная информация", reply_markup=builder_2.as_markup())

        else:
            await bot.send_message(message.chat.id, "Нет дополнительной информации для отображения.")

    except ValueError:

        await bot.send_message(message.chat.id, 'Введено некорректное значение. Пожалуйста, введите число в диапазоне от 1 до {}.'.format(len(found_values)))


# Функции для работы команды /otpusk


@main_router.callback_query(F.data.contains("school"))
async def handle_schools_info(query):
    data = json.loads(query.data)

    from main import bot
    chat_id = json.loads(query.data)["chat_id"]
    if chat_id in schools_info_storage:
        response = schools_info_storage[chat_id]
        messages = split_message(response)
        for message_group in messages:
            msg = ''.join(message_group)
            if msg.strip():  # Проверка, что сообщение не пустое
                await bot.send_message(chat_id, msg, parse_mode='HTML')

        await bot.answer_callback_query(query.id)
    else:
        await bot.answer_callback_query(query.id, "Информация из таблицы по школам недоступна.")


@main_router.callback_query(F.data == "start_survey")
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext):
    from main import bot

    data = await state.get_data()

    np = data['np']

    await state.set_state(Survey.tele2_level)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="4G", callback_data="tele2_4g"),
         InlineKeyboardButton(text="3G", callback_data="tele2_3g"),
         InlineKeyboardButton(text="2G", callback_data="tele2_2g")],
        [InlineKeyboardButton(text="Услуги отсутствуют", callback_data="tele2_none"),
         InlineKeyboardButton(text="Не знаю", callback_data="tele2_unknown")]
    ])

    # Отправляем сообщение с предложением оценить уровень сигнала
    await bot.send_animation(chat_id=query.message.chat.id,
                             animation=tele2_id,
                             caption="Пожалуйста, оцените уровень сигнала Tele2:",
                             reply_markup=markup)


@main_router.callback_query(F.data.contains("survey_res"))
async def handle_show_survey_results(query: types.CallbackQuery, state: FSMContext):

    data = await state.get_data()
    np = data['np']
    survey_res = await search_survey_results(np)
    builder = InlineKeyboardBuilder()
    survey_results_dict = {}
    for item in survey_res:
        # Создаем информативный текст для кнопки
        user_id = item['user_id']
        # user_info = f"ID {item['user_id']}: Tele2 {item['tele2_level']} {item['tele2_quality']}, MTS {item['mts_level']}"
        builder.button(text=f"🏢 {item['first_name']}",
                       callback_data=f"detailed_survey_data:{item['user_id']}")
        builder.adjust(2)
        survey_results_dict[user_id] = item

    await state.update_data(survey_results_dict=survey_results_dict)

    # Получаем клавиатуру для использования в ответе
    keyboard = builder.as_markup()

    # Отправляем сообщение с инлайн-клавиатурой
    await query.message.answer(text="Выберите пользователя для детальной информации:", reply_markup=keyboard)


@main_router.callback_query(F.data.contains("detailed_survey_data"))
async def show_user_data(query: types.CallbackQuery, state: FSMContext):
    user_id = query.data.split(":")[1]
    data = await state.get_data()

    survey_results_dict = data.get('survey_results_dict', {})
    survey_results = survey_results_dict.get(user_id)

    if survey_results:
        response_text = (
            f"<b>{survey_results['first_name']} {survey_results['last_name']}</b>\n\n"
            f"Никнейм: @{survey_results['username']}\n"
            f"Телефон: {survey_results['contact']}\n"

            f"Tele2: {survey_results['tele2_level']} {survey_results['tele2_quality']}\n"
            f"МТС: {survey_results['mts_level']} {survey_results['mts_quality']}\n"
            f"Мегафон: {survey_results['megafon_level']} {survey_results['megafon_quality']}\n"
            f"Билайн: {survey_results['beeline_level']} {survey_results['beeline_quality']}\n\n"
            f"{survey_results['time']}"

        )
    else:
        response_text = "Информация по данному пользователю не найдена."

    await query.message.answer_photo(protect_content=True, photo=default_profile, caption=response_text, parse_mode='HTML')


@main_router.callback_query(F.data.startswith("tele2"), StateFilter(Survey.tele2_level))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext):
    await state.update_data(tele2_level=query.data.split("_")[1])
    data = await state.get_data()

    selected_option = query.data.split("_")[1]
    user_id = query.from_user.id
    first_name = query.from_user.first_name
    last_name = query.from_user.last_name
    username = query.from_user.username
    survey_time = datetime.now().astimezone(
        ZoneInfo("Asia/Krasnoyarsk")).strftime("%Y-%m-%d %H:%M:%S")
    survey_data = {
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "time": survey_time,
        "tele2_level": data.get("tele2_level"),

    }

    np = data['np']
    await save_survey_results(np, user_id, survey_data)
    if selected_option == "none":
        np = data['np']

        await state.set_state(Survey.mts_level)
        await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="4G", callback_data="mts_4g"),
             InlineKeyboardButton(text="3G", callback_data="mts_3g"),
             InlineKeyboardButton(text="2G", callback_data="mts_2g")],
            [InlineKeyboardButton(text="Услуги отсутствуют", callback_data="mts_none"),
             InlineKeyboardButton(text="Не знаю", callback_data="mts_unknown")]
        ])

        try:

            await bot.send_animation(chat_id=query.message.chat.id,
                                     animation=mts_id,
                                     caption="Пожалуйста, оцените уровень сигнала МТС:",
                                     reply_markup=markup)
        except Exception as e:
            print(f"Failed to edit message caption: {str(e)}")

            return
    else:

        await state.set_state(Survey.tele2_quality)

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Низкое", callback_data="tele2_quality_low"),
             InlineKeyboardButton(
                 text="Среднее", callback_data="tele2_quality_mid"),
             InlineKeyboardButton(text="Хорошее", callback_data="tele2_quality_good")],
            [InlineKeyboardButton(
                text="Затрудняюсь ответить", callback_data="tele2_quality_unknown")]
        ])

        try:

            await bot.edit_message_caption(chat_id=query.message.chat.id,
                                           message_id=query.message.message_id,
                                           caption="Оцените качество услуг Теле2",
                                           reply_markup=markup)
        except Exception as e:
            print(f"Failed to edit message caption: {str(e)}")


@main_router.callback_query(F.data.startswith("tele2_quality"), StateFilter(Survey.tele2_quality))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext):

    await state.update_data(tele2_quality=query.data.split("_")[2])
    data = await state.get_data()

    user_id = query.from_user.id
    survey_data = {
        "tele2_quality": data.get("tele2_quality"),

    }
    print(f'survey_data в tele2_quality {survey_data}')

    np = data['np']
    await save_survey_results(np, user_id, survey_data)
    await state.set_state(Survey.mts_level)
    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="4G", callback_data="mts_4g"),
         InlineKeyboardButton(text="3G", callback_data="mts_3g"),
         InlineKeyboardButton(text="2G", callback_data="mts_2g")],
        [InlineKeyboardButton(text="Услуги отсутствуют", callback_data="mts_none"),
         InlineKeyboardButton(text="Не знаю", callback_data="mts_unknown")]
    ])

    try:

        await bot.send_animation(chat_id=query.message.chat.id,
                                 animation=mts_id,
                                 caption="Пожалуйста, оцените уровень сигнала МТС:",
                                 reply_markup=markup)
    except Exception as e:
        print(f"Failed to edit message caption: {str(e)}")


@main_router.callback_query(F.data.startswith("mts"), StateFilter(Survey.mts_level))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext):
    await state.update_data(mts_level=query.data.split("_")[1])
    data = await state.get_data()
    selected_option = query.data.split("_")[1]

    np = data['np']
    user_id = query.from_user.id
    survey_data = {
        "mts_level": data.get("mts_level"),

    }
    await save_survey_results(np, user_id, survey_data)
    if selected_option == 'none':

        await state.set_state(Survey.megafon_level)
        await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="4G", callback_data="megafon_4g"),
             InlineKeyboardButton(text="3G", callback_data="megafon_3g"),
             InlineKeyboardButton(text="2G", callback_data="megafon_2g")],
            [InlineKeyboardButton(text="Услуги отсутствуют", callback_data="megafon_none"),
             InlineKeyboardButton(text="Не знаю", callback_data="megafon_unknown")]
        ])

        try:

            await bot.send_animation(chat_id=query.message.chat.id,
                                     animation=megafon_id,
                                     caption="Пожалуйста, оцените уровень сигнала Мегафон:",
                                     reply_markup=markup)
        except Exception as e:
            print(f"Failed to edit message caption: {str(e)}")

    else:

        await state.set_state(Survey.mts_quality)

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Низкое", callback_data="mts_quality_low"),
             InlineKeyboardButton(
                 text="Среднее", callback_data="mts_quality_mid"),
             InlineKeyboardButton(text="Хорошее", callback_data="mts_quality_good")],
            [InlineKeyboardButton(
                text="Затрудняюсь ответить", callback_data="mts_quality_unknown")]
        ])

        try:

            await bot.edit_message_caption(chat_id=query.message.chat.id,
                                           message_id=query.message.message_id,
                                           caption="Оцените качество сигнала МТС",
                                           reply_markup=markup)
        except Exception as e:
            print(f"Failed to edit message caption: {str(e)}")


@main_router.callback_query(F.data.startswith("mts_quality"), StateFilter(Survey.mts_quality))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext):
    await state.update_data(mts_quality=query.data.split("_")[2])
    data = await state.get_data()
    np = data['np']
    user_id = query.from_user.id
    survey_data = {
        "mts_quality": data.get("mts_quality"),

    }
    await save_survey_results(np, user_id, survey_data)

    await state.set_state(Survey.megafon_level)
    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="4G", callback_data="megafon_4g"),
            InlineKeyboardButton(text="3G", callback_data="megafon_3g"),
            InlineKeyboardButton(text="2G", callback_data="megafon_2g")],
        [InlineKeyboardButton(text="Услуги отсутствуют", callback_data="megafon_none"),
            InlineKeyboardButton(text="Не знаю", callback_data="megafon_unknown")]
    ])

    try:

        await bot.send_animation(chat_id=query.message.chat.id,
                                 animation=megafon_id,
                                 caption="Пожалуйста, оцените уровень сигнала Мегафон:",
                                 reply_markup=markup)
    except Exception as e:
        print(f"Failed to edit message caption: {str(e)}")


@main_router.callback_query(F.data.startswith("megafon"), StateFilter(Survey.megafon_level))
async def megafon_level_survey(query: types.CallbackQuery, state: FSMContext):
    await state.update_data(megafon_level=query.data.split("_")[1])
    data = await state.get_data()

    user_id = query.from_user.id
    survey_data = {
        "megafon_level": data.get("megafon_level"),

    }

    np = data['np']
    selected_option = query.data.split("_")[1]

    await save_survey_results(np, user_id, survey_data)
    if selected_option == 'none':
        np = data['np']

        await state.set_state(Survey.beeline_level)

        await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="4G", callback_data="beeline_4g"),
             InlineKeyboardButton(text="3G", callback_data="beeline_3g"),
             InlineKeyboardButton(text="2G", callback_data="beeline_2g")],
            [InlineKeyboardButton(text="Услуги отсутствуют", callback_data="beeline_none"),
             InlineKeyboardButton(text="Не знаю", callback_data="beeline_unknown")]
        ])

        try:

            await bot.send_animation(chat_id=query.message.chat.id,
                                     animation=beeline_id,
                                     caption="Пожалуйста, оцените уровень сигнала Билайн:",
                                     reply_markup=markup)
        except Exception as e:
            print(f"Failed to edit message caption: {str(e)}")

    else:
        await state.set_state(Survey.megafon_quality)

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Низкое", callback_data="megafon_quality_low"),
             InlineKeyboardButton(
                text="Среднее", callback_data="megafon_quality_mid"),
             InlineKeyboardButton(text="Хорошее", callback_data="megafon_quality_good")],
            [InlineKeyboardButton(text="Затрудняюсь ответить",
                                  callback_data="megafon_quality_unknown")]
        ])

        try:

            await bot.edit_message_caption(chat_id=query.message.chat.id,
                                           message_id=query.message.message_id,
                                           caption="Оцените качество услуг Мегафон",
                                           reply_markup=markup)
        except Exception as e:
            print(f"Failed to edit message caption: {str(e)}")


@main_router.callback_query(F.data.startswith("megafon_quality"), StateFilter(Survey.megafon_quality))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext):
    await state.update_data(megafon_quality=query.data.split("_")[2])
    data = await state.get_data()

    user_id = query.from_user.id
    survey_data = {
        "megafon_quality": data.get("megafon_quality"),

    }

    np = data['np']
    await save_survey_results(np, user_id, survey_data)
    await state.set_state(Survey.beeline_level)

    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="4G", callback_data="beeline_4g"),
         InlineKeyboardButton(text="3G", callback_data="beeline_3g"),
         InlineKeyboardButton(text="2G", callback_data="beeline_2g")],
        [InlineKeyboardButton(text="Услуги отсутствуют", callback_data="beeline_none"),
         InlineKeyboardButton(text="Не знаю", callback_data="beeline_unknown")]
    ])

    try:

        await bot.send_animation(chat_id=query.message.chat.id,
                                 animation=beeline_id,
                                 caption="Пожалуйста, оцените уровень сигнала Билайн:",
                                 reply_markup=markup)
    except Exception as e:
        print(f"send_animation: {str(e)}")


@main_router.callback_query(F.data.startswith("beeline"), StateFilter(Survey.beeline_level))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext):
    await state.update_data(beeline_level=query.data.split("_")[1])
    data = await state.get_data()
    selected_option = query.data.split("_")[1]
    user_id = query.from_user.id
    survey_data = {
        "beeline_level": data.get("beeline_level"),

    }

    np = data['np']
    await save_survey_results(np, user_id, survey_data)
    if selected_option == 'none':

        await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
        builder_loc = ReplyKeyboardBuilder()

        builder_loc.row(types.KeyboardButton(text='поделиться локацией', request_location=True),
                        types.KeyboardButton(text='поделиться контактом', request_contact=True))

        keyboard_loc = builder_loc.as_markup(
            resize_keyboard=True, one_time_keyboard=True)

        await query.message.answer("При желании можете поделиться своим местоположением и номером телефона с нами 😊 \n (работает только со смартфона)", reply_markup=keyboard_loc)

    else:

        await state.set_state(Survey.beeline_quality)

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Низкое", callback_data="beeline_quality_low"),
             InlineKeyboardButton(
                 text="Среднее", callback_data="beeline_quality_mid"),
             InlineKeyboardButton(text="Хорошее", callback_data="beeline_quality_good")],
            [InlineKeyboardButton(
                text="Затрудняюсь ответить", callback_data="beeline_quality_unknown")]
        ])

        try:
            # Attempt to edit the caption of the message
            await bot.edit_message_caption(chat_id=query.message.chat.id,
                                           message_id=query.message.message_id,
                                           caption="Оцените качество услуг Билайн",
                                           reply_markup=markup)
        except Exception as e:
            print(f"Failed to edit message caption: {str(e)}")


@main_router.callback_query(F.data.startswith("beeline_quality"), StateFilter(Survey.beeline_quality))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext):
    await state.update_data(beeline_quality=query.data.split("_")[2])
    data = await state.get_data()

    user_id = query.from_user.id
    survey_data = {
        "beeline_quality": data.get("beeline_quality"),

    }

    np = data['np']
    await save_survey_results(np, user_id, survey_data)

    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)

    builder_loc = ReplyKeyboardBuilder()

    builder_loc.row(types.KeyboardButton(text='поделиться локацией', request_location=True),
                    types.KeyboardButton(text='поделиться контактом', request_contact=True))

    keyboard_loc = builder_loc.as_markup(
        resize_keyboard=True, one_time_keyboard=True)

    await query.message.answer("При желании можете поделиться своим местоположением и номером телефона с нами 😊 \n (работает только со смартфона)", reply_markup=keyboard_loc)

  #  await bot.answer_callback_query(query.id, f'номер выбранного населенного пункта: {np}')


@main_router.callback_query(F.data.contains("szore"))
async def handle_szoreg_info(query: types.CallbackQuery):
    data = json.loads(query.data)
    print(f"Received szo callback data: {data}")
    try:

        print("Данные из callback_data:", data)
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON: {e}")
        await query.bot.answer_callback_query(query.id, "Некорректные данные.")
        return

    chat_id = data["chat_id"]
    if chat_id not in szoreg_info_storage:
        print("Информация для данного chat_id не найдена в хранилище.")
        await query.bot.answer_callback_query(query.id, "Информация недоступна.")
        return

    response = szoreg_info_storage[chat_id]
    messages = split_message(response)

    try:
        for message_group in messages:
            msg = ''.join(message_group)
            if msg.strip():
                await query.bot.send_message(chat_id, msg, parse_mode='HTML')
        await query.bot.answer_callback_query(query.id, "Данные отправлены.")

        print("Сообщения успешно отправлены.")

    except Exception as e:
        await query.bot.answer_callback_query(query.id, "Произошла ошибка при обработке запроса.")
        print(
            f"Exception: {e} Callback query didn't answer for chat ID {chat_id}")

