import gspread
from google.oauth2 import service_account
import gspread_asyncio
import re
from additional import normalize_text_v2, split_message
from fuzzywuzzy import fuzz
import traceback
from aioredis import Redis
import json
redis = None
spreadsheet = None
async def init_redis():
    # Using aioredis.from_url to initialize the Redis client
    try:
        # Правильное формирование URL для подключения
        redis = Redis.from_url('redis://localhost:6379', decode_responses=True, db=0)
        print('Успешно подключено к Redis')
        return redis
    except Exception as e:
        print(f"Ошибка при подключении к Redis: {e}")
        return None

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SERVICE_ACCOUNT_FILE = 'credentials.json'
creds = None
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
SPREADSHEET_ID = '1ghoLFQ6Ydbz0QRMgCfAT2_0fktJSNI4HkHIu6qKWWbU'

async def get_authorized_client_and_spreadsheet():
    agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: creds)
    gc = await agcm.authorize()
    spreadsheet = await gc.open_by_key(SPREADSHEET_ID)
    return gc, spreadsheet


async def get_value(row, index, default_value=''):
    try:
        return row[index]
    except IndexError:
        return default_value


async def load_szoreg_values(spreadsheet, redis):
    try:
        print('Loading SZOREG values into Redis...')
        range_name = 'szoreg!A1:Q9000'
        agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: creds)
        gc = await agcm.authorize()
        spreadsheet = await gc.open_by_key(SPREADSHEET_ID)

        result = await spreadsheet.values_batch_get(range_name)
        rows = result.get('valueRanges', [])[0].get('values', [])
        max_columns = 16  # предположим, что максимальное количество колонок в данных 16


        pipeline = redis.pipeline()
        for row in rows:
            if len(row) > 0:
                unique_key = str(row[0]).lower()  # предполагаем, что row[0] - это неуникальный ключ
                full_row = row + [None] * (max_columns - len(row))
                pipeline.rpush(f"szoreg:{unique_key}", json.dumps(full_row))

        await pipeline.execute()
        print('All SZOREG values loaded successfully.')

        # Извлечение и вывод первых 10 записей из каждого списка
        keys = await redis.keys('szoreg:*')
        for key in keys[:10]:  # берем только первые 10 ключей
            list_length = await redis.llen(key)  # Получаем длину списка
            list_items = await redis.lrange(key, 0, list_length - 1)  # Получаем все элементы списка


    except Exception as e:
        print("An error occurred during loading SZOREG values:", e)

async def search_szoreg_values(query, redis):
    try:
        query_lower = query.lower()
        print(f'Поиск данных SZOREG в Redis по ключу: szoreg:{query_lower}...')

        # Используем lrange для извлечения всех элементов списка, хранящихся под ключом 'szoreg:{query_lower}'
        data_json_list = await redis.lrange(f"szoreg:{query_lower}", 0, -1)
        if data_json_list:
            # Преобразуем все JSON строки в объекты Python в одном выражении list comprehension
            found_values = [json.loads(data_json) for data_json in data_json_list]
            
            return found_values
        else:
            print(f'Данные по запросу "{query_lower}" не найдены.')
            return None
    except Exception as e:
        print(f"Произошла ошибка при поиске значений SZOREG в Redis:", e)
        return None





async def load_yandex_2023_values(spreadsheet, redis):
    try:
        print('Loading Yandex 2023 data into Redis...')
        range_name = '2023!A3:P50'
        agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: creds)
        gc = await agcm.authorize()
        spreadsheet = await gc.open_by_key(SPREADSHEET_ID)
        result = await spreadsheet.values_batch_get(range_name)
        rows = result.get('valueRanges', [])[0].get('values', [])
        max_columns = 16  # Assuming the range has columns from A to P
        pipeline = redis.pipeline()
        for row in rows:
            if len(row) > 0:
                unique_key = str(row[0]).lower()
                full_row = [item if item is not None else None for item in row] + [None] * (max_columns - len(row))
                pipeline.rpush(f"yandex2023:{unique_key}", json.dumps(full_row))
        await pipeline.execute()
        print('All Yandex 2023 values loaded successfully.')
    except Exception as e:
        print("An error occurred during loading Yandex 2023 values:", e)



