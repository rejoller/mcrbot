from aiogram import F, Router, types, Bot
import os
from media_files.animations import vacation_file

router = Router()


@router.message(F.document)
async def contacts_handler(message: types.Message, bot: Bot):
    user_name = message.from_user.first_name
    document = message.document
    file_name = document.file_name.lower()
    if "рафик" in file_name:
        directory = 'data_sources/vacation'
        if not os.path.exists(directory):
            os.mkdir(directory)
        destination = os.path.join(os.getcwd(), directory, file_name)
        file_info = await bot.get_file(document.file_id)
        await bot.download_file(file_info.file_path, destination)
        await message.answer_animation(caption=f'Файл с отпусками загружен.\nХорошего дня тебе, {user_name}😊',
                                   animation=vacation_file)
