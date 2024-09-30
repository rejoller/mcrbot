
from aiogram import Router, F, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.models import Survey
from media_files.animations import  megafon_id, mts_id
from datetime import datetime as dt
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, update



router = Router()

@router.callback_query(F.data.startswith("tele2_none_"))
@router.callback_query(F.data.startswith("quality_tele2_"))
async def handle_mts_level(query: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    print('mts')
    city = ''
    user_id = query.from_user.id
    splitted_data = query.data.split('_')
    if len(splitted_data) == 4:
        provider = splitted_data[1]
        quality = splitted_data[2]
        city = splitted_data[3]
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
        provider = provider
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

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="4G", callback_data=f"mts_4g_{city}"),
         InlineKeyboardButton(text="3G", callback_data=f"mts_3g_{city}"),
         InlineKeyboardButton(text="2G", callback_data=f"mts_2g_{city}")],
        [InlineKeyboardButton(text="Услуги отсутствуют", callback_data=f"mts_none_{city}"),
         InlineKeyboardButton(text="Не знаю", callback_data=f"mts_unknown_{city}")]
    ])

    message_id = query.message.message_id
    if message_id:
        await bot.delete_message(chat_id=query.message.chat.id, message_id=message_id)

    await query.message.answer_animation(
        animation=mts_id,
        caption="Пожалуйста, оцените уровень сигнала МТС:",
        reply_markup=markup)
    await query.answer()


@router.callback_query(F.data.startswith("mts_"), F.data.not_contains("mts_none"))
async def handle_mts_quality(query: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
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
            text="Низкое", callback_data=f"quality_mts_low_{city}"),
         InlineKeyboardButton(
            text="Среднее", callback_data=f"quality_mts_mid_{city}"),
         InlineKeyboardButton(
            text="Хорошее", callback_data=f"quality_mts_good_{city}")],
        [InlineKeyboardButton(
            text="Затрудняюсь ответить", callback_data=f"quality_mts_unknown_{city}")]
    ])

    await bot.edit_message_caption(chat_id=query.message.chat.id,
                                   message_id=query.message.message_id,
                                   caption="Оцените качество услуг МТС",
                                   reply_markup=markup)


@router.callback_query(F.data.contains("mts_none"))
@router.callback_query(F.data.startswith("quality_mts_"), F.data.not_contains("mts_none"))
async def handle_megafon_level(query: types.CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    user_id = query.from_user.id
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
        
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="4G", callback_data=f"megafon_4g_{city}"),
         InlineKeyboardButton(text="3G", callback_data=f"megafon_3g_{city}"),
         InlineKeyboardButton(text="2G", callback_data=f"megafon_2g_{city}")],
        [InlineKeyboardButton(text="Услуги отсутствуют", callback_data=f"megafon_none_{city}"),
         InlineKeyboardButton(text="Не знаю", callback_data=f"megafon_unknown_{city}")]
    ])

    message_id = query.message.message_id
    if message_id:
        await bot.delete_message(chat_id=query.message.chat.id, message_id=message_id)

    await query.message.answer_animation(
        animation=megafon_id,
        caption="Пожалуйста, оцените уровень сигнала Мегафон:",
        reply_markup=markup)
    await query.answer()