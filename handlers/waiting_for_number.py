from aiogram import Router
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart, StateFilter, CommandObject
from aiogram.fsm.state import State, StatesGroup
import pandas as pd

from database.models import Cities
from users.user_states import Form
from icecream import ic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from sqlalchemy.dialects.postgresql import insert

from utils.response_manager import espd_response_creator, main_response_creator, schools_response_creator




waiting_of_number_router = Router()






@waiting_of_number_router.message(StateFilter(Form.waiting_number), F.text)
async def handle_start_new_dialog(message: Message, state: FSMContext, session: AsyncSession):
    print("ожидание номера")
    data = await state.get_data()
    many_cities = data.get('list_of_lists')
    ic(many_cities)
    
    selected_np = message.text
    print(type(selected_np))
    
    index_to_city = {index: key for _, key, index in many_cities}
    async def get_city_id_by_index(user_index):
        return index_to_city.get(user_index, "Индекс не найден")
    
    city_id = await get_city_id_by_index(int(selected_np))
    ic(type(city_id))

    if city_id:
        await state.clear()
        builder = InlineKeyboardBuilder()
        main_response = await main_response_creator(session, city_id = int(city_id))
        await message.answer(text=main_response, parse_mode='HTML', disable_web_page_preview=True)
        
        
        espd_info= await espd_response_creator(session, city_id = int(city_id))
        schools_info = await schools_response_creator(session, city_id = int(city_id))

        if espd_info:
            builder.button(
                text="подключенные учреждения", callback_data=f'espd_data_{int(city_id)}'
            )
        
        if schools_info:
            builder.button(
                text="школы", callback_data=f'schools_data_{int(city_id)}'
            )
            
            
        builder.adjust(1)
        keyboard = builder.as_markup()
        print(keyboard)
        if keyboard.inline_keyboard:
            await message.answer('дополнительная информация', reply_markup=keyboard)
        
        
    
        
    