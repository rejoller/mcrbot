import time
import pandas as pd
import gsheet_pandas

import logging
from icecream import ic

from config import SPREADSHEET_ID
from pathlib import Path

from database.models import Cities, Espd, Schools

from sqlalchemy import update, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


from utils.time_limiter import timeout


secret_path = Path("data_sources").resolve()
gsheet_pandas.setup(credentials_dir=secret_path / "credentials.json")


@timeout(20)
async def szoreg_saver(session: AsyncSession):
    try:
        start_time = time.time()
        szoreg_df = pd.from_gsheet(
            spreadsheet_id=SPREADSHEET_ID, sheet_name="szoreg", range_name="!A:L"
        )
        szoreg_df.fillna({"Изменение": ""})
        szoreg_df["ключ"] = szoreg_df["ключ"].apply(
            lambda x: int(x) if pd.notnull(x) and x != "" else None
        )
        to_df_query = []
        for index, row in szoreg_df.iterrows():
            to_df_query = (
                update(Espd)
                .where(Espd.espd_id == row["ID"])
                .values(
                    city_id=int(row["ключ"]) if not pd.isna(row["ключ"]) else None,
                    espd_id=row["ID"],
                    addres=row["Адрес_2"],
                    technology_type=row["Технология подключения"],
                    functional_customer=row["Функциональный заказчик"],
                    name_of_institution=row["Учреждение"],
                    internet_speed=row["Скорость"],
                    contract=row["Контракт"],
                    changes=row["Изменение"] if not pd.isna(row["Изменение"]) else "",
                )
            )

            await session.execute(to_df_query)
            await session.commit()
        print(f"еспд обновлено за {time.time() - start_time} секунд")
        empty_check_query = select(Espd).limit(1)
        empty_check_query_result = await session.execute(empty_check_query)
        result = empty_check_query_result.all()
        if result == []:
            for index, row in szoreg_df.iterrows():
                to_df_query = (
                    insert(Espd).values(
                        city_id=int(row["ключ"]) if not pd.isna(row["ключ"]) else None,
                        espd_id=row["ID"],
                        addres=row["Адрес_2"],
                        technology_type=row["Технология подключения"],
                        functional_customer=row["Функциональный заказчик"],
                        name_of_institution=row["Учреждение"],
                        internet_speed=row["Скорость"],
                        contract=row["Контракт"],
                        changes=row["Изменение"] if not pd.isna(row["Изменение"]) else "",
                    )
                ).on_conflict_do_nothing()

                await session.execute(to_df_query)
                await session.commit()
            print(f"еспд загружено за {time.time() - start_time} секунд")

    except Exception as e:
        logging.error(f"Данные ЕСПД не загружены {e}")


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

    cities_df["количество голосов"] = cities_df["количество голосов"].apply(
        lambda x: int(x) if pd.notnull(x) and x != "" else None
    )

    cities_df["место в рейтинге"] = cities_df["место в рейтинге"].apply(
        lambda x: int(x) if pd.notnull(x) and x != "" else None
    )

    cities_df["такое же количество голосов имеют"] = cities_df[
        "такое же количество голосов имеют"
    ].apply(lambda x: int(x) if pd.notnull(x) and x != "" else None)

    cities_df.fillna("")
    for index, row in cities_df.iterrows():   
        to_db_query = (update(Cities).where(Cities.city_id == int(row['ключ'])).values(
            city_id = int(row["ключ"]),
            region = row["район"],
            city_short_name = row["Краткое наименование населенного пункта"],
            city_full_name = row["Наименование населенного пункта"],
            population_2010 = int(row[" Население "]),
            population_2020 = int(row["перепись 2020"]),
            arctic_zone = False if row["Арктическая зона"] == "" else True,
            latitude = float(row["широта"]),
            longitude = float(row["долгота"]),
            fias = row["ФИАС"] if not pd.isna(row["ФИАС"]) else '',
            taksophone_address = str(row["Таксофон"]) if not pd.isna(row["Таксофон"]) else '',
            subsid_operator = row["оператор по субсидии"] if not pd.isna(row["оператор по субсидии"]) else '',
            subsid_year = row["Субсидия Таня, год"] if not pd.isna(row["Субсидия Таня, год"]) else '',
            selsovet = row["сельсовет"] if not pd.isna(row["сельсовет"]) else '',
            city_name_from_gosuslugi = row["адрес для кода"] if not pd.isna(row["адрес для кода"]) else '',
            number_of_votes_ucn2023 = row["количество голосов"] if not pd.isna(row["количество голосов"]) else '',
            date_of_update_ucn2023 = row["время записи"] if not pd.isna(row["время записи"]) else '',
            rank_ucn2023 = row["место в рейтинге"] if not pd.isna(row["место в рейтинге"]) else '',
            same_number_of_votes_ucn2023 = row["такое же количество голосов имеют"] if not pd.isna(row["такое же количество голосов имеют"]) else '',
            television = row["Телевидение"] if not pd.isna(row["Телевидение"]) else '',
            radio = row["Радио"]) if not pd.isna(row["Радио"]) else '')
        await session.execute(to_db_query)
        await session.commit()
    
    empty_check_query = select(Cities).limit(1)
    empty_check_query_result = await session.execute(empty_check_query)
    result = empty_check_query_result.all()
    
    if result == []:
        for index, row in cities_df.iterrows():
            to_db_query = (insert(Cities).values(
                city_id = int(row["ключ"]),
                region = row["район"],
                city_short_name = row["Краткое наименование населенного пункта"],
                city_full_name = row["Наименование населенного пункта"],
                population_2010 = int(row[" Население "]),
                population_2020 = int(row["перепись 2020"]),
                arctic_zone = False if row["Арктическая зона"] == "" else True,
                latitude = float(row["широта"]),
                longitude = float(row["долгота"]),
                fias = row["ФИАС"] if not pd.isna(row["ФИАС"]) else '',
                taksophone_address = str(row["Таксофон"]) if not pd.isna(row["Таксофон"]) else '',
                subsid_operator = row["оператор по субсидии"] if not pd.isna(row["оператор по субсидии"]) else '',
                subsid_year = row["Субсидия Таня, год"] if not pd.isna(row["Субсидия Таня, год"]) else '',
                selsovet = row["сельсовет"] if not pd.isna(row["сельсовет"]) else '',
                city_name_from_gosuslugi = row["адрес для кода"] if not pd.isna(row["адрес для кода"]) else '',
                number_of_votes_ucn2023 = row["количество голосов"] if not pd.isna(row["количество голосов"]) else '',
                date_of_update_ucn2023 = row["время записи"] if not pd.isna(row["время записи"]) else '',
                rank_ucn2023 = row["место в рейтинге"] if not pd.isna(row["место в рейтинге"]) else '',
                same_number_of_votes_ucn2023 = row["такое же количество голосов имеют"] if not pd.isna(row["такое же количество голосов имеют"]) else '',
                television = row["Телевидение"] if not pd.isna(row["Телевидение"]) else '',
                radio = row["Радио"]) if not pd.isna(row["Радио"]) else '').on_conflict_do_nothing()
            await session.execute(to_db_query)
            await session.commit()
        


@timeout(20)
async def schools_saver(session: AsyncSession):
    schools_df = pd.from_gsheet(
        spreadsheet_id=SPREADSHEET_ID, sheet_name="Школы", range_name="!A:V"
    )
    schools_df.fillna("")
    schools_df["Широта"] = schools_df["Широта"].apply(
        lambda x: x.replace(",", ".") if "," in x else None if "#" in x else x
    )
    schools_df["Долгота"] = schools_df["Долгота"].apply(
        lambda x: x.replace(",", ".") if "," in x else None if "#" in x else x
    )
    for index, row in schools_df.iterrows():
        
        to_db_query = update(Schools).where(Schools.school_id == int(row['ID'])).values(
            
                city_id = int(row["ключ"]) if not pd.isna(row["ключ"]) else '',
                school_number = row["№ объекта"]  if not pd.isna(row["№ объекта"]) else '',
                school_id = int(row["ID"]) if not pd.isna(row["ID"]) else '',
                school_adress = row["Адрес учреждения"] if not pd.isna(row["Адрес учреждения"]) else '',
                latitude = float(row["Широта"]) if not pd.isna(row["Широта"]) else '',
                longitude = float(row["Долгота"]) if not pd.isna(row["Долгота"]) else '',
                type_of_institution = row["Тип учреждения"] if not pd.isna(row["Тип учреждения"]) else '',
                name_of_school = row["Полное наименование учреждения"] if not pd.isna(row["Полное наименование учреждения"]) else '',
                internet_speed = row["Скорость подключения (план), Мбит/с"] if not pd.isna(row["Скорость подключения (план), Мбит/с"]) else '',
                technology_type = row["Тип подключения"] if not pd.isna(row["Долгота"]) else '',
        )
        await session.execute(to_db_query)
        await session.commit()
        
    empty_check_query = select(Schools).limit(1)
    empty_check_query_result = await session.execute(empty_check_query)
    result = empty_check_query_result.all()
    if result == []:
        for index, row in schools_df.iterrows():
            to_db_query = insert(Schools).values(
                city_id = int(row["ключ"]) if not pd.isna(row["ключ"]) else '',
                school_number = row["№ объекта"]  if not pd.isna(row["№ объекта"]) else '',
                school_id = int(row["ID"]) if not pd.isna(row["ID"]) else '',
                school_adress = row["Адрес учреждения"] if not pd.isna(row["Адрес учреждения"]) else '',
                latitude = float(row["Широта"]) if not pd.isna(row["Широта"]) else '',
                longitude = float(row["Долгота"]) if not pd.isna(row["Долгота"]) else '',
                type_of_institution = row["Тип учреждения"] if not pd.isna(row["Тип учреждения"]) else '',
                name_of_school = row["Полное наименование учреждения"] if not pd.isna(row["Полное наименование учреждения"]) else '',
                internet_speed = row["Скорость подключения (план), Мбит/с"] if not pd.isna(row["Скорость подключения (план), Мбит/с"]) else '',
                technology_type = row["Тип подключения"] if not pd.isna(row["Долгота"]) else '',
                
        ).on_conflict_do_nothing()
            await session.execute(to_db_query)
            await session.commit()
        
    
