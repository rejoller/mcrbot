
from aiogram.filters import Command
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from config import HELP_TEXT

router = Router()

@router.message(Command('help'))
async def handle_help(message: types.Message, state: FSMContext):
    await state.clear()

    
    text = "".join(HELP_TEXT)

    await message.answer(text=text, parse_mode='Markdown')