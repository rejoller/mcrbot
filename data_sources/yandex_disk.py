from io import BytesIO
import logging
import pandas as pd
import requests
import yadisk
import os
from icecream import ic

from config import OAUTH_TOKEN
from database.models import Cities
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import literal, update

from utils.time_limiter import timeout



def exctract_signal_level(signal_info):
    if signal_info !=  '\\xa0' and pd.notnull(signal_info):   
        signal_info = signal_info.replace('(', ' ').replace(')','').split(' ')
        if len(signal_info)>1:
            level = signal_info[1]
            return level
    else:
        return None
    
    
def exctract_quality_level(signal_info):
    if signal_info !=  '\\xa0' and pd.notnull(signal_info):
        signal_info = signal_info.replace('(', ' ').replace(')','').split(' ')
        if len(signal_info)>1:
            quality = signal_info[2]
            return quality   
    else:
        return None
    
    
timeout(10)
async def load_subsidies_file(session: AsyncSession):
    try:
        y = yadisk.YaDisk(token=OAUTH_TOKEN)
        file_path = '/Программы/Субсидия.xlsx'
        if y.exists(file_path) and y.is_file(file_path):
             
            direct_url = y.get_download_link(file_path)
            response = requests.get(direct_url)
            response.raise_for_status()
            df = pd.read_excel(BytesIO(response.content), sheet_name='показатель 504-п')
            
            df['beeline_level'] = df['Билайн'].apply(lambda x: exctract_signal_level(x))
            df['beeline_quality'] = df['Билайн'].apply(lambda x: exctract_quality_level(x))
            
            df['mts_level'] = df['МТС'].apply(lambda x: exctract_signal_level(x))
            df['mts_quality'] = df['МТС'].apply(lambda x: exctract_quality_level(x))
            
            df['megafon_level'] = df['Мегафон'].apply(lambda x: exctract_signal_level(x))
            df['megafon_quality'] = df['Мегафон'].apply(lambda x: exctract_quality_level(x))
            
            df['tele2_level'] = df['Теле2'].apply(lambda x: exctract_signal_level(x))
            df['tele2_quality'] = df['Теле2'].apply(lambda x: exctract_quality_level(x))
            
            for index, row in df.iterrows():
            
                to_db_query = update(Cities).where(Cities.city_id == int(row['ключ'])).values(
                    city_id= int(row['ключ']),
                    beeline_level= row['beeline_level'],
                    beeline_quality= row['beeline_quality'],
                    mts_level= row['mts_level'],
                    mts_quality= row['mts_quality'],
                    megafon_level= row['megafon_level'],
                    megafon_quality= row['megafon_quality'],
                    tele2_level= row['tele2_level'],
                    tele2_quality= row['tele2_quality'])
                await session.execute(to_db_query)
                await session.commit()
    except Exception as e:
        logging.info(f'Импорт сотовой связи не удался {e}')
        