import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter


from database.models import Cities
from users.user_manager import MessagesManager
from users.user_states import Form
from icecream import ic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from sqlalchemy.dialects.postgresql import insert

from utils.response_manager import espd_response_creator, get_coordinates, main_response_creator, schools_response_creator


router = Router()


@router.message(StateFilter(Form.waiting_number), F.text)
async def handle_start_new_dialog(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    many_cities = data.get('list_of_lists')
    selected_np = message.text
    if selected_np == "Отмена":
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except:
            logging.exception('Не удалось удалить сообщение')
        await message.answer('Поиск отменен.', reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return
    if not selected_np.isdigit():
        await ('Введено некорректное значение. Пожалуйста, введите число.')
        return
    index = int(selected_np)
    if index <= 0 or index > len(many_cities):
        await message.answer(f'Введено некорректное значение. Пожалуйста, введите число в диапазоне от 1 до {len(many_cities)}.')
        return

    index_to_city = {index: key for _, key, index in many_cities}

    async def get_city_id_by_index(user_index):
        return index_to_city.get(user_index, "Индекс не найден")
    city_id = await get_city_id_by_index(int(selected_np))

    if city_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except:
            logging.exception('Не удалось удалить сообщение')
        latitude, longitude = await get_coordinates(session, city_id=int(city_id))
        main_response = await main_response_creator(session, city_id=int(city_id))
        await bot.send_location(chat_id=message.from_user.id, latitude=latitude, longitude=longitude)
        await state.clear()
        builder_1 = InlineKeyboardBuilder()
        builder_2 = InlineKeyboardBuilder()
        main_response = await main_response_creator(session, city_id=int(city_id))
        builder_1.button(
            text="Оставить обратную связь", callback_data=f'start_survey_{int(city_id)}'
        )
        keyboard_1 = builder_1.as_markup()
        await message.answer(text='<b>Выбранный населенный пункт✅</b>', parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove())
        await message.answer(text=main_response, parse_mode='HTML', disable_web_page_preview=True, reply_markup=keyboard_1)

        espd_info, elements_number = await espd_response_creator(session, city_id=int(city_id))

        schools_info, schools_elements_number = await schools_response_creator(session, city_id=int(city_id))

        if espd_info:
            builder_2.button(
                text=f"🏢подключенные учреждения ({elements_number})", callback_data=f'espd_data_{int(city_id)}'
            )

        if schools_info:
            builder_2.button(
                text=f"🏫школы ({schools_elements_number})", callback_data=f'schools_data_{int(city_id)}'
            )

        builder_2.adjust(1)
        keyboard_2 = builder_2.as_markup()
        if keyboard_2.inline_keyboard:
            await message.answer('дополнительная информация', reply_markup=keyboard_2)
