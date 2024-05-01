from motor.motor_asyncio import AsyncIOMotorClient

async def save_survey_results(np, user_id, survey_data):
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.survey_results
    surveys_collection = db.network
    update_query = {f"$set": {f"results.{user_id}.{key}": value for key, value in survey_data.items()}}
    await surveys_collection.update_one({"_id": np}, update_query, upsert=True)

async def save_user_location(user_id, location_data):
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.survey_results
    surveys_collection = db.network

    # Обновляем данные для всех документов, где есть этот user_id
    await surveys_collection.update_many(
        {f"results.{user_id}": {"$exists": True}},  # Фильтр для выборки документов с этим user_id
        {"$set": {f"results.{user_id}.location": location_data}}  # Обновление данных локации
    )
