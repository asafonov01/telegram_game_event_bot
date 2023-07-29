from aiogram import Router
from aiogram.dispatcher.fsm.context import FSMContext
from aiogram.types import Message

from handlers.common import start

default_router = Router()

@default_router.message()
async def default_handler(message: Message, state: FSMContext, user):
    await start(message, state, user)