import csv
from aiogram import BaseMiddleware
from aiogram.types import Message
import logging
from datetime import datetime as dt



def log_user_data(user_id, first_name, last_name, username, message_text):
    file_path = 'users_data.csv'
    current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(file_path, 'x', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'User ID', 'First Name',
                             'Last Name', 'Username', 'Message'])
    except FileExistsError:
        pass

    with open(file_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([current_time, user_id, first_name,
                         last_name, username, message_text])


async def log_user_data_from_message(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username
    message_text = message.text

    log_user_data(user_id, first_name, last_name, username, message_text)



class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        logging.info(f"Received message from {event.from_user.id}: {event.text}")
        await log_user_data_from_message(event)
        return await handler(event, data)