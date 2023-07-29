from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware, types
from aiogram.types import Message
from pymongo import ReturnDocument

from settings import db


class UserMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        super().__init__()

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:

            chat: types.Chat = types.Chat.get_current()

            user = await db.users.find_one_and_update(
                {"chat_id": chat.id},
                {"$setOnInsert": {
                    'ranks': {},
                    'coins': 0,
                }},
                upsert=True,
                return_document=ReturnDocument.AFTER)

            data['user'] = user

            return await handler(event, data)


