from datetime import datetime
import json
from zoneinfo import ZoneInfo
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import types, Router, F
from additional import split_message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import Message
from animations_providers import (megafon_id, mts_id, tele2_id, beeline_id)
from mongo_connect import save_survey_results, search_survey_results
from main import bot
from images import default_profile


main_router = Router()

class Survey(StatesGroup):
    tele2_level = State()
    tele2_quality = State()
    megafon_level = State()
    megafon_quality = State()
    mts_level = State()
    mts_quality = State()
    beeline_level = State()
    beeline_quality = State()


from handlers import additional_info_storage, szoreg_info_storage, schools_info_storage, message_storage, survey_data_storage, response_storage



@main_router.callback_query(F.data.in["szoreg_info", "2_szoreg_info"])
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
        print("Информация для данного chat_id не найдена в хранилище szore.")
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
