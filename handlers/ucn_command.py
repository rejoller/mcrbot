import os
from aiogram.filters import Command
from aiogram import Router, types, F
import pandas as pd
from pandas import option_context

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import Ucn2025
from icecream import ic

router = Router()

@router.message(F.text.contains('уцн'))
@router.message(Command('ucn'))
async def handle_help(message: types.Message, session: AsyncSession):
    ucn2025_subquery = select(Ucn2025.city_id, Ucn2025.city_name_from_gosuslugi, Ucn2025.number_of_votes_ucn2025,
                           func.rank().over(order_by=Ucn2025.number_of_votes_ucn2025.desc()).label('rank'), Ucn2025.date_of_update_ucn2025)

    ucn2025_result = await session.execute(ucn2025_subquery)
    response_ucn2025 = ucn2025_result.all()
    ucn2025df = pd.DataFrame(response_ucn2025)
    ucn2025df.index +=1
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

    
    await message.answer_document(caption='Голосование УЦН 2.0', document=types.FSInputFile(destination))