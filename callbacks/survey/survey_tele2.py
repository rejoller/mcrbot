import traceback
from aiogram import Router, F, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.models import Survey, Users
from media_files.animations import (beeline_id, tele2_id, megafon_id, mts_id)
from datetime import datetime as dt
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, select, update
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from icecream import ic

from users.user_manager import UserManager


router = Router()


@router.callback_query(F.data.startswith("start_survey_"))
async def handle_start_survey(query: types.CallbackQuery, state: FSMContext, session: AsyncSession):

    city_id = query.data.split('_')[2]
    user_id = query.from_user.id
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="4G", callback_data=f"tele2_4g_{city_id}"),
         InlineKeyboardButton(text="3G", callback_data=f"tele2_3g_{city_id}"),
         InlineKeyboardButton(text="2G", callback_data=f"tele2_2g_{city_id}")],
        [InlineKeyboardButton(text="Услуги отсутствуют", callback_data=f"tele2_none_{city_id}"),
         InlineKeyboardButton(text="Не знаю", callback_data=f"tele2_unknown_{city_id}")]
    ])

    await query.message.answer_animation(
        animation=tele2_id,
        caption="Пожалуйста, оцените уровень сигнала Tele2:",
        reply_markup=markup)


@router.callback_query(F.data.startswith("tele2_"), F.data.not_contains("tele2_none_"))
async def handle_select_tele2_quality(query: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    user_manager = UserManager(session)
    user_data = user_manager.extract_user_data_from_query(query)
    await user_manager.add_user_if_not_exists(user_data)

    user_id = query.from_user.id
    provider = query.data.split('_')[0]
    level = query.data.split('_')[1]
    city = query.data.split('_')[2]
    add_query = insert(Survey).values(
        city_id=int(city),
        user_id=int(user_id),
        import_time=dt.now(),
        provider=provider,
        level=level
    ).on_conflict_do_nothing()
    await session.execute(add_query)
    await session.commit()
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Низкое", callback_data=f"quality_tele2_low_{city}"),
         InlineKeyboardButton(
            text="Среднее", callback_data=f"quality_tele2_mid_{city}"),
         InlineKeyboardButton(
            text="Хорошее", callback_data=f"quality_tele2_good_{city}")],
        [InlineKeyboardButton(
            text="Затрудняюсь ответить", callback_data=f"quality_tele2_unknown_{city}")]
    ])

    await bot.edit_message_caption(chat_id=query.message.chat.id,
                                   message_id=query.message.message_id,
                                   caption="Оцените качество услуг Теле2",
                                   reply_markup=markup)









