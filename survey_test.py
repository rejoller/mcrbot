from pymongo import MongoClient
from bson import ObjectId

async def add_or_update_survey_document(client, user_id, locality_key, survey_data):
    # Установка соединения с базой данных и коллекцией
    db = client['your_database_name']  # Имя вашей базы данных
    collection = db['surveys']  # Имя вашей коллекции
    
    # Создание или обновление документа в MongoDB
    filter = {'user_id': user_id, 'locality_key': locality_key}
    update = {
        '$set': {
            'timestamp': survey_data['timestamp'],
            'first_name': survey_data['first_name'],
            'last_name': survey_data['last_name'],
            'username': survey_data['username'],
            f"{survey_data['operator']}_network": survey_data.get(f"{survey_data['operator']}_network", "Отсутствует"),
            f"{survey_data['operator']}_quality": survey_data.get(f"{survey_data['operator']}_quality", "")
        }
    }
    
    # Опция upsert=True создаст новый документ, если соответствующий фильтру не найден
    result = await collection.update_one(filter, update, upsert=True)
    
    return result.upserted_id or filter  # Возвращаем идентификатор нового документа или фильтр существующего

# Пример использования функции
client = MongoClient('mongodb://localhost:27017/')  # Подключение к MongoDB
user_id = "123456"
locality_key = 789
survey_data = {
    'timestamp': "2023-04-28T12:34:56",
    'user_id': user_id,
    'first_name': "Иван",
    'last_name': "Иванов",
    'username': "ivanov",
    'operator': "tele2",
    'tele2_network': "Хорошо",
    'tele2_quality': "Отлично"
}


await add_or_update_survey_document()
print("Документ обновлен, ID:", document_id)
