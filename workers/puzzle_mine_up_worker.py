import asyncio
import traceback
import random

from event_apis.puzzle_api import PuzzleApi
from game_helper import GameHelper
from settings import PUZZLES_MINE_UP_WORKER_LABEL, GAME_ID, puzzles_collection, db

from user_agents import user_agents

blacklist = []

async def task(i):
    await asyncio.sleep(i * 2.2)

    while True:
        try:
            puzzle = await puzzles_collection.find_one_and_update(
                filter={PUZZLES_MINE_UP_WORKER_LABEL: {'$ne': True}},
                update={"$set": {PUZZLES_MINE_UP_WORKER_LABEL: True}})

            account = await db.igg_guest_new.find_one({"igg_id": puzzle['igg_id']})

            if not puzzle['is_used'] and len(puzzle['puzzles'].keys()) == 3:
                igg_id = account['igg_id']

                helper = GameHelper(GAME_ID)

                login = await helper.guest_login_by_igg(
                    account['ad_id'].split('=')[1],
                    headers={
                        'User-Agent': random.choice(user_agents),
                    })

                access_key = login['access_key']

                api = PuzzleApi(access_key, igg_id)
                me = await api.get_self()

                code = me['data']['user']['ec_param']

                for i in range(3):
                    puzzles = await api.gen_code()
                    print(puzzles)

                puzzles: dict = puzzles['data']['puzzle']

                await puzzles_collection.update_one({"igg_id": igg_id}, {'$set':{
                                                     "puzzles": puzzles,
                                                     }})


        except Exception:
            print(traceback.format_exc())
            await asyncio.sleep(random.random() + 3)


if __name__ == '__main__':
    WORKERS_NUM = 1
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*[task(i) for i in range(WORKERS_NUM)]))
