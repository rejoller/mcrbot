import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from sqlalchemy.dialects.postgresql import insert
from aiogram.fsm.context import FSMContext
from database.models import Cities, Espd, Schools
from aiogram.types import Message
from icecream import ic







async def get_coordinates(session: AsyncSession, city_id = None):

    cities_query = select(Cities.latitude, Cities.longitude)  \
                    .where(Cities.city_id ==city_id)
        
    cities_result = await session.execute(cities_query)
    response_cities = cities_result.all()
    coordinates = pd.DataFrame(response_cities).to_string()
    latitude = coordinates.split()[3]
    longitude = coordinates.split()[4]
    
    return latitude, longitude






async def main_response_creator(session: AsyncSession, city_id = None):

    cities_query = select(Cities.city_full_name, Cities.selsovet, Cities.population_2010, Cities.population_2020,
                            Cities.television, Cities.beeline_level, Cities.beeline_quality, Cities.megafon_level,
                            Cities.megafon_quality, Cities.mts_level, Cities.mts_quality, Cities.tele2_level, Cities.tele2_quality,
                            Cities.taksophone_address, Cities.subsid_operator, Cities.subsid_year, Cities.date_of_update_ucn2023,
                            Cities.rank_ucn2023, Cities.number_of_votes_ucn2023, Cities.same_number_of_votes_ucn2023,
                            Cities.latitude, Cities.longitude, Cities.internet, Cities.arctic_zone)  \
                    .where(Cities.city_id ==city_id)
        
    cities_result = await session.execute(cities_query)
    response_cities = cities_result.all()
    main_df = pd.DataFrame(response_cities)
    main_df = main_df.reset_index()
    main_response=''
    if not main_df.empty:
        for i, row in main_df.iterrows():
            row.fillna('')
            main_response = f'<b>{row["city_full_name"]}</b>\n\n'
            if row['selsovet'] != '':
                main_response += f'{row["selsovet"]}\n\n'
            if row['arctic_zone'] == True:
                main_response += '❄️Арктическая зона❄️\n\n'            
            main_response += f'👥население 2010 г: {row["population_2010"]}\n'
            main_response += f'👥население 2020 г: {row["population_2020"]}\n'
            if row['television'] != None:
                main_response += f'📺телевидение: {row["television"]}\n'
            if row['taksophone_address'] != '':
                main_response += f'☎️таксофон: {row["taksophone_address"]}\n'    
            main_response += '\n<pre>'
            main_response += '📱Сотовая связь:\n'
            
            if row['tele2_level'] != None:
                main_response += f'Теле2: {row["tele2_level"]} {row["tele2_quality"].lower()}\n'
            
            if row['mts_level'] != None:
                main_response += f'МТС: {row["mts_level"]} {row["mts_quality"].lower()}\n'
                
            if row['megafon_level'] != None:
                main_response += f'Мегафон: {row["megafon_level"]} {row["megafon_quality"].lower()}\n'
                
            if row['beeline_level'] != None:
                main_response += f'Билайн: {row["beeline_level"]} {row["beeline_quality"].lower()}\n'
            
            if row['tele2_level'] == None and row['mts_level'] == None and row['megafon_level'] == None and row['beeline_level'] == None:
                main_response += 'Отсутствует\n'
            main_response += '</pre>\n'
            if row['subsid_operator'] != 'None' and row['subsid_operator'] != '':
                main_response += (f'\n\nнаселенный пункт был подключен в рамках государственной программый "Развитие информационного общества"'
                                f'в {row["subsid_year"]} году, оператор {row["subsid_operator"]}\nhttp://digital.krskstate.ru/subsidiimo/page17877')
                
            if row['rank_ucn2023'] != None:
                main_response += f'\n\n<b>Голосование УЦН 2024</b>\nhttps://www.gosuslugi.ru/inet\n\nколичество голосов: <b>{row["number_of_votes_ucn2023"]} </b>'
                main_response += f'(такое же количество\nголосов имеют {row["same_number_of_votes_ucn2023"]} населенных пунктов)'
                main_response += f'\n🏆Место в рейтинге {row["rank_ucn2023"]}\n'   
    return main_response
    
    
    
async def espd_response_creator(session: AsyncSession, city_id = None):

    espd_query = select(Espd.functional_customer, Espd.name_of_institution, Espd.addres, Espd.technology_type,
                        Espd.internet_speed, Espd.contract, Espd.changes) \
                    .where((Espd.city_id == city_id) & or_(Espd.changes != 'Исключение', Espd.changes.is_(None)))

    espd_result = await session.execute(espd_query)
    response_espd = espd_result.all()
    espd_df = pd.DataFrame(response_espd)
    espd_df = espd_df.reset_index()
    elements_number = len(espd_df)
    espd_info = ''
    if not espd_df.empty:
        espd_info += '🏢Учреждения, подключенные по госпрограмме\n\n'
        for i, row in espd_df.iterrows():
            i+=1
            espd_info += f'<blockquote>{i}. <b>Тип:</b> {row["functional_customer"]}\n<b>Наименование:</b> {row["name_of_institution"]}\n'
            espd_info += f'<b>Адрес:</b> {row["addres"]}\n<b>Тип подключения:</b> {row["technology_type"]}\n<b>Пропускная способность: </b>'
            espd_info += f'{row["internet_speed"]}\n<b>Контракт:</b> {row["contract"]}</blockquote>\n\n'
        
    return espd_info, elements_number



async def espd_no_tags_response_creator(session: AsyncSession, city_id = None):

    espd_query = select(Espd.functional_customer, Espd.name_of_institution, Espd.addres, Espd.technology_type,
                        Espd.internet_speed, Espd.contract, Espd.changes) \
                    .where((Espd.city_id == city_id) & or_(Espd.changes != 'Исключение', Espd.changes.is_(None)))

    espd_result = await session.execute(espd_query)
    response_espd = espd_result.all()
    espd_df = pd.DataFrame(response_espd)
    espd_df = espd_df.reset_index()
    elements_number = len(espd_df)
    espd_info = ''
    if not espd_df.empty:
        espd_info += '🏢Учреждения, подключенные по госпрограмме\n\n'
        for i, row in espd_df.iterrows():
            i+=1
            espd_info += f'{i}. <b>Тип:</b> {row["functional_customer"]}\n<b>Наименование:</b> {row["name_of_institution"]}\n'
            espd_info += f'<b>Адрес:</b> {row["addres"]}\n<b>Тип подключения:</b> {row["technology_type"]}\n<b>Пропускная способность: </b>'
            espd_info += f'{row["internet_speed"]}\n<b>Контракт:</b> {row["contract"]}\n\n'
        
    return espd_info, elements_number



async def schools_response_creator(session: AsyncSession, city_id = None):

    schools_query = select(Schools.name_of_school, Schools.school_adress, Schools.internet_speed, Schools.technology_type) \
                    .where(Schools.city_id == city_id)

    schools_result = await session.execute(schools_query)
    response_schools = schools_result.all()
    schools_df = pd.DataFrame(response_schools)
    schools_df = schools_df.reset_index()
    schools_info = ''
    schools_elements_number = len(schools_df)
    
    if not schools_df.empty:
        schools_info += '<b>Школы</b>:\n\n'
        for i, row in schools_df.iterrows():
            i += 1
            schools_info += f'<blockquote>{i}.<b>{row["name_of_school"]}</b>\n{row["school_adress"]}\n'
            schools_info += f'{row["technology_type"]}, {row["internet_speed"]}</blockquote>\n\n'
        
    return schools_info, schools_elements_number