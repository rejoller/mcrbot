

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReactionTypeEmoji, InputFile, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types, Router, F


from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import Message
from datetime import datetime, timedelta
import csv
from mongo_connect import save_survey_results
from google_connections import get_authorized_client_and_spreadsheet, search_yandex_2023_values, search_in_pokazatel_504p, search_in_ucn2, search_schools_values, search_survey_results, load_otpusk_data, search_values, search_values_levenshtein, search_szoreg_values, get_value, init_redis
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



# Функции для логирования действий пользователей
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

# Функция для сохранения данных пользователя из сообщения


async def log_user_data_from_message(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username
    message_text = message.text

    log_user_data(user_id, first_name, last_name, username, message_text)

# Состояние ожидания введения номера пользователем (используется когда населенных пунктов с одинаковым названием несколько)


class Form(StatesGroup):
    default = State()
    waiting_for_number = State()


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

    for row_idx, row in enumerate(otpusk_data):
        if row_idx == 0:  # пропустить заголовки таблицы
            continue
        if len(row) >= 5:
            try:
                start_date = datetime.strptime(row[3], "%d.%m.%Y").date()
                end_date = datetime.strptime(row[4], "%d.%m.%Y").date()

                if start_date <= today <= end_date:
                    employees_on_vacation.append(row)

                if today < start_date <= future_vacation_start:
                    employees_starting_vacation_soon.append(row)

            except ValueError:
                pass  # игнорировать строки с неправильным форматом даты

    return employees_on_vacation, employees_starting_vacation_soon


@main_router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    await state.clear()

    user_first_name = message.from_user.first_name
    await message.answer(
        f'Я бот министерства цифрового развития Красноярского края!'
        '\n Введи наименование любого населенного пункта края, '

        'чтобы получить информацию о связи в нем. По вопросам обращаться к @rejoller.')




@main_router.message(F.location)
async def handle_location(message: types.Message, state: FSMContext):
    # Обработка локации
    from mongo_connect import save_user_location
    user_id = message.from_user.id
    location_data = {"latitude": message.location.latitude, "longitude": message.location.longitude}
    await message.answer('спасибо😉')
    await save_user_location(user_id, location_data)



@main_router.message(F.animation)
async def echo_gif(message: Message):
    file_id = message.animation.file_id
    print(file_id)
    await message.reply_animation(message.animation.file_id)


@main_router.message(~StateFilter(Form.waiting_for_number))
async def handle_text(message: Message, state: FSMContext):
   
    reaction_emoji = ReactionTypeEmoji(emoji='🫡')
    await message.react(reaction=[reaction_emoji], is_big=True)
    redis = await init_redis()

  #  user_state = await state.get_state()



    global info_text_storage
    await state.set_state(Form.default)
   # user_first_name = message.from_user.first_name
    await log_user_data_from_message(message)
  #  chat_id = message.chat.id

    #user_id = message.from_user.id  # Получаем user_id

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

            if len(found_values) > 0 and len(found_values[0]) > 4:
                # Подразумевается, что если условие выполнено, то можно безопасно обращаться к found_values[5][4]

                ucn2_values, yandex_2023_values, pokazatel_504p_values, survey_results_values = await asyncio.gather(
                    search_in_ucn2(found_values[0][4], redis),
                    search_yandex_2023_values(found_values[0][4], redis),
                    search_in_pokazatel_504p(found_values[0][4], redis),
                    search_survey_results(found_values[0][4], redis)
                )
            else:
                # Если условие не выполнено, значит индекса [5][4] нет, и нужно обойтись без search_in_results
                ucn2_values, yandex_2023_values, pokazatel_504p_values = await asyncio.gather(
                    search_in_ucn2(found_values[0][4], redis),
                    search_yandex_2023_values(found_values[0][4], redis),
                    search_in_pokazatel_504p(found_values[0][4], redis)
                )
                survey_results_values = None

            if found_values_a:
                for row in found_values_a:
                    # Создаем словарь с операторами и их значениями, используя метод get для безопасного обращения к элементам списка
                    operators = {
                        "Tele2": row[39] if len(row) > 39 else None,
                        "Мегафон": row[40] if len(row) > 40 else None,
                        "Билайн": row[41] if len(row) > 41 else None,
                        "МТС": row[42] if len(row) > 42 else None,
                    }

                    operators_response = '\nОценка жителей:\n'

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

                    response += operators_response

            if yandex_2023_values:
                yandex_2023_response = '\n\n\n<b>Информация из таблицы 2023</b>\n\n'
                for row in yandex_2023_values:
                    yandex_2023_response += f'Тип подключения: {row[4]}\nОператор: {row[15]}\nСоглашение: {row[7]}\nПодписание соглашения с МЦР: {row[8]}\nПодписание соглашения с АГЗ: {row[9]}\nДата подписания контракта: {row[11]}\nДата установки АМС: {row[12]}\nДата монтажа БС: {row[13]}\nЗапуск услуг: {row[14]}\n\n'
            if pokazatel_504p_values:
                for index in range(6, 10):
                    if len(pokazatel_504p_values[0]) > index and pokazatel_504p_values[0][index] and pokazatel_504p_values[0][index].strip():
                        value = pokazatel_504p_values[0][index]
                        if "Хорошее" in value:
                            value = value.replace("Хорошее", "🟢Хорошее")
                        if "Низкое" in value:
                            value = value.replace("Низкое", "🟠Низкое")
                        pokazatel_504p_lines.append(value)
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
                selsovet_info, tanya_sub_info_year, tanya_sub_info_provider, taksofony_info, arctic_info, internet_info, population_2010, population_2020, itog_ucn_2023 = await asyncio.gather(
                    get_value(found_values[0], 20),
                    get_value(found_values[0], 13),
                    get_value(found_values[0], 14),
                    get_value(found_values[0], 12),
                    get_value(found_values[0], 6),
                    get_value(found_values[0], 9),
                    get_value(found_values[0], 2),
                    get_value(found_values[0], 5),
                    get_value(found_values[0], 24),
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
            response += f'\n\n📱<b>Сотовая связь:</b>\n{pokazatel_504p_response}'

            if tanya_sub_info_year and tanya_sub_info_provider:
                response += f'\n\nнаселенный пункт был подключен в рамках государственной программый "Развитие информационного общества" в {tanya_sub_info_year} году, оператор {tanya_sub_info_provider}'

            if itog_ucn_2023:
                response += f'\n\nкомментарий Минцифры России об УЦН 2024: {itog_ucn_2023}'
            response += f'\n{operators_response}\n'
            response += f'{yandex_2023_response}{ucn2_response}{votes_response}\nЕсли хочешь узнать о голосовании УЦН 2.0 2024 жми /votes\n\nБот для проведения опросов жителей - <a href="http://t.me/providers_rating_bot">@providers_rating_bot</a>'

            info_text_storage[message.chat.id] = response

            await bot.send_location(message.chat.id, latitude, longitude, heading=10, proximity_alert_radius = 200)

            messages = split_message(response)
            survey_builder = InlineKeyboardBuilder()
            markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"Пройти опрос", callback_data='start_survey')]
                ])
            survey_builder.attach(InlineKeyboardBuilder.from_markup(markup))

            
            await bot.send_message(message.chat.id, response, parse_mode='HTML', disable_web_page_preview=True, reply_markup=survey_builder.as_markup())


                
                

            szoreg_values, schools_values = await asyncio.gather(

                search_szoreg_values(found_values[0][4], redis),
                search_schools_values(found_values[0][4], redis)
            )

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

                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Показать результаты опроса", callback_data=json.dumps(
                        {"type": "survey_chart", "chat_id": message.chat.id}))]
                ])
                builder.attach(InlineKeyboardBuilder.from_markup(markup))
                await message.answer("Найдены результаты опроса. Хотите посмотреть?", reply_markup=builder.as_markup())

        #  if szofed_values or espd_values or szoreg_values or schools_values or info_text_storage:

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

            if markup:
                await message.answer("доп инфо", reply_markup=builder.as_markup())

                # await bot.send_message(message.chat.id, "⬇️Дополнительная информация⬇️", reply_markup=inline_keyboard)
            else:
                await bot.send_message(message.chat.id, "Нет дополнительной информации для отображения.")

                # await bot.send_message(message.chat.id, "⬇️Дополнительная информация⬇️", reply_markup=inline_keyboard)
        # response_storage[message.chat.id] = response

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
            resize_keyboard=True, one_time_keyboard=True)

        saved_data = await state.update_data()
        await state.set_state(Form.waiting_for_number)

        await bot.send_message(message.chat.id, 'Выберите номер необходимого населенного пункта:', reply_markup=keyboard_1)

        logging.info(f"Получен текст сообщения: {message.text}")


