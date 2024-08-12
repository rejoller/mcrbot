from aiogram import F, Router
from data_sources.vacation_load import load_vacation_data
from datetime import datetime as dt, timedelta
from aiogram.filters import Command
from aiogram.types import Message

from users.user_manager import MessagesManager, UserManager
from utils.message_splitter import split_message



router = Router()


def get_employees_on_vacation(otpusk_data, days_ahead=None):
    today = dt.today().date()
    future_vacation_start = today + timedelta(days=days_ahead)
    employees_on_vacation = []
    employees_starting_vacation_soon = []
    for index, row in otpusk_data.iterrows():
        start_date = dt.strptime(
            row['Дата начала фактического отпуска'], "%d.%m.%Y").date()
        
        end_date = dt.strptime(
            row['Дата конца фактического отпуска'], "%d.%m.%Y").date()

        if start_date <= today <= end_date:
            employees_on_vacation.append(row)

        if today < start_date <= future_vacation_start:
            employees_starting_vacation_soon.append(row)

    
    return employees_on_vacation, employees_starting_vacation_soon


@router.message(F.text.contains('тпуск'))
@router.message(Command('otpusk'))
async def handle_otpusk_command(message: Message, session=None):
   
    days_ahead=14
    
    user_manager = UserManager(session)
    msg_manager = MessagesManager(session)
    user_data = user_manager.extract_user_data_from_message(message)
    msg_data = msg_manager.extract_data_from_message(message)

    await user_manager.add_user_if_not_exists(user_data)

    otpusk_data = await load_vacation_data()
    employees_on_vacation, employees_starting_vacation_soon = get_employees_on_vacation(
        otpusk_data, days_ahead)

    response = ""

    if employees_on_vacation:
        response += f'<i>Сегодня в отпуске</i>🏝\n\n'
        for row in employees_on_vacation:
            response += f"<blockquote><b>{row.iloc[0]}</b>\n"
            response += f"начало: {row.iloc[1]} ({row.iloc[3]})\n"
            response += f"окончание: {row.iloc[2]} ({row.iloc[3]})</blockquote>\n\n"

    if employees_starting_vacation_soon:
        response += f"\n<i>Сотрудники, уходящие в отпуск в ближайшие <b>{days_ahead}</b> дней</i>\n\n"
        for emp_row in employees_starting_vacation_soon:
            response += f"<blockquote><b>{emp_row.iloc[0]}</b>\n"
            response += f"начало: {emp_row.iloc[1]} ({emp_row.iloc[3]})\n"
            response += f"окончание: {emp_row.iloc[2]} ({emp_row.iloc[3]})</blockquote>\n\n"

    if not response:
        response = f"Сегодня никто не в отпуске, и никто не уходит в отпуск в ближайшие {days_ahead} дней."

    
    messages = await split_message(response)

    for msg in messages:

        await message.answer(msg, parse_mode='HTML')
        await msg_manager.add_message_if_not_exists(msg_data, msg)
