import pandas as pd
import gsheet_pandas

import logging

from config import SPREADSHEET_ID
from pathlib import Path

from database.models import Cities, Espd, Schools

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


from utils.time_limiter import timeout


secret_path = Path("data_sources").resolve()
gsheet_pandas.setup(credentials_dir=secret_path / "credentials.json")


@timeout(20)
async def szoreg_saver(session: AsyncSession):

    szoreg_df = pd.DataFrame()
    df = pd.from_gsheet(spreadsheet_id=SPREADSHEET_ID, sheet_name="szoreg", range_name="!A2:L2")
    if df.shape[1] == 11:
        szoreg_df = pd.from_gsheet(spreadsheet_id=SPREADSHEET_ID, sheet_name="szoreg", range_name="!A:K")
        szoreg_df["Изменение"] = ""
    else:
        szoreg_df = pd.from_gsheet(spreadsheet_id=SPREADSHEET_ID, sheet_name="szoreg", range_name="!A:L")
        
    szoreg_df["ключ"] = szoreg_df["ключ"].apply(
        lambda x: int(x) if pd.notnull(x) and x != "" else None
    )
    szoreg_df['ID'] = szoreg_df['ID'].apply(
        lambda x: x.replace('_ ', '_') if isinstance(x, str) and '_ ' in x else x
    )
    to_df_query = []
    for index, row in szoreg_df.iterrows():
        row_data = {
            "city_id": int(row["ключ"]) if not pd.isna(row["ключ"]) else None,
            "espd_id": row["ID"] if not pd.isna(row["ID"]) else '',
            "addres": row["Адрес_2"] if not pd.isna(row["Адрес_2"]) else '',
            "technology_type": row["Технология подключения"] if not pd.isna(row["Технология подключения"]) else '',
            "functional_customer": row["Функциональный заказчик"] if not pd.isna(row["Функциональный заказчик"]) else '',
            "name_of_institution": row["Учреждение"],
            "internet_speed": row["Скорость"],
            "contract": row["Контракт"],
            "changes": row["Изменение"] if not row["Изменение"] == '' else "",
        }

        to_df_query = insert(Espd).values(row_data).on_conflict_do_update(
            index_elements=["espd_id"],
            set_=row_data 
        )

        try:
            await session.execute(to_df_query)
            await session.commit()
        except Exception as e:
            logging.info(f'Импорт города {row["Учреждение"]} не удался {e}')

    logging.info("еспд обновлено")




@timeout(20)
async def city_saver(session: AsyncSession):
    cities_df = pd.from_gsheet(
        spreadsheet_id=SPREADSHEET_ID, sheet_name="goroda2.0", range_name="!A:AS"
    )
    cities_df[" Население "] = cities_df[" Население "].apply(
        lambda x: int(x.replace("\xa0", "").replace(" ", "").replace("-", "0"))
    )

    cities_df["перепись 2020"] = cities_df["перепись 2020"].apply(
        lambda x: int(x.replace("\xa0", "").replace(" ", "").replace("-", "0"))
    )
    
    cities_df['место в рейтинге'] = pd.to_numeric(cities_df['место в рейтинге'], downcast='integer').astype('Int64')
    cities_df['количество голосов'] = pd.to_numeric(cities_df['количество голосов'], downcast='integer').astype('Int64')
    cities_df['такое же количество голосов имеют'] = pd.to_numeric(cities_df['такое же количество голосов имеют'], downcast='integer').astype('Int64')
    

    for index, row in cities_df.iterrows():
        row_data = {
            "city_id": int(row["ключ"]),
            "region": row["район"],
            "city_short_name": row["Краткое наименование населенного пункта"],
            "city_full_name": row["Наименование населенного пункта"],
            "population_2010": int(row[" Население "]),
            "population_2020": int(row["перепись 2020"]),
            "arctic_zone": False if row["Арктическая зона"] == "" else True,
            "latitude": float(row["широта"]),
            "longitude": float(row["долгота"]),
            "fias": row["ФИАС"],
            "taksophone_address": str(row["Таксофон"]),
            "subsid_operator": row["оператор по субсидии"],
            "subsid_year": row["Субсидия Таня, год"],
            "selsovet": row["сельсовет"],
            "city_name_from_gosuslugi": row["адрес для кода"],
            "television": row["Телевидение"],
            "radio": row["Радио"],
        }

        to_db_query = insert(Cities).values(row_data).on_conflict_do_update(
            index_elements=["city_id"], 
            set_=row_data  
        )

        try:
            await session.execute(to_db_query)
            await session.commit()
        except Exception as e:
            logging.info(f'Импорт города {row["Краткое наименование населенного пункта"]} не удался {e}')

    logging.info("Города обновлены")




@timeout(20)
async def schools_saver(session: AsyncSession):
    
    schools_df = pd.DataFrame()
    df = pd.from_gsheet(spreadsheet_id=SPREADSHEET_ID, sheet_name="Школы", range_name="!A2:U2")
    if df.shape[1] == 19:
        schools_df = pd.from_gsheet(spreadsheet_id=SPREADSHEET_ID, sheet_name="Школы", range_name="!A:S")
        schools_df['Компонент Услуги связи «Организация канала L2»'] = ""
        schools_df['Комментарии'] = ""
    else:
        schools_df = pd.from_gsheet(spreadsheet_id=SPREADSHEET_ID, sheet_name="Школы", range_name="!A:U")
        
        
    schools_df["Широта"] = schools_df["Широта"].apply(
        lambda x: x.replace(",", ".") if "," in x else None if "#" in x else x
    )
    schools_df["Долгота"] = schools_df["Долгота"].apply(
        lambda x: x.replace(",", ".") if "," in x else None if "#" in x else x
    )
    
    for index, row in schools_df.iterrows():
        row_data = {
            "city_id": int(row["ключ"]) if not pd.isna(row["ключ"]) else None,
            "school_number": row["№ объекта"],
            "school_id": row["ID"],
            "school_adress": row["Адрес учреждения"],
            "latitude": float(row["Широта"]) if not pd.isna(row["Широта"]) else None,
            "longitude": float(row["Долгота"]) if not pd.isna(row["Долгота"]) else None,
            "type_of_institution": row["Тип учреждения"],
            "name_of_school": row["Полное наименование учреждения"],
            "internet_speed": row["Скорость подключения (план), Мбит/с"],
            "technology_type": row["Тип подключения"],
        }

        to_db_query = insert(Schools).values(row_data).on_conflict_do_update(
            index_elements=["school_number"],
            set_=row_data
        )

        try:
            await session.execute(to_db_query)
            await session.commit()
        except Exception as e:
            logging.error(f"Школа {row['Адрес учреждения']} не загружена, ошибка: {e}")

    logging.info("Школы обновлены")
        
        
    