async def search_yandex_2023_values(query, redis):
    try:
        query_lower = query.lower()
        print(f'Поиск данных о Yandex 2023 в Redis по ключу: yandex2023:{query_lower}...')
        data_json_list = await redis.lrange(f"yandex2023:{query_lower}", 0, -1)
        if data_json_list:
            found_values = [json.loads(data_json) for data_json in data_json_list if data_json is not None]
            return found_values
        else:
            print(f'Данные по запросу "{query_lower}" не найдены.')
            return None
    except Exception as e:
        print(f"Произошла ошибка при поиске данных о Yandex 2023 в Redis:", e)
        return None



async def load_pokazatel_504p_values(spreadsheet, redis):
    try:
        print('Loading 504-п values into Redis...')
        range_name = 'показатель 504-п!A1:K1719'
        agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: creds)
        gc = await agcm.authorize()
        spreadsheet = await gc.open_by_key(SPREADSHEET_ID)
        result = await spreadsheet.values_batch_get(range_name)
        rows = result.get('valueRanges', [])[0].get('values', [])
        max_columns = 11
        pipeline = redis.pipeline()
        for row in rows:
            if len(row) > 0:
                unique_key = str(row[0]).lower()
                full_row = row + [None] * (max_columns - len(row))
                pipeline.rpush(f"pokazatel_504p:{unique_key}", json.dumps(full_row))

        await pipeline.execute()
        print('All 504-п values loaded successfully.')
    except Exception as e:
        print("An error occurred during loading 504-п values:", e)


async def search_in_pokazatel_504p(query, redis):
    try:
        query_lower = query.lower()
        print(f'Поиск данных 504-п в Redis по ключу: pokazatel_504p:{query_lower}...')

        data_json_list = await redis.lrange(f"pokazatel_504p:{query_lower}", 0, -1)
        if data_json_list:

            return [json.loads(data_json) for data_json in data_json_list]
        else:
            print(f'Данные по запросу "{query_lower}" не найдены.')
            return None
    except Exception as e:
        print(f"Произошла ошибка при поиске значений 504-п в Redis:", e)
        return None


async def load_ucn2_values(spreadsheet, redis):
    try:
        print('Loading UCN 2.0 (2023) data into Redis...')
        range_name = 'УЦН 2.0 (2023)!A1:K800'
        agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: creds)
        gc = await agcm.authorize()
        spreadsheet = await gc.open_by_key(SPREADSHEET_ID)

        result = await spreadsheet.values_batch_get(range_name)
        rows = result.get('valueRanges', [])[0].get('values', [])
        max_columns = 11  # Assuming the range has columns from A to K
        pipeline = redis.pipeline()
        for row in rows:
            if len(row) > 0:
                unique_key = str(row[0]).lower()
                full_row = [item if item is not None else None for item in row] + [None] * (max_columns - len(row))
                pipeline.rpush(f"ucn2:{unique_key}", json.dumps(full_row))

        await pipeline.execute()
        print('All UCN 2.0 (2023) values loaded successfully.')
    except Exception as e:
        print("An error occurred during loading UCN 2.0 (2023) values:", e)

async def search_in_ucn2(query, redis):
    try:
        query_lower = query.lower()
        print(f'Поиск данных о UCN 2.0 (2023) в Redis по ключу: ucn2:{query_lower}...')

        data_json_list = await redis.lrange(f"ucn2:{query_lower}", 0, -1)
        if data_json_list:
            found_values = [json.loads(data_json) for data_json in data_json_list if data_json is not None]

            return found_values
        else:
            print(f'Данные по запросу "{query_lower}" не найдены.')
            return None
    except Exception as e:
        print(f"Произошла ошибка при поиске данных о UCN 2.0 (2023) в Redis:", e)
        return None


async def load_schools_values(spreadsheet, redis):
    try:
        print('Loading school data into Redis...')
        range_name = 'Школы!A1:U2000'
        agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: creds)
        gc = await agcm.authorize()
        spreadsheet = await gc.open_by_key(SPREADSHEET_ID)
        result = await spreadsheet.values_batch_get(range_name)
        rows = result.get('valueRanges', [])[0].get('values', [])
        max_columns = 21
        pipeline = redis.pipeline()
        for row in rows:
            if len(row) > 0:
                unique_key = str(row[0]).lower()
                full_row = [item if item is not None else None for item in row] + [None] * (max_columns - len(row))
                pipeline.rpush(f"schools:{unique_key}", json.dumps(full_row))
        await pipeline.execute()
        print('All school values loaded successfully.')
    except Exception as e:
        print("An error occurred during loading school values:", e)

async def search_schools_values(query, redis):
    try:
        query_lower = query.lower()
        print(f'Поиск данных о школах в Redis по ключу: schools:{query_lower}...')

        data_json_list = await redis.lrange(f"schools:{query_lower}", 0, -1)
        if data_json_list:
            found_values = [json.loads(data_json) for data_json in data_json_list if data_json is not None]

            return found_values
        else:
            print(f'Данные по запросу "{query_lower}" не найдены.')
            return None
    except Exception as e:
        print(f"Произошла ошибка при поиске данных о школах в Redis:", e)
        return None




async def load_votes_values(spreadsheet, redis):
    try:
        print('Loading votes data into Redis...')
        range_name = 'votes!A1:D2000'
        agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: creds)
        gc = await agcm.authorize()
        spreadsheet = await gc.open_by_key(SPREADSHEET_ID)

        result = await spreadsheet.values_batch_get(range_name)
        rows = result.get('valueRanges', [])[0].get('values', [])
        max_columns = 4

        pipeline = redis.pipeline()
        for row in rows:
            if len(row) > 0:
                unique_key = str(row[0]).lower()  # Предположим, что первое поле - это уникальный ключ (например, ID голосования)
                full_row = [item if item is not None else None for item in row] + [None] * (max_columns - len(row))
                pipeline.rpush(f"votes:{unique_key}", json.dumps(full_row))  # Добавление в список Redis

        await pipeline.execute()
        print('All votes values loaded successfully.')
    except Exception as e:
        print(f"An error occurred during loading votes values: {e}")



async def search_votes_values(query, redis):
    try:
        query_lower = query.lower()
        print(f'Searching for votes data in Redis with key: votes:{query_lower}...')

        data_json_list = await redis.lrange(f"votes:{query_lower}", 0, -1)
        if data_json_list:
            found_values = [json.loads(data_json) for data_json in data_json_list if data_json is not None]

            return found_values
        else:
            print(f'No data found for the query "{query_lower}".')
            return None
    except Exception as e:
        print(f"An error occurred during search for votes data: {e}")
        return None



async def load_survey_values(spreadsheet, redis):
    try:
        print('Loading survey data into Redis...')
        range_name = 'Результаты опроса!A1:O'
        agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: creds)
        gc = await agcm.authorize()
        spreadsheet = await gc.open_by_key(SPREADSHEET_ID)

        result = await spreadsheet.values_batch_get(range_name)
        rows = result.get('valueRanges', [])[0].get('values', [])
        max_columns = 16

        pipeline = redis.pipeline()
        for row in rows:
            if len(row) > 0:
                unique_key = str(row[0]).lower()  # Предположим, что первое поле - это уникальный ключ (например, ID голосования)
                full_row = [item if item is not None else None for item in row] + [None] * (max_columns - len(row))
                pipeline.rpush(f"surv_results:{unique_key}", json.dumps(full_row))  # Добавление в список Redis

        await pipeline.execute()
        print('All votes values loaded successfully.')
    except Exception as e:
        print(f"An error occurred during loading votes values: {e}")


async def search_survey_results(query, redis):
    try:
        query_lower = query.lower()
        print(f'Searching for surv_results data in Redis with key: surv_results:{query_lower}...')

        data_json_list = await redis.lrange(f"surv_results:{query_lower}", 0, -1)
        if data_json_list:
            found_values = [json.loads(data_json) for data_json in data_json_list if data_json is not None]

            return found_values
        else:
            print(f'No data found for the query "{query_lower}".')
            return None
    except Exception as e:
        print(f"An error occurred during search for surv_results data: {e}")
        return None




async def load_otpusk_data():
    agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: creds)
    gc = await agcm.authorize()
    spreadsheet = await gc.open_by_key(SPREADSHEET_ID)
    sheet = await spreadsheet.worksheet('otpusk')
    rows = await sheet.get('A1:F100')
    return rows
    
    
    
    
async def load_values(spreadsheet, redis):
    try:
        print('Loading values into Redis...')
        range_name = 'goroda2.0!A1:AQ1721'
        agcm = gspread_asyncio.AsyncioGspreadClientManager(lambda: creds)
        gc = await agcm.authorize()
        spreadsheet = await gc.open_by_key(SPREADSHEET_ID)

        result = await spreadsheet.values_batch_get(range_name)
        rows = result.get('valueRanges', [])[0].get('values', [])

        await redis.flushdb()
        pipeline = redis.pipeline()
        for index, row in enumerate(rows):
            if len(row) > 3:
                town_name = normalize_text_v2(str(row[0]).lower())
                unique_key = str(row[4]).lower()
                pipeline.sadd(f"town:{town_name}", unique_key)
                pipeline.set(f"data:{unique_key}", json.dumps(row))
                

        await pipeline.execute()
        print('All values loaded successfully.')
    except Exception as e:
        print('Error loading values into Redis:', str(e))
        traceback.print_exc()


async def search_values(query, redis):
    normalized_query = normalize_text_v2(query.lower())
    print(f'Searching for: {normalized_query}')

    unique_keys = await redis.smembers(f"town:{normalized_query}")
    print(f'Unique keys retrieved: {unique_keys}')

    if unique_keys:
        keys_to_fetch = [f"data:{key}" for key in unique_keys]
        data_json_list = await redis.mget(keys_to_fetch)

        found_values_a = sorted([json.loads(data_json) for data_json in data_json_list if data_json])
        print(f'Data found for keys: {keys_to_fetch}')

        return found_values_a
    else:
        print("No unique keys found for the query.")
        return None
        




async def search_values_levenshtein(query, spreadsheet, threshold=0.7, max_results=5):
    try:
        # Открываем конкретный диапазон
        range_name = 'goroda2.0!A1:AM1721'
        result = await spreadsheet.values_batch_get(range_name)
        rows = result.get('valueRanges', [])[0].get('values', [])
        normalized_query = normalize_text_v2(query)

        # Создаем список для хранения всех совпадений
        all_matches = []

        for row in rows:
            try:
                if len(row) > 0:
                    similarity = fuzz.token_sort_ratio(normalized_query, normalize_text_v2(row[0]))
                    if similarity >= (threshold * 100):
                        all_matches.append((row, similarity))
            except IndexError:
                pass

        # Сортируем все совпадения по показателю сходства в обратном порядке (от большего к меньшему)
        sorted_matches = sorted(all_matches, key=lambda x: x[1], reverse=True)

        # Берем до max_results наиболее релевантных результатов
        top_matches = sorted_matches[:max_results]

        # Получаем только значения из первых позиций в каждом совпадении
        found_values_a = [match[0][0] for match in top_matches]

        return found_values_a
    except Exception as e:
        print("An error occurred during search_values_levenshtein:", e)
        return []
