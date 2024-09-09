from aiogram import types, F, Router

from sqlalchemy.ext.asyncio import AsyncSession

from utils.response_manager import  schools_response_creator
from utils.message_splitter import split_message

router = Router()

@router.callback_query(F.data.startswith('schools_data_'))
async def handle_waiting_for_choise(query: types.CallbackQuery, session: AsyncSession):
    city_id = query.data.split('_')[2]
    schools_info, schools_elements_number = await schools_response_creator(session, city_id = int(city_id))
    msg_parts = await split_message(schools_info)
    
    for part in msg_parts:
        await query.message.answer(text=part, parse_mode='HTML')