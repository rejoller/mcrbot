import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient('mongodb://localhost:27017')
db = client.survey_results
surveys_collection = db.network





'''
async def show_collection_data(np=None):
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    
    db = client.survey_results
    surveys_collection = db.network

    # Асинхронно получаем все документы из коллекции
    document  = await surveys_collection.find_one({'_id':np})
    return document




async def show_collection_data(np):
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.survey_results
    surveys_collection = db.network
    document = await surveys_collection.find_one({'_id': np})

    if document:
        # Обрабатываем данные перед отправкой в колбек
        simplified_data = {
            'tele2_level': document.get('results', {}).get('964635576', {}).get('tele2_level', ''),
            'mts_level': document.get('results', {}).get('964635576', {}).get('mts_level', '')
            # Добавьте другие поля по аналогии
        }
        return simplified_data
    return None
'''


async def show_collection_data(np):
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.survey_results
    surveys_collection = db.network
    document = await surveys_collection.find_one({'_id': np})

    if document and 'results' in document:
        all_data = []
        for user_id, user_data in document['results'].items():
            user_info = {
                '_id': str(document['_id']),
                'user_id': user_id,
                'tele2_level': user_data.get('tele2_level', ''),
                'tele2_quality': user_data.get('tele2_quality', ''),
                'mts_level': user_data.get('mts_level', ''),
                'megafon_level': user_data.get('megafon_level', ''),
                'megafon_quality': user_data.get('megafon_quality', ''),
                'beeline_level': user_data.get('beeline_level', ''),
                'beeline_quality': user_data.get('beeline_quality', ''),
                'location': user_data.get('location', {})
            }
            all_data.append(user_info)
        return all_data
    return None



async def save_survey_results(np, user_id, survey_data):
    update_query = {f"$set": {f"results.{user_id}.{key}": value for key, value in survey_data.items()}}
    await surveys_collection.update_one({"_id": np}, update_query, upsert=True)

async def save_user_location(user_id, location_data):
    await surveys_collection.update_many(
        {f"results.{user_id}": {"$exists": True}},
        {"$set": {f"results.{user_id}.location": location_data}}
    )

