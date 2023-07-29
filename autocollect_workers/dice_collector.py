import asyncio
import json
import multiprocessing
import random

from aiogram.utils.i18n import I18n
from aiohttp import ClientSession
from pymongo import MongoClient

import datetime

from bot import bot, release_bot
from settings import MONGO_URL, MONGO_PORT, tokens_collection, thanksgiving_collection, db, EVENT_URL, LOCALES_DIR, \
    I18N_DOMAIN, servers
from event_apis.thanksgiving_api import ThanksgivingManager
import time

from user_agents import user_agents


async def task(i: int, workers_num: int):
    while True:
        event_info = await db.enabled_events.find_one({'event': 'dice'})

        if not event_info['status']:
            time.sleep(60 * 60)
            continue
        try:
            collect_label = f'dice_collected_{event_info["start_date"]}'

            async for account in thanksgiving_collection.find({collect_label: {'$ne': True}}):
                try:
                    print(account)
                    igg_account = await tokens_collection.find_one({"_id": account['account_id']})
                    if not igg_account:
                        print(f'Account dropped')
                        continue

                    user_lang = (await db.aiogram_data.find_one({'chat': igg_account['tg_id']}))['data'].get('locale') or 'ru'

                    _ = I18n(path=LOCALES_DIR, default_locale=user_lang, domain=I18N_DOMAIN).gettext

                    async with ClientSession() as session:
                        resp = await session.get(f'{EVENT_URL}event/dice/ajax.req.php?action=lottery',
                                                 params={
                                                     'signed_key': igg_account['sign'],
                                                     'uid': igg_account['uid'],
                                                     'action': 'lottery',
                                                     'g_id': servers[user_lang],
                                                 }, headers={'User-Agent': random.choice(user_agents), 'X-Requested-With': 'XMLHttpRequest'}
                                                 )
                        resp = json.loads((await resp.text())[1:])
                    if resp['status']:
                        await release_bot.send_message(igg_account['tg_id'], text=_('Собрана настолка: {}').format(resp['data']['msg']))
                        print(resp)
                        print(_('Собрана настолка: {}').format(resp['data']['msg']))
                    await thanksgiving_collection.update_one({"_id": account["_id"]}, {"$set": {collect_label: True}})

                except Exception as e:
                    print(e)
                    await asyncio.sleep(5)
        except Exception as e:
            print(e)
            await asyncio.sleep(5)

        print('Pass')
        time.sleep(15)


WORKERS_NUM = 1

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*[task(i, WORKERS_NUM) for i in range(WORKERS_NUM)]))
