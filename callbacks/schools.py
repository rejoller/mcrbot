from aiogram import types, F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from icecream import ic

from utils.response_manager import  schools_response_creator
from utils.message_splitter import split_message

schools_router = Router()

@schools_router.callback_query(F.data.startswith('schools_data_'))
async def handle_waiting_for_choise(query: types.CallbackQuery, session: AsyncSession):
    print('школы')
    city_id = query.data.split('_')[2]
    schools_info = await schools_response_creator(session, city_id = int(city_id))
    msg_parts = await split_message(schools_info)
    for part in msg_parts:
        await query.message.answer(text=part, parse_mode='HTML')