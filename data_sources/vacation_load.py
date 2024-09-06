from glob import glob
import os
import pandas as pd
import re


async def load_vacation_data():    
    file_path = glob('data_sources/vacation/*рафик*.xlsx')
    file_path.sort(key=os.path.getmtime, reverse=True)
    latest_file_path = file_path[0]

    df = pd.read_excel(latest_file_path, engine ='openpyxl')
    df = df[~df['Сотрудник'].str.contains('увол.', na=False)]
    df['Начало_1'] = pd.to_datetime(df['Начало'], dayfirst=True)
    df['день'] = df['Начало_1'].apply(lambda x: x.day_of_week)
    df['день'] = df['день'].apply(lambda x: 'Понедельник' if x == 0 
                              else 'Вторник' if x == 1
                              else 'Среда' if x == 2
                              else 'Четверг' if x == 3
                              else 'Пятница' if x == 4
                              else 'Суббота' if x == 5
                              else 'Воскресенье' if x == 6 else '')
    date_pattern = re.compile(
        r'с (\d{2}\.\d{2}\.\d{4}) по (\d{2}\.\d{2}\.\d{4})')

    def extract_periods(row):
        description = row['Описание перенесенного отпуска']
        periods = []      
        if pd.notna(description):
            matches = date_pattern.findall(description)
            if matches:
                for start, end in matches:
                    periods.append({
                        'ФИО': row['Сотрудник'],
                        'Дата начала фактического отпуска': start,
                        'Дата конца фактического отпуска': end,
                        'День недели': row['день']
                    })

        if not periods:
            periods.append({
                'ФИО': row['Сотрудник'],
                'Дата начала фактического отпуска': row['Начало'],
                'Дата конца фактического отпуска': row['Окончание'],
                'День недели': row['день']
            })

        return periods

    new_periods = []
    for _, row in df.iterrows():
        new_periods.extend(extract_periods(row))
    periods_df = pd.DataFrame(new_periods)
    
    return periods_df
