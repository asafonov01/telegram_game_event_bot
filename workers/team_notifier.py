import asyncio

from bot import bot
from settings import db, TEAM_NOTIFIED


async def main():
    while True:
        code = await TEAM_NOTIFIED.find_one({'is_notified': {'$exists': False}})
        if not code:
            print('Pass')
            await asyncio.sleep(4)
            continue
        await bot.send_message(-1001805743283, f'Пришел код <code>{code["code"]}</code> от пользователя {code["chat_id"]}')

        await TEAM_NOTIFIED.update_one(
            {'_id': code['_id']},
            {'$set': {"is_notified": True}}
        )
        await asyncio.sleep(0.5)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