@main_router.message(StateFilter(Form.waiting_for_number))
async def handle_select_number(message: Message, state: FSMContext):
    from google_connections import init_redis
    redis = await init_redis()
    data = await state.get_data()
    from main import bot

    try:
        await state.clear()
        found_values = data.get('found_values')

        index_text = message.text
        print(f'введенное значение: {index_text}')
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
        print(f'выбранный населенный пункт {index}')
        if index <= 0 or index > len(found_values):
            await bot.send_message(chat_id, f'Введено некорректное значение. Пожалуйста, введите число в диапазоне от 1 до {len(found_values)}.')
            return

        selected_np = found_values[index - 1]
        await state.update_data(found_values=selected_np)
        await state.update_data(np=selected_np[4])
        latitude = selected_np[7]
        longitude = selected_np[8]

        yandex_2023_values, pokazatel_504p_values, survey_results_values, ucn2_values = await asyncio.gather(
            search_yandex_2023_values(selected_np[4], redis),
            search_in_pokazatel_504p(selected_np[4], redis),
            search_survey_results(selected_np[4], redis),

            search_in_ucn2(selected_np[4], redis)
        )
        print('pokazatel_504p_values:', pokazatel_504p_values,)

        # Создаем словарь с операторами и их значениями
        operators = {
            "    |Tele2": selected_np[39] if len(selected_np) > 39 else None,
            "    |Мегафон": selected_np[40] if len(selected_np) > 40 else None,
            "    |Билайн": selected_np[41] if len(selected_np) > 41 else None,
            "    |МТС": selected_np[42] if len(selected_np) > 42 else None,
        }

        operators_response = '\nОценка жителей:\n'

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
        if not operator_responses:
            operators_response += 'Нет данных\n'
        else:
            operators_response += ''.join(operator_responses)

        response += operators_response

        if yandex_2023_values:
            yandex_2023_response = '\n\n<b>Информация из таблицы 2023</b>\n\n'
            for row in yandex_2023_values:
                yandex_2023_response += f'Тип подключения: {row[4]}\nОператор: {row[15]}\nСоглашение: {row[7]}\nПодписание соглашения с МЦР: {row[8]}\nПодписание соглашения с АГЗ: {row[9]}\nДата подписания контракта: {row[11]}\nДата установки АМС: {row[12]}\nДата монтажа БС: {row[13]}\nЗапуск услуг: {row[14]}\n\n'

        if len(pokazatel_504p_values) > 0:
            for i in range(6, 10):
                if len(pokazatel_504p_values[0]) > i and pokazatel_504p_values[0][i] and pokazatel_504p_values[0][i].strip():
                    value = pokazatel_504p_values[0][i]
                    value = value.replace("Хорошее", "🟢Хорошее").replace(
                        "Низкое", "🟠Низкое")
                    pokazatel_504p_lines.append(f"{value}")

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
            selsovet_info, tanya_sub_info_year, tanya_sub_info_provider, taksofony_info, arctic_info, internet_info, population_2010, population_2020, itog_ucn_2023 = await asyncio.gather(
                get_value(found_values[index - 1], 20),
                get_value(found_values[index - 1], 13),
                get_value(found_values[index - 1], 14),
                get_value(found_values[index - 1], 12),
                get_value(found_values[index - 1], 6),
                get_value(found_values[index - 1], 9),
                get_value(found_values[index - 1], 2),
                get_value(found_values[index - 1], 5),
                get_value(found_values[index - 1], 24),
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
        response += f'\n\n📱<b>Сотовая связь:</b>\n{pokazatel_504p_response}'

        if tanya_sub_info_year and tanya_sub_info_provider:
            response += f'\n\nнаселенный пункт был подключен в рамках государственной программый "Развитие информационного общества" в {tanya_sub_info_year} году, оператор {tanya_sub_info_provider}'

        if itog_ucn_2023:
            response += f'\n\nкомментарий Минцифры России об УЦН 2024: {itog_ucn_2023}'

        response += f'\n{operators_response}\n'

        response += f'{ucn2_response}{yandex_2023_response}{votes_response}\nЕсли хочешь узнать о голосовании УЦН 2.0 2024 жми /votes\nБот для проведения опросов жителей - <a href="http://t.me/providers_rating_bot">@providers_rating_bot</a>'

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

       
        await bot.send_message(message.chat.id, response, parse_mode='HTML', disable_web_page_preview=True, reply_markup=survey_builder.as_markup())
        
        szoreg_values, schools_values = await asyncio.gather(
            search_szoreg_values(selected_np[4], redis),
            search_schools_values(selected_np[4], redis)
        )
        print(f'szoreg_values: {szoreg_values}')
        print(f'schools_values: {schools_values}')
        builder_2 = InlineKeyboardBuilder()

        

        markup = None
        if survey_results_values:
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Показать результаты опроса", callback_data=json.dumps(
                    {"type": "survey_chart", "chat_id": message.chat.id}))]
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

        print(
            f"Creating szo button with data: {json.dumps({'type': 'szoreg_info', 'chat_id': message.chat.id})}")
        print(
            f"Creating school button with data: {json.dumps({'type': 'school_info', 'chat_id': message.chat.id})}")

        if markup != None:
            await message.answer("доп инфо", reply_markup=builder_2.as_markup())

        else:
            await bot.send_message(message.chat.id, "Нет дополнительной информации для отображения.")

    except ValueError:

        await bot.send_message(message.chat.id, 'Введено некорректное значение. Пожалуйста, введите число в диапазоне от 1 до {}.'.format(len(found_values)))


@main_router.message(F.text == "привет")
async def hello(message: types.Message):
    await message.answer("Я с тобой не разговариваю!")


# Стартовое сообщение (когда пользователь нажал /start)


# отправка файла с итогами голосования по УЦН 2024 (когда пользователь нажал /votes)
@main_router.message(Command("votes"))
async def send_votes(message: types.Message):
    from main import bot
    from google_connections import get_votes_data
    try:
        gc, spreadsheet = await get_authorized_client_and_spreadsheet()
        data = await get_votes_data(spreadsheet)
        excel_data = create_excel_file_2(data)  # убрали headers здесь
        await log_user_data_from_message(message)
        # Сохраняем данные Excel во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp:
            temp.write(excel_data.read())
            temp_filename = temp.name

        # Переименовываем файл перед отправкой
        final_filename = "Голосование УЦН 2_0 2024.xlsx"
        shutil.move(temp_filename, final_filename)

        # Отправляем файл
        with open(final_filename, "rb") as temp:
            await bot.send_document(message.chat.id, temp, caption='Информация о голосовании УЦН 2.0 2024')

        # Удаляем файл после отправки
        os.remove(final_filename)

    except Exception as e:
        tb = traceback.format_exc()  # Получить трассировку стека
        # Печатает трассировку стека
        print("An error occurred while handling /votes:", tb)
        # Включает ошибку и трассировку стека в ответ пользователю
        await message.reply(f'Произошла ошибка при обработке вашего запроса: {e}\n{tb}')


