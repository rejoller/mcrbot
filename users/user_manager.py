from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from database.models import Messages as Msgs, Users
from aiogram import types
from datetime import datetime as dt


class UserManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    def extract_user_data_from_query(self, query: types.CallbackQuery):
        return {
            'user_id': query.from_user.id,
            'first_name': query.from_user.first_name,
            'last_name': query.from_user.last_name,
            'username': query.from_user.username
        }
        
    def extract_user_data_from_message(self, message: types.Message):
        return {
            'user_id': message.from_user.id,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'username': message.from_user.username
        }

    async def add_user_if_not_exists(self, user_data: dict):
        add_user_query = insert(Users).values(
            user_id=user_data['user_id'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            username=user_data['username'],
            joined_at=dt.now(),
            is_admin=True if user_data['user_id'] == 964635576 else False
        ).on_conflict_do_nothing()
        await self.session.execute(add_user_query)
        await self.session.commit()




class MessagesManager:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    def extract_data_from_message(self, message: types.Message):
        return {
            'user_id': message.from_user.id,
            'date_send': message.date.strftime('%Y-%m-%d %H:%M:%S'),
            'message_text': message.text
        }
        
    async def add_message_if_not_exists(self, msg_data: dict, response = None):
        add_user_query = insert(Msgs).values(
            user_id=msg_data['user_id'],
            date_send=dt.strptime(msg_data['date_send'], '%Y-%m-%d %H:%M:%S'),
            message_text=msg_data['message_text'],
            response_text=response
        ).on_conflict_do_nothing()
        await self.session.execute(add_user_query)
        await self.session.commit()

