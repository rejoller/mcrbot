from aiogram import Router, F, types

from database.models import Users

from sqlalchemy import and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from icecream import ic


router = Router()


@router.message(F.contact)
async def handle_contacts(message: types.Message, session: AsyncSession):
    user_id = message.from_user.id
    contact_data = {"contact": message.contact.phone_number}
    contact = [value for  value in contact_data.values()][0]
    update_query = (
        update(Users)
        .where(and_(
            Users.user_id == user_id
        ))
        .values(phone_number=contact)
    )
    await message.answer('спасибо😉')
    await session.execute(update_query)
    await session.commit()
    