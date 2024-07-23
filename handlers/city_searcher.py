from aiogram.types import Message
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from icecream import ic
from database.models import Cities, Espd





city_router = Router()

@city_router.message(F.chat.type == 'private')
async def handle_city_search(message: Message, state: FSMContext, session: AsyncSession, city_ids: List[int]):
    

    cities_query = select(Cities.city_full_name, Cities.selsovet, Cities.population_2010, Cities.population_2020,
                            Cities.television, Cities.beeline_level, Cities.beeline_quality, Cities.megafon_level,
                            Cities.megafon_quality, Cities.mts_level, Cities.mts_quality, Cities.tele2_level, Cities.tele2_quality,
                            Cities.taksophone_address, Cities.subsid_operator, Cities.subsid_year,
                            Cities.rank_ucn2023, Cities.number_of_votes_ucn2023, Cities.same_number_of_votes_ucn2023,
                            Cities.latitude, Cities.longitude, Cities.internet, Cities.arctic_zone)  \
                    .where(Cities.city_id.in_(city_ids))
        
    cities_result = await session.execute(cities_query)
    response_cities = cities_result.all()
    main_df = pd.DataFrame(response_cities)
    main_df = main_df.reset_index()
    if not main_df.empty:
        for i, row in main_df.iterrows():
            ic(row)
            row.ffill(inplace=True)
            #row.fillna(value='н/д', inplace=True, axis=1)
            ic(row)
            main_response = f'<b>{row['city_full_name']}</b>\n'
            if row['arctic_zone'] is True:
                main_response += '❄️Арктическая зона❄️\n'   
            main_response += f'👥население 2010 г: {row['population_2010']}\n'
            main_response += f'👥население 2020 г: {row['population_2020']}\n'
            if row['television'] != '':
                main_response += f'телевидение: {row['television']}\n'
            if row['taksophone_address'] != '':
                main_response += f'таксофон: {row['taksophone_address']}\n'    
            
            main_response += '\n📱Сотовая связь:\n'
            
            if row['tele2_level'] != '':
                main_response += f'Теле2: {row['tele2_level']} {row['tele2_quality']}\n'
            
            if row['mts_level'] != '':
                main_response += f'МТС: {row['mts_level']} {row['mts_quality']}\n'
                
            if row['megafon_level'] != '':
                main_response += f'Мегафон: {row['megafon_level']} {row['megafon_quality']}\n'
                
            if row['beeline_level'] != '':
                main_response += f'Билайн: {row['beeline_level']} {row['beeine_quality']}\n'
            
            if row['tele2_level'] == '' and row['mts_level'] == '' and row['megafon_level'] == '' and row['beeline_level'] == '':
                main_response += 'Отсутствует\n'
            
                    
            
        await message.answer(text=main_response, parse_mode='HTML')
    
    
    
    
    
    espd_query = select(Espd.functional_customer, Espd.name_of_institution, Espd.addres, Espd.technology_type,
                        Espd.internet_speed, Espd.contract, Espd.changes) \
                    .join(Cities, Cities.city_id == Espd.city_id) \
                    .where((Espd.changes != 'Исключение')&(Cities.city_id.in_(city_ids)))
                    
    espd_result = await session.execute(espd_query)
    response_espd = espd_result.all()
    espd_df = pd.DataFrame(response_espd)
    espd_df = espd_df.reset_index()
    espd_info = ''
    if not espd_df.empty:
        espd_info += '🏢Учреждения, подключенные по госпрограмме\n'
        for i, row in espd_df.iterrows():
            espd_info += f'{i+1}. <b>Тип:</b> {row['functional_customer']}\n<b>Наименование:</b> {row['name_of_institution']}\n'
            espd_info += f'<b>Адрес:</b> {row['addres']}\n<b>Тип подключения:</b> {row['technology_type']}\n<b>Пропускная способность:</b> {row['internet_speed']}\n<b>Контракт:</b> {row['contract']}'
    ic(espd_info)     
    
            
        
    
    
    
    
    
    
    
    
    
    
    
    
    