# Функции для работы команды /otpusk


@main_router.message(Command('otpusk'))
async def handle_otpusk_command(message: types.Message, days_ahead=30):
    
    await bot.send_message(message.chat.id, '🏝Загружаю️')
    await log_user_data_from_message(message)
    otpusk_data = await load_otpusk_data()

    employees_on_vacation, employees_starting_vacation_soon = get_employees_on_vacation(
        otpusk_data, days_ahead)

    response = ""

    if employees_on_vacation:
        response += '*Сегодня в отпуске*😎\n\n'
        for row in employees_on_vacation:
            response += f"{row[0]}, {row[1]}\n"
            response += f"  - Дата начала отпуска: {row[3]}\n"
            response += f"  - Дата окончания отпуска: {row[4]}\n\n"

    if employees_starting_vacation_soon:
        response += f"\n*Сотрудники, уходящие в отпуск в ближайшие {days_ahead} дней*\n\n"
        for emp_row in employees_starting_vacation_soon:
            response += f"{emp_row[0]}, {emp_row[1]}\n"
            response += f"  - Дата начала отпуска: {emp_row[3]}\n"
            response += f"  - Дата окончания отпуска: {emp_row[4]}\n\n"

    if not response:
        response = "Сегодня никто не в отпуске, и никто не уходит в отпуск в ближайшие 14 дней."

    messages = split_message(response)

    for msg in messages:

        await bot.send_message(message.chat.id, msg, parse_mode='Markdown')


'''
async def handle_additional_info(query):
    from main import bot
    chat_id = json.loads(query.data)["chat_id"]
    if chat_id in additional_info_storage:
        response = additional_info_storage[chat_id]
        messages = split_message(response)
        for message_group in messages:
            msg = ''.join(message_group)
            if msg.strip():  # Проверка, что сообщение не пустое
                await bot.send_message(chat_id, msg, parse_mode='Markdown')

        await bot.answer_callback_query(query.id)
    else:
        await bot.answer_callback_query(query.id, "Дополнительная информация недоступна.")
'''


