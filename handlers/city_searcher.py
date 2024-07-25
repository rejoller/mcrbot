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
from users.user_states import Form
from utils.response_manager import main_response_creator, espd_response_creator, schools_response_creator




city_router = Router()







@city_router.message(F.text, F.chat.type == 'private', StateFilter(None))
async def handle_city_search(message: Message, state: FSMContext, session: AsyncSession):
    print('основной хэнд')
    cities = pd.read_json('cities.json')
    choised_np = message.text
    ic(choised_np)
    np_ids = cities.query(f'city_short_name == "{choised_np}"')['city_id'].to_list()

    
    if len(np_ids) == 1:
        await state.clear()
        builder = InlineKeyboardBuilder()
        main_response = await main_response_creator(session, city_id = int(np_ids[0]))
        await message.answer(text=main_response, parse_mode='HTML')
        
        
        espd_info= await espd_response_creator(session, city_id = int(np_ids[0]))
        schools_info = await schools_response_creator(session, city_id = int(np_ids[0]))

        if espd_info:
            builder.button(
                text="подключенные учреждения", callback_data=f'espd_data_{np_ids[0]}'
            )
        
        if schools_info:
            builder.button(
                text="школы", callback_data=f'schools_data_{np_ids[0]}'
            )
        builder.adjust(1)   
        keyboard = builder.as_markup()
        if keyboard:
            await message.answer('дополнительная информация', reply_markup=keyboard)
        
    
    if len(np_ids) > 1:
        await state.set_state(Form.waiting_number)
        cities_query = select(Cities.city_full_name).where(Cities.city_id.in_(np_ids)).order_by(Cities.city_full_name)        
        cities_result = await session.execute(cities_query)
        response_cities = pd.DataFrame(cities_result.all())
        ic(response_cities)
        

        builder = ReplyKeyboardBuilder()
        button_text = ''
        message_text = 'Найдено несколько населенных пунктов, выберите номер нужного❗️\n\n'
        
        list_of_lists = []
        for index, (key, value) in enumerate(response_cities['city_full_name'].items(), start=1):
            list_of_lists.append([key, np_ids[key], index])
            button_text = f'{index}'
            message_text += f'<b>{index}</b>. {value}\n'
            builder.button(text=button_text)
        await state.update_data(list_of_lists = list_of_lists)
        builder.adjust(4)
        keyboard_1 = builder.as_markup(resize_keyboard=True, one_time_keyboard=True, input_field_placeholder="Выберите населенный пункт")
        await message.answer(text=message_text, reply_markup=keyboard_1, parse_mode='HTML')
        return
    if len(np_ids) < 1:
        await message.answer(text='не найдено')
        
    
    
    
    
    
    
    
    
    
    
    
    