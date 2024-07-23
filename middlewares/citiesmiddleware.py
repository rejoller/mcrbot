from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable, List
from aiogram.types import TelegramObject, Message
from aiogram  import BaseMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker
import pandas as pd
from icecream import ic



class CitiesMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker, cities: List[str]):
        self.session_pool = session_pool
        self.cities = cities
        ic(self.cities.head())
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        ic(event.message.text)
        matching_cities = self.cities[self.cities['city_short_name'] == event.message.text]

        if not matching_cities.empty:
            city_ids = matching_cities['city_id'].tolist()
            ic(f"City found: {event.message.text}, IDs: {city_ids}")
            async with self.session_pool() as session:
                data['session'] = session
                data['city_ids'] = city_ids
                return await handler(event, data)