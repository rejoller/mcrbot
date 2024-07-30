import traceback
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from sqlalchemy.dialects.postgresql import insert
from icecream import ic
from database.models import Cities, Espd
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.filters import StateFilter
from users.user_manager import MessagesManager, UserManager
from users.user_states import Form
from utils.input_manager import normalize_input
from utils.response_manager import main_response_creator, espd_response_creator, schools_response_creator
from cities import get_city_dict
from fuzzywuzzy import process


router = Router()


@router.message(F.animation)
async def echo_gif(message: Message):
    file_id = message.animation.file_id
    print(file_id)
    await message.answer(message.animation.file_id)


async def find_keys_by_value(search_value):
    city_dict = get_city_dict()
    keys = [key for key, (normalized_value, _) in city_dict.items(
    ) if normalized_value == search_value]
    return keys


async def find_similar_cities(search_value, threshold=70):
    city_dict = get_city_dict()
    all_cities = [similar_cities for key,
                  (_, similar_cities) in city_dict.items()]
    best_matches = process.extract(search_value, all_cities, limit=5)
    result = [match for match in best_matches if match[1] >= threshold]
    return result


@router.message(F.text, F.chat.type == 'private', StateFilter(None))
async def handle_city_search(message: Message, state: FSMContext, session: AsyncSession):
    user_manager = UserManager(session)
    user_data = user_manager.extract_user_data_from_message(message)
    await user_manager.add_user_if_not_exists(user_data)
    choised_np = normalize_input(message.text)
    np_ids = await find_keys_by_value(choised_np)

    if len(np_ids) == 1:
        await state.clear()
        builder_1 = InlineKeyboardBuilder()
        builder_2 = InlineKeyboardBuilder()
        builder_1.button(
            text="Оставить обратную связь", callback_data=f'start_survey_{np_ids[0]}'
        )
        keyboard_1 = builder_1.as_markup()

        main_response = await main_response_creator(session, city_id=int(np_ids[0]))
        
        msg_manager = MessagesManager(session)
        
        msg_data = msg_manager.extract_data_from_message(message)
        ic(type(msg_data))
        
        
        
        await message.answer(text=main_response, parse_mode='HTML', disable_web_page_preview=True, reply_markup=keyboard_1)
        await msg_manager.add_message_if_not_exists(msg_data, main_response)
        espd_info = await espd_response_creator(session, city_id=int(np_ids[0]))
        schools_info = await schools_response_creator(session, city_id=int(np_ids[0]))

        if espd_info:
            builder_2.button(
                text="подключенные учреждения", callback_data=f'espd_data_{np_ids[0]}'
            )

        if schools_info:
            builder_2.button(
                text="школы", callback_data=f'schools_data_{np_ids[0]}'
            )
            
        builder_2.adjust(1)
        keyboard_2 = builder_2.as_markup()
        if keyboard_2.inline_keyboard:
            await message.answer('дополнительная информация', reply_markup=keyboard_2)
        return

    if len(np_ids) > 1:
        await state.set_state(Form.waiting_number)
        cities_query = select(Cities.city_full_name).where(
            Cities.city_id.in_(np_ids)).order_by(Cities.city_full_name)
        cities_result = await session.execute(cities_query)
        response_cities = pd.DataFrame(cities_result.all())
        builder = ReplyKeyboardBuilder()
        button_text = ''
        message_text = 'Найдено несколько населенных пунктов, выберите номер нужного❗️\n\n'
        list_of_lists = []
        for index, (key, value) in enumerate(response_cities['city_full_name'].items(), start=1):
            list_of_lists.append([key, np_ids[key], index])
            button_text = f'{index}'
            message_text += f'<b>{index}</b>. {value}\n'
            builder.button(text=button_text)

        await state.update_data(list_of_lists=list_of_lists)
        builder.adjust(4)
        keyboard_1 = builder.as_markup(
            resize_keyboard=True, one_time_keyboard=True, input_field_placeholder="Выберите населенный пункт")
        await message.answer(text=message_text, reply_markup=keyboard_1, parse_mode='HTML')
        return
    else:
        similar_cities = await find_similar_cities(choised_np)
        if similar_cities != []:
            builder = ReplyKeyboardBuilder()
            message_text = 'Проверьте правильность написания населенного пункта и попробуйте ещё раз. Или выберите из списка ниже❗️\n\n'
            for city_name, _ in similar_cities:
                button_text = f'{city_name}'
                builder.button(text=button_text)
            builder.adjust(1)
            keyboard_2 = builder.as_markup(
                resize_keyboard=True, one_time_keyboard=True, input_field_placeholder="Выберите правильное наименование")
            await message.answer(text=message_text, reply_markup=keyboard_2, parse_mode='HTML')
        else:
            await message.answer('Не удалось найти информацию по данному запросу.\nВведите только наименование населенного пункта')
