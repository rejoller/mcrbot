from aiogram import Router, F, types

from database.models import Users

from sqlalchemy import and_, update
from sqlalchemy.ext.asyncio import AsyncSession


router = Router()


@router.message(F.location)
async def handle_location(message: types.Message, session: AsyncSession):
    user_id = message.from_user.id
    latitude = message.location.latitude
    longitude = message.location.longitude    
    update_query = (
        update(Users)
        .where(and_(
            Users.user_id == user_id
        ))
        .values(latitude=latitude,
                longitude=longitude)
    )
    await message.answer('спасибо😉')
    await session.execute(update_query)
    await session.commit()

    
