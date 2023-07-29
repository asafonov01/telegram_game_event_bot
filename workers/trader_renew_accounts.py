import json
import random

import asyncio

from aiohttp import ClientSession

from game_helper import GameHelper
from settings import db, GAME_ID, trader_collection
from user_agents import user_agents

KEY = 'access_key_v10'
async def main():
    global accounts
    accounts = await db.keks_accounts.find({KEY: {'$exists': False}}).to_list(length=100)
    for account in accounts:
        async with ClientSession() as session:
            resp = await session.get(account['guest_link'],
                                     headers={'User-Agent': random.choice(user_agents)

                                              }
                                     )
            print(await resp.text())
            access_key = json.loads((await resp.text())[:-32])['result']['0']['access_key']

        print(access_key)
        await db.keks_accounts.update_one(
            {'_id': account['_id']},
            {'$set': {KEY: access_key}}
        )

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