@main_router.callback_query(F.data.contains("school"))
async def handle_schools_info(query):
    data = json.loads(query.data)
    print(f"Received callback school data: {data}")
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


@main_router.callback_query(F.data.contains("survey"))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext ):
    from main import bot
    
    data = await state.get_data()
    print(f'data in multipl: {data}')
    
    
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

@main_router.callback_query(F.data.startswith("tele2"), StateFilter(Survey.tele2_level))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext ):
    await state.update_data(tele2_level=query.data.split("_")[1])
  #  print(f'data в tele2_level: {data}')
    data = await state.get_data()
    
    user_id = query.from_user.id
    message_id=query.message.message_id
    survey_data = {
        "tele2_level": data.get("tele2_level"),
        # Дополнительные данные, если они есть
    }
   # survey_data = await state.update_data(tele2_level=query.data.split("_")[1])
    np = data['np']
    await save_survey_results(np, user_id, survey_data)
    await state.set_state(Survey.tele2_quality)
    

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Низкое", callback_data="tele2_quality_low"),
        InlineKeyboardButton(text="Среднее", callback_data="tele2_quality_mid"),
        InlineKeyboardButton(text="Хорошее", callback_data="tele2_quality_good")],
        [InlineKeyboardButton(text="Затрудняюсь ответить", callback_data="tele2_quality_unknown")]
    ])

    #await query.message.edit_text("Пожалуйста, оцените качество сигнала Tele2:", reply_markup=markup)
    try:
        # Attempt to edit the caption of the message
        await bot.edit_message_caption(chat_id=query.message.chat.id,
                                    message_id=query.message.message_id,
                                    caption="Оцените качество услуг Теле2",
                                    reply_markup=markup)
    except Exception as e:
        print(f"Failed to edit message caption: {str(e)}")
    



@main_router.callback_query(F.data.startswith("tele2_quality"), StateFilter(Survey.tele2_quality))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext ):
    
    await state.update_data(tele2_quality=query.data.split("_")[2])
    data = await state.get_data()
  #  print(f'data в t2_quality: {data}')
    user_id = query.from_user.id
    survey_data = {
        "tele2_quality": data.get("tele2_quality"),
        # Дополнительные данные, если они есть
    }
    print(f'survey_data в tele2_quality {survey_data}')
   # survey_data = await state.update_data(tele2_level=query.data.split("_")[1])
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

    # Отправляем сообщение с предложением оценить уровень сигнала
    
    try:
        # Attempt to edit the caption of the message
        await bot.send_animation(chat_id=query.message.chat.id, 
                         animation=mts_id, 
                         caption="Пожалуйста, оцените уровень сигнала МТС:", 
                         reply_markup=markup)
    except Exception as e:
        print(f"Failed to edit message caption: {str(e)}")









@main_router.callback_query(F.data.startswith("mts"), StateFilter(Survey.mts_level))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext ):
    await state.update_data(mts_level=query.data.split("_")[1])
    data = await state.get_data()
  #  print(f'data в mts level: {data}')
    user_id = query.from_user.id
    survey_data = {
        "mts_level": data.get("mts_level"),
        # Дополнительные данные, если они есть
    }
   # survey_data = await state.update_data(tele2_level=query.data.split("_")[1])
    np = data['np']
    await save_survey_results(np, user_id, survey_data)
    await state.set_state(Survey.mts_quality)
    

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Низкое", callback_data="mts_quality_low"),
        InlineKeyboardButton(text="Среднее", callback_data="mts_quality_mid"),
        InlineKeyboardButton(text="Хорошее", callback_data="mts_quality_good")],
        [InlineKeyboardButton(text="Затрудняюсь ответить", callback_data="mts_quality_unknown")]
    ])

    try:
        # Attempt to edit the caption of the message
        await bot.edit_message_caption(chat_id=query.message.chat.id,
                                    message_id=query.message.message_id,
                                    caption="Оцените качество сигнала МТС",
                                    reply_markup=markup)
    except Exception as e:
        print(f"Failed to edit message caption: {str(e)}")


