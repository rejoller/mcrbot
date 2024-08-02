import traceback
from aiogram import types, F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from icecream import ic

from utils.message_splitter import split_message
from utils.response_manager import espd_no_tags_response_creator, espd_response_creator

router = Router()

@router.callback_query(F.data.startswith('espd_data_'))
async def handle_waiting_for_choise(query: types.CallbackQuery, session: AsyncSession):
    city_id = query.data.split('_')[2]
    espd_info, elements_number= await espd_response_creator(session, city_id = int(city_id))    
    msg_parts = await split_message(espd_info)
    try:
        for part in msg_parts:
            await query.message.answer(text=part, parse_mode='HTML')
    except:
        espd_info= await espd_no_tags_response_creator(session, city_id = int(city_id))    
        msg_parts = await split_message(espd_info)
        for part in msg_parts:
            await query.message.answer(text=part, parse_mode='HTML')
        