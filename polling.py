import asyncio

from aiogram import Dispatcher
from aiogram.dispatcher.fsm.storage.mongo import MongoStorage
from motor.motor_asyncio import AsyncIOMotorClient

from bot import bot
from handlers.common import common_router
from handlers.default_hander import default_router
from handlers.home import home_router
from handlers.puzzles import puzzles_router
from handlers.thanksgiving import thanksgiving_router
from handlers.trader import trader_router
from handlers.team_up import team_router
from middlewares import UserMiddleware
from settings import MONGO_DOMAIN, MONGO_PORT, MONGO_USERNAME, MONGO_PASSWORD, \
    i18n_middleware


async def main():
    storage = MongoStorage(AsyncIOMotorClient(MONGO_DOMAIN, MONGO_PORT, username=MONGO_USERNAME, password=MONGO_PASSWORD),
                           db_name='cc_puzzle_bot', with_destiny=False, with_bot_id=False)

    dp = Dispatcher(storage=storage)
    # dp.message.setup(LoggingMiddleware())
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    dp.message.outer_middleware(i18n_middleware)
    dp.callback_query.outer_middleware(i18n_middleware)

    dp.include_router(common_router)
    dp.include_router(puzzles_router)
    #dp.include_router(home_router)
    dp.include_router(trader_router)
    dp.include_router(thanksgiving_router)
    dp.include_router(team_router)
    dp.include_router(default_router)

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())