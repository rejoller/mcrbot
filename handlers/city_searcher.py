from aiogram.types import Message
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from sqlalchemy.dialects.postgresql import insert
from icecream import ic
from database.models import Cities, Espd





city_router = Router()

@city_router.message(F.chat.type == 'private')
async def handle_city_search(message: Message, state: FSMContext, session: AsyncSession, city_ids: List[int]):
    

    cities_query = select(Cities.city_full_name, Cities.selsovet, Cities.population_2010, Cities.population_2020,
                            Cities.television, Cities.beeline_level, Cities.beeline_quality, Cities.megafon_level,
                            Cities.megafon_quality, Cities.mts_level, Cities.mts_quality, Cities.tele2_level, Cities.tele2_quality,
                            Cities.taksophone_address, Cities.subsid_operator, Cities.subsid_year, Cities.date_of_update_ucn2023,
                            Cities.rank_ucn2023, Cities.number_of_votes_ucn2023, Cities.same_number_of_votes_ucn2023,
                            Cities.latitude, Cities.longitude, Cities.internet, Cities.arctic_zone)  \
                    .where(Cities.city_id.in_(city_ids))
        
    cities_result = await session.execute(cities_query)
    response_cities = cities_result.all()
    main_df = pd.DataFrame(response_cities)
    main_df = main_df.reset_index()
    if not main_df.empty:
        for i, row in main_df.iterrows():
            row.fillna('')
            main_response = f'<b>{row['city_full_name']}</b>\n'
            if row['selsovet'] != None:
                main_response += f'{row['selsovet']}\n\n'
            if row['arctic_zone'] == True:
                main_response += '❄️Арктическая зона❄️\n\n'   
            main_response += f'👥население 2010 г: {row['population_2010']}\n'
            main_response += f'👥население 2020 г: {row['population_2020']}\n'
            if row['television'] != None:
                main_response += f'телевидение: {row['television']}\n'
            if row['taksophone_address'] != None:
                main_response += f'таксофон: {row['taksophone_address']}\n'    
            main_response += '\n<pre>'
            main_response += '\n📱Сотовая связь:\n'
            
            if row['tele2_level'] != None:
                main_response += f'Теле2: {row['tele2_level']} {row['tele2_quality']}\n'
            
            if row['mts_level'] != None:
                main_response += f'МТС: {row['mts_level']} {row['mts_quality']}\n'
                
            if row['megafon_level'] != None:
                main_response += f'Мегафон: {row['megafon_level']} {row['megafon_quality']}\n'
                
            if row['beeline_level'] != None:
                main_response += f'Билайн: {row['beeline_level']} {row['beeline_quality']}\n'
            
            if row['tele2_level'] == None and row['mts_level'] == None and row['megafon_level'] == None and row['beeline_level'] == None:
                main_response += 'Отсутствует\n'
            main_response += '</pre>'
            if row['subsid_operator'] != None:
                main_response += (f'\n\nнаселенный пункт был подключен в рамках государственной программый "Развитие информационного общества"'
                                f'в {row['subsid_year']} году, оператор {row['subsid_operator']}\n')
                
            if row['rank_ucn2023'] != None:
                main_response += f'\n\n<b>Голосование УЦН 2024</b>\nhttps://www.gosuslugi.ru/inet\n\nколичество голосов: <b>{row['number_of_votes_ucn2023']} </b>'
                main_response += f'(такое же количество\nголосов имеют {row['same_number_of_votes_ucn2023']} населенных пунктов)'
                main_response += f'\n🏆Место в рейтинге {row['rank_ucn2023']}\n'   
            
        await message.answer(text=main_response, parse_mode='HTML')
    
    
    
    ic(city_ids)
    ic(city_ids[0])
    espd_query = select(Espd.functional_customer, Espd.name_of_institution, Espd.addres, Espd.technology_type,
                        Espd.internet_speed, Espd.contract, Espd.changes) \
                    .where((Espd.city_id == city_ids[0]) & or_(Espd.changes != 'Исключение', Espd.changes.is_(None)))
    ic(espd_query)            
    espd_result = await session.execute(espd_query)
    response_espd = espd_result.all()
    espd_df = pd.DataFrame(response_espd)
    espd_df = espd_df.reset_index()
    espd_info = ''
    if not espd_df.empty:
        espd_info += '🏢Учреждения, подключенные по госпрограмме\n'
        for i, row in espd_df.iterrows():
            espd_info += f'{i+1}. <b>Тип:</b> {row['functional_customer']}\n<b>Наименование:</b> {row['name_of_institution']}\n'
            espd_info += f'<b>Адрес:</b> {row['addres']}\n<b>Тип подключения:</b> {row['technology_type']}\n<b>Пропускная способность:</b>'
            espd_info += f'{row['internet_speed']}\n<b>Контракт:</b> {row['contract']}'
    ic(espd_info)     
    
            
        
    
    
    
    
    
    
    
    
    
    
    
    
    