import os
from zoneinfo import ZoneInfo
from aiogram.filters import Command
from aiogram import Router, types, F
import pandas as pd



from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import Ucn2025

from datetime import datetime as dt
from icecream import ic

router = Router()

@router.message(F.text.contains('уцн'))
@router.message(Command('ucn'))
async def handle_help(message: types.Message, session: AsyncSession):
    ucn2025_subquery = select(Ucn2025.city_id, Ucn2025.city_name_from_gosuslugi, Ucn2025.number_of_votes_ucn2025,
                           func.dense_rank().over(order_by=Ucn2025.number_of_votes_ucn2025.desc()).label('rank'), Ucn2025.date_of_update_ucn2025)

    ucn2025_result = await session.execute(ucn2025_subquery)
    response_ucn2025 = ucn2025_result.all()
    ucn2025df = pd.DataFrame(response_ucn2025)
    ucn2025df.index +=1
    ucn2025df['date_of_update_ucn2025'] = pd.to_datetime(
        ucn2025df['date_of_update_ucn2025'], dayfirst=True, format='%d.%m.%Y %H:%M', utc=True
    )

    ucn2025df['date_of_update_ucn2025'] = (
        ucn2025df['date_of_update_ucn2025'].dt.strftime('%d.%m.%Y %H:%M')
    )

    ucn2025df = ucn2025df.rename(columns={'city_name_from_gosuslugi':'Наименование населенного пункта','city_id': 'ID',
                              'number_of_votes_ucn2025':'количество голосов', 'date_of_update_ucn2025': 'дата актуальности', 'rank': 'Место в рейтинге'})
    directory = 'data_sources/ucn'
    filename = 'УЦН.xlsx'
    
    if not os.path.exists(directory):
            os.mkdir(directory)
    
    destination = os.path.join(directory, filename)    
    writer = pd.ExcelWriter(destination, engine='xlsxwriter')
    ucn2025df.to_excel(writer, index=False, sheet_name='УЦН 2.0')


    workbook = writer.book
    worksheet = writer.sheets['УЦН 2.0']
    for i, col in enumerate(ucn2025df.columns):
        width = max(ucn2025df[col].apply(lambda x: len(str(x))).max(), len(col))
        worksheet.set_column(i, i, width)
    writer.close()

    count_of_votes = len(ucn2025df)
    sum_of_votes = ucn2025df['количество голосов'].sum()
    vote_time = ucn2025df['дата актуальности'].max()
    
    caption=(f'<b>Голосование УЦН 2.0</b>\n<i>{vote_time}</i>\n\nНаселенных пунктов: {count_of_votes}\n'
            f'Всего голосов в регионе: {sum_of_votes}\n')
    
    
    await message.answer_document(caption=caption, document=types.FSInputFile(destination), parse_mode='HTML')