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

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        ic(event)
        return await handler(event, data)
            
            