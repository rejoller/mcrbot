import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from db_config import (user, password, host, port, database)
from models import Base

DBURL=f'postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}'


engine = create_async_engine(DBURL, echo=False)
session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        

async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
      
        
        
asyncio.run(create_db())