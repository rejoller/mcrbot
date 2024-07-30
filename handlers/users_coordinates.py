from aiogram import Router, F, types
from sqlalchemy import and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Users


router = Router()


@router.message(F.location)
async def handle_location(message: types.Message, session: AsyncSession):
    user_id = message.from_user.id
    latitude = message.location.latitude,
    longitude = message.location.longitude
    
    await message.answer('спасибо😉')
    update_query = (
        update(Users)
        .where(and_(
            Users.user_id == user_id
        ))
        .values(latitude=latitude,
                longitude=longitude)
    )

    await session.execute(update_query)
    await session.commit()



    
@router.message(F.location)
async def handle_contact(message: types.Message, session: AsyncSession):
    
    
    user_id = message.from_user.id
    contact_data = message.contact.phone_number
    
    await message.answer('спасибо😉')
    update_query = (
        update(Users)
        .where(and_(
            Users.user_id == user_id
        ))
        .values(phone_number=contact_data)
    )

    await session.execute(update_query)
    await session.commit()
    
