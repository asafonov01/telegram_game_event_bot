import asyncio
import multiprocessing

from pymongo import MongoClient

import datetime

from settings import MONGO_URL, MONGO_PORT, tokens_collection, thanksgiving_collection
from event_apis.thanksgiving_api import ThanksgivingManager
import time


async def task(i: int, workers_num: int):

    while True:
        try:
            async for account in thanksgiving_collection.find({}):
                try:
                    print(account)
                    igg_account = await tokens_collection.find_one({"_id": account['account_id']})
                    if not igg_account:
                        print(f'Account dropped')
                        continue
                    # print(account['cd_time'])
                    if account['cd_time'] < datetime.datetime.now() and account['last_id'] < 41:
                        thg_m = ThanksgivingManager()
                        info = await thg_m.load_account_info(igg_account['sign'], igg_account['uid'])
                        if info.cd_time > 0:
                            cd_finish = datetime.datetime.now() + datetime.timedelta(seconds=info.cd_time / 1000)
                            await thanksgiving_collection.update_one({"_id": account["_id"]}, {
                                "$set": {'cd_time': cd_finish, 'last_id': info.last_id}})
                        else:
                            roll = await thg_m.roll(igg_account['sign'], igg_account['uid'], 1 if info.last_id == 0 else info.last_id)
                            await asyncio.sleep(3)
                            print(roll)
                except Exception as e:
                    print(e)
                    await asyncio.sleep(5)
        except Exception as e:
            print(e)
            await asyncio.sleep(5)

        print('Pass')
        time.sleep(120)


WORKERS_NUM = 1


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*[task(i, WORKERS_NUM) for i in range(WORKERS_NUM)]))