@main_router.callback_query(F.data.startswith("mts_quality"), StateFilter(Survey.mts_quality))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext ):
    await state.update_data(mts_quality=query.data.split("_")[2])
    data = await state.get_data()
    
 #   print(f'data в mts_quality: {data}')
    user_id = query.from_user.id
    survey_data = {
        "mts_quality": data.get("mts_quality"),
        # Дополнительные данные, если они есть
    }
   # survey_data = await state.update_data(tele2_level=query.data.split("_")[1])
    np = data['np']
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

    # Отправляем сообщение с предложением оценить уровень сигнала
    
    try:
        # Attempt to edit the caption of the message
        await bot.send_animation(chat_id=query.message.chat.id, 
                         animation=megafon_id, 
                         caption="Пожалуйста, оцените уровень сигнала Мегафон:", 
                         reply_markup=markup)
    except Exception as e:
        print(f"Failed to edit message caption: {str(e)}")


@main_router.callback_query(F.data.startswith("megafon"), StateFilter(Survey.megafon_level))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext ):
    await state.update_data(megafon_level=query.data.split("_")[1])
    data = await state.get_data()
  #  print(f'data в megafon_level: {data}')
    user_id = query.from_user.id
    survey_data = {
        "megafon_level": data.get("megafon_level"),
        # Дополнительные данные, если они есть
    }
    
    np = data['np']
    await save_survey_results(np, user_id, survey_data)
    await state.set_state(Survey.megafon_quality)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Низкое", callback_data="megafon_quality_low"),
        InlineKeyboardButton(text="Среднее", callback_data="megafon_quality_mid"),
        InlineKeyboardButton(text="Хорошее", callback_data="megafon_quality_good")],
        [InlineKeyboardButton(text="Затрудняюсь ответить", callback_data="megafon_quality_unknown")]
    ])

    try:
        # Attempt to edit the caption of the message
        await bot.edit_message_caption(chat_id=query.message.chat.id,
                                    message_id=query.message.message_id,
                                    caption="Оцените качество услуг Мегафон",
                                    reply_markup=markup)
    except Exception as e:
        print(f"Failed to edit message caption: {str(e)}")


@main_router.callback_query(F.data.startswith("megafon_quality"), StateFilter(Survey.megafon_quality))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext ):
    await state.update_data(megafon_quality=query.data.split("_")[2])
    data = await state.get_data()
  #  print(f'data в megafon_quality: {data}')
    
    
    user_id = query.from_user.id
    survey_data = {
        "megafon_quality": data.get("megafon_quality"),
        # Дополнительные данные, если они есть
    }
   # survey_data = await state.update_data(tele2_level=query.data.split("_")[1])
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

    # Отправляем сообщение с предложением оценить уровень сигнала
    #CgACAgIAAxkBAAKO2WY0XeYvkJTECxFtYXIyzr7ZMmTTAALcTAAC7Y2gSQJWxCwQ2DtvNAQ
    #CgACAgIAAxkBAAKO12Y0XdG8exa0B19UHY15jEDLZpoYAALRTAAC7Y2gSU01Fs6vmKdjNAQ
    try:
        # Attempt to edit the caption of the message
        await bot.send_animation(chat_id=query.message.chat.id, 
                         animation=beeline_id, 
                         caption="Пожалуйста, оцените уровень сигнала Билайн:", 
                         reply_markup=markup)
    except Exception as e:
        print(f"Failed to edit message caption: {str(e)}")


@main_router.callback_query(F.data.startswith("beeline"), StateFilter(Survey.beeline_level))
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext ):
    await state.update_data(beeline_level=query.data.split("_")[1])
    data = await state.get_data()
   # print(f'data в beeline_level: {data}')
    user_id = query.from_user.id
    survey_data = {
        "beeline_level": data.get("beeline_level"),
        # Дополнительные данные, если они есть
    }
   # survey_data = await state.update_data(tele2_level=query.data.split("_")[1])
    np = data['np']
    await save_survey_results(np, user_id, survey_data)
    await state.set_state(Survey.beeline_quality)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Низкое", callback_data="beeline_quality_low"),
        InlineKeyboardButton(text="Среднее", callback_data="beeline_quality_mid"),
        InlineKeyboardButton(text="Хорошее", callback_data="beeline_quality_good")],
        [InlineKeyboardButton(text="Затрудняюсь ответить", callback_data="beeline_quality_unknown")]
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
async def handle_survey_chart(query: types.CallbackQuery, state: FSMContext ):
    await state.update_data(beeline_quality=query.data.split("_")[2])
    data = await state.get_data()
   # print(f'data в beeline_quality: {data}')
   
    
    
    user_id = query.from_user.id
    survey_data = {
        "beeline_quality": data.get("beeline_quality"),
        # Дополнительные данные, если они есть
    }
   # survey_data = await state.update_data(tele2_level=query.data.split("_")[1])
    np = data['np']
    await save_survey_results(np, user_id, survey_data)
    await state.clear()
    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)

    builder_loc = ReplyKeyboardBuilder()

    builder_loc.button(text='поделиться локацией', request_location=True)
  
    
    keyboard_loc = builder_loc.as_markup(resize_keyboard=True, one_time_keyboard=True)
    
    await query.message.answer("При желании можете поделиться своим местоположением 😊 \n (работает только со смартфона)", reply_markup=keyboard_loc)








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


