import asyncio
import json
import random

from aiohttp import ClientSession
from settings import db
from user_agents import user_agents

lock = asyncio.Lock()

async def worker(start):
    print(start)
    while True:
        try:
            for i in range(start , 9999999999999999999999999999):
                if await db.dumped_accounts.find_one({'iggid': i}):
                    print('pass')
                    continue
                async with ClientSession() as session:
                    async with lock:
                        user_info = await session.get(f'https://castleclash.igg.com/shop/get_user_info.php?iggid={i}',
                        headers={'User-Agent': random.choice(user_agents)})
                    try:
                        resp = json.loads(await user_info.text())
                    except Exception as e:
                        print(f'ERROR: ${await user_info.text()}')
                    print(resp)
                    if resp['error'] == 0:
                        await db.dumped_accounts.insert_one(resp['data'])
                    else:
                        await db.dumped_accounts.insert_one(resp)
        except Exception as e:
            print(e)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*[worker(start) for start in [85153887, 92595978, 100270845, 106299202, 120757070, 140491116, 160388721, 185215242, 190627426, 200853730, 215239723, 240801203]]))
