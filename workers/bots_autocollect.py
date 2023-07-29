import asyncio
import json
import random

from aiohttp import ClientSession

from autocollect_workers.events_checker import CatcherEvent, DiceEvent, GasEvent, XmasSignin
from game_helper import GameHelper
from settings import home_collection, db, HOME_WORKER_LABEL, GAME_ID, LOCALES_DIR, I18N_DOMAIN, EVENT_URL
from user_agents import user_agents

lock = asyncio.Lock()


async def task(i: int):
    await asyncio.sleep(0.5 * i)

    collect_label = 'collected_8_iter'
    events_to_collect = [CatcherEvent(), DiceEvent(), GasEvent(), XmasSignin()]
    relogin_counter = 0
    relogin = False
    while True:

        try:
            account = await db.igg_guest_new.find_one_and_update(
                filter={"might_ru": {'$gt': 10_000}, f'{collect_label}': {'$ne': True}},
                update={"$set": {f"{collect_label}": True}})

            collection_info = await db.collected_events.find_one(
                {'event': 'code_CCHAPPY9', "igg_id": account['igg_id']}
            )

            if not collection_info:
                async with lock:
                    async with ClientSession() as session:
                        resp = await session.get(
                            f'https://castleclash.igg.com/event/cdkey/ajax.req.php?lang=ru&iggid=1280584562&cdkey=55KAND9TH&',
                            params={
                                'lang': 'ru',
                                'iggid': account['igg_id'],
                                'cdkey': 'CCHAPPY9'
                            }, headers={
                                'User-Agent': random.choice(user_agents),
                                'x-requested-with': 'XMLHttpRequest',
                                'referrer': 'https://castleclash.igg.com/event/cdkey/'
                            }
                        )
                        j = json.loads(await resp.text())
                    print('code', j)
                    await db.collected_events.insert_one(
                        {'event': 'code_CCHAPPY9', "igg_id": account['igg_id'],
                         'response': j})

            for event_to_collect in events_to_collect:
                print(event_to_collect)
                params = {
                    'g_id': GAME_ID,
                    'signed_key': account['new_token'],
                    'uid': account['igg_id'],
                }

                if relogin_counter <= 3:
                    status, message = await event_to_collect.collect(params, aggressive=True)
                    print('resp1', status, message)
                    if not status and message == '!LOGIN_FAIL!':
                        print(f'Relogin required {relogin_counter}')
                        relogin = True
                        relogin_counter += 1
                    else:
                        relogin = False

                if relogin or relogin_counter > 3:
                    print('relogin')

                    helper = GameHelper(GAME_ID)

                    login = await helper.guest_login_by_igg(account['ad_id'].split('=')[1], headers={
                        'User-Agent': random.choice(user_agents),
                    })
                    access_key = login['access_key']
                    account['new_token'] = access_key

                    await db.igg_guest_new.update_one(
                        filter={"igg_id": account["igg_id"]},
                        update={"$set": {"new_token": access_key}})

                    params['signed_key'] = access_key

                    status, message = await event_to_collect.collect(params, aggressive=True)
                    print('resp2', status, message)
        except Exception as e:
            print(e)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*[task(i) for i in range(12)]))