async def create_individual_radar_chart(chat_id, data_df, title):
    print("create_individual_radar_chart called with data:", data_df)
    from main import bot
    # Создайте новое изображение с белым фоном
    img_width, img_height = 1000, 600
    img = Image.new('RGB', (img_width, img_height), 'white')
    draw = ImageDraw.Draw(img)

    # Добавьте заголовок
    title_font_path = "fonts/ofont.ru_Geologica.ttf"
    title_font = ImageFont.truetype(title_font_path, 30)
    text_font = ImageFont.truetype(title_font_path, 18)

    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width, title_height = title_bbox[2] - \
        title_bbox[0], title_bbox[3] - title_bbox[1]
    draw.text(((img_width - title_width) // 2, 20),
              title, fill="black", font=title_font)

    # Загрузите логотипы и уменьшите их
    logo_paths = [
        'logos/tele2_1.png',
        'logos/megafon_1.png',
        'logos/beeline_1.png',
        'logos/mts_1.png',
    ]

    logos = []
    # Уменьшаем МТС в 3 раза меньше и увеличиваем Билайн в 2 раза больше
    resize_factors = [0.1, 0.1, 0.1*2, 0.1/3]
    for i, path in enumerate(logo_paths):
        logo = Image.open(path)
        logo_width, logo_height = logo.size
        logos.append(logo.resize(
            (int(logo_width * resize_factors[i]), int(logo_height * resize_factors[i]))))

    # Добавьте логотипы
    column_width = img_width // 4
    for i, logo in enumerate(logos):
        x = column_width * i + (column_width - logo.width) // 2
        y = 100
        if i in [1, 2]:  # индексы для Билайн и Мегафон
            # Создаем отдельное изображение для наложения
            logo_img = Image.new(
                'RGBA', (img_width, img_height), (255, 255, 255, 0))
            logo_img.paste(logo, (x, y))

            # Накладываем логотип на основное изображение
            img = Image.alpha_composite(
                img.convert('RGBA'), logo_img).convert('RGB')
        else:
            # Для других логотипов просто вставляем их
            img.paste(logo, (x, y))

    # Создаем новый объект draw для текущего изображения
    draw = ImageDraw.Draw(img)

    # Сформулируйте текст для каждой строки в data_df и добавьте его на график
    operator_columns = [
        ('Уровень_Tele2', 'Качество_Tele2'),
        ('Уровень_Megafon', 'Качество_Megafon'),
        ('Уровень_Beeline', 'Качество_Beeline'),
        ('Уровень_MTS', 'Качество_MTS')
    ]

    y_start = y + logos[0].height + 20
    y_step = 20

    for idx, row_series in data_df.iterrows():
        for i, (level_column, quality_column) in enumerate(operator_columns):
            # Проверка на наличие данных для каждого оператора
            if pd.notnull(row_series[level_column]) or pd.notnull(row_series[quality_column]):
                text = f"{row_series.get(level_column, 'Нет данных')} {row_series.get(quality_column, 'Нет данных')}"
            else:
                text = "Нет данных"

            # Исправляем позиционирование текста
            x = column_width * i + (column_width - logos[i].width) // 2
            y_text = y_start + idx * y_step

            draw.text((x, y_text), text, fill="black", font=text_font)

    # Сохраните и отправьте изображение
    temp_file_path = "temp_survey_result.png"
    img.save(temp_file_path)

    # Отправляем изображение пользователю
    await bot.send_photo(chat_id, open(temp_file_path, 'rb'))

    # Удаляем временный файл
    os.remove(temp_file_path)
