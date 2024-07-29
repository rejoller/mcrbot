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


router = Router()



@router.callback_query(F.data.startswith("beeline_"), F.data.not_contains("beeline_none"))
async def handle_beeline_level(query: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    print('handle_beeline_level')
    user_id = query.from_user.id
    splitted_data = query.data.split('_')
    if len(splitted_data) == 4:
        provider = query.data.split('_')[1]
        quality = query.data.split('_')[2]
        city = query.data.split('_')[3]
        update_query = (
            update(Survey)
            .where(and_(
                Survey.user_id == user_id,
                Survey.provider == provider,
                Survey.city_id == int(city)
            ))
            .values(quality=quality)
        )

        await session.execute(update_query)
        await session.commit()
        
    if len(splitted_data) == 3:
        ic(splitted_data)
        provider = splitted_data[0]
        ic(provider)
        level = splitted_data[1]
        ic(level)
        city = splitted_data[2]
        ic(city)
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
            text="Низкое", callback_data=f"quality_beeline_low_{city}"),
         InlineKeyboardButton(
            text="Среднее", callback_data=f"quality_beeline_mid_{city}"),
         InlineKeyboardButton(
            text="Хорошее", callback_data=f"quality_beeline_good_{city}")],
        [InlineKeyboardButton(
            text="Затрудняюсь ответить", callback_data=f"quality_beeline_unknown_{city}")]
    ])

    await bot.edit_message_caption(chat_id=query.message.chat.id,
                                   message_id=query.message.message_id,
                                   caption="Оцените качество услуг Билайн",
                                   reply_markup=markup)


@router.callback_query(F.data.contains("beeline_none"))
@router.callback_query(F.data.startswith("quality_beeline_"))
async def handle_beeline_quality(query: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    print('handle_beeline_quality')
    user_id = query.from_user.id
    ic(query.data)
    city = ''
    user_id = query.from_user.id
    splitted_data = query.data.split('_')
    if len(splitted_data) == 4:
        provider = query.data.split('_')[1]
        quality = query.data.split('_')[2]
        city = query.data.split('_')[3]
        update_query = (
            update(Survey)
            .where(and_(
                Survey.user_id == user_id,
                Survey.provider == provider,
                Survey.city_id == int(city)
            ))
            .values(quality=quality)
        )

        await session.execute(update_query)
        await session.commit()
        
    if len(splitted_data) == 3:
        provider = splitted_data[0]
        level = splitted_data[1]
        city = splitted_data[2]
        add_query = insert(Survey).values(
            city_id=int(city),
            user_id=int(user_id),
            import_time=dt.now(),
            provider=provider,
            level=level
        ).on_conflict_do_nothing()
        await session.execute(add_query)
        await session.commit()

    message_id = query.message.message_id
    ic(message_id)
    if message_id:

        await bot.delete_message(chat_id=query.message.chat.id, message_id=message_id)

    builder_loc = ReplyKeyboardBuilder()

    builder_loc.row(types.KeyboardButton(text='поделиться локацией', request_location=True),
                    types.KeyboardButton(text='поделиться контактом', request_contact=True))

    keyboard_loc = builder_loc.as_markup(
        resize_keyboard=True, one_time_keyboard=True)

    await query.message.answer("При желании можете поделиться своим местоположением и номером телефона с нами 😊 \n (работает только со смартфона)", reply_markup=keyboard_loc)