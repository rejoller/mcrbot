

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReactionTypeEmoji, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types, Router, F
import asyncio
import re
from aiogram.types.web_app_info import WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from additional import split_message
from handlers import Form
from google_connections import (get_authorized_client_and_spreadsheet, search_yandex_2023_values, search_in_pokazatel_504p, search_in_ucn2,
                                search_schools_values, load_otpusk_data, search_values, search_values_levenshtein, search_szoreg_values, get_value, init_redis)
from mongo_connect import search_survey_results
import json
import html

main_router=Router()


info_text_storage = {}
user_messages = {}
additional_info_storage = {}
szoreg_info_storage = {}
schools_info_storage = {}
message_storage = {}
survey_data_storage = {}
response_storage = {}



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
                search_in_pokazatel_504p(selected_np[4], redis))
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

            async with asyncio.TaskGroup() as tg:
                task1 = tg.create_task(
                    get_value(found_values[index - 1], 20))
                task2 = tg.create_task(
                    get_value(found_values[index - 1], 13))
                task3 = tg.create_task(
                    get_value(found_values[index - 1], 14))
                task4 = tg.create_task(
                    get_value(found_values[index - 1], 12))
                task5 = tg.create_task(
                    get_value(found_values[index - 1], 6))
                task6 = tg.create_task(
                    get_value(found_values[index - 1], 9))
                task7 = tg.create_task(
                    get_value(found_values[index - 1], 2))
                task8 = tg.create_task(
                    get_value(found_values[index - 1], 5))
                task9 = tg.create_task(
                    get_value(found_values[index - 1], 24))

                selsovet_info = await task1
                tanya_sub_info_year = await task2
                tanya_sub_info_provider = await task3
                taksofony_info = await task4
                arctic_info = await task5
                internet_info = await task6
                population_2010 = await task7
                population_2020 = await task8
                itog_ucn_2023 = await task9

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

        response += f'\n🌐интернет: {internet_info}️\n'
        response += f'⠀'
        response += f'<pre>📱Сотовая связь:\n{pokazatel_504p_response}</pre>\n'

        if tanya_sub_info_year and tanya_sub_info_provider:
            response += f'\n\nнаселенный пункт был подключен в рамках государственной программый "Развитие информационного общества" в {tanya_sub_info_year} году, оператор {tanya_sub_info_provider}'

        if itog_ucn_2023:
            response += f'\n\nкомментарий Минцифры России об УЦН 2024: {itog_ucn_2023}'

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
        response += f'⠀'
        await bot.send_message(message.chat.id, response, parse_mode='HTML', disable_web_page_preview=True, reply_markup=survey_builder.as_markup())

        builder_2 = InlineKeyboardBuilder()

        if survey_results_values:
            survey_data_storage[message.chat.id] = survey_results_values
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Показать результаты опроса ({len(survey_results_values)})", callback_data=json.dumps(
                    {"type": "2_survey_results", "chat_id": message.chat.id}))]
            ])
            builder_2.attach(InlineKeyboardBuilder.from_markup(markup))

        if szoreg_values:

            szoreg_response = '🏢<b>Учреждения, подключенные по госпрограмме</b>\n\n'
            for i, row in enumerate(szoreg_values, 1):
                if len(row) > 6:

                    szoreg_response += f'\n{i}. <b>Тип:</b> {row[7]}\n<b>Наименование:</b> {row[8]}\n<b>Адрес:</b> {row[5]} \n<b>Тип подключения:</b> {row[6]}\n<b>Пропускная способность:</b> {row[9]}\n<b>Контракт:</b> {row[10]}\n'
                else:
                    print(f'Строка {i} слишком короткая для обработки: {row}')

            szoreg_info_storage[message.chat.id] = szoreg_response
            callback_data = json.dumps(
                {"type": "2_szoreg_info", "chat_id": message.chat.id})

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
                    {"type": "2_schools_info", "chat_id": message.chat.id}))]
            ])
            builder_2.attach(InlineKeyboardBuilder.from_markup(markup))

        if schools_values or szoreg_values or survey_results_values:
            await message.answer("Дополнительная информация", reply_markup=builder_2.as_markup())

        else:
            await bot.send_message(message.chat.id, "Нет дополнительной информации для отображения.")

    except ValueError:

        await bot.send_message(message.chat.id, 'Введено некорректное значение. Пожалуйста, введите число в диапазоне от 1 до {}.'.format(len(found_values)))