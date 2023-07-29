from dataclasses import dataclass
import json
import random

from aiohttp import ClientSession

from settings import EVENT_URL, GAME_ID
from user_agents import user_agents

@dataclass
class ThanksgivingAccountReport:
    cd_time: int
    last_id: int


class ThanksgivingManager:

    def __init__(self):
        pass

    async def load_account_info(self, sign: str, uid: int):
        async with ClientSession() as session:
            account = await session.get(f'{EVENT_URL}event/thanksgiving_time',
                                        params={
                                            'g_id': GAME_ID,
                                            'signed_key': sign,
                                            'uid': uid},
                                        headers={
                                            'User-Agent': random.choice(user_agents)
                                        }, proxy='http://alekssafonov01:7PYL4rWH9Z@109.172.115.218:50100')

            resp = await account.text()

        if 'var user = ' not in resp:
            print(resp)
            print(account.url)
            raise RuntimeError("Site returns error")

        user = resp.split('var user = ')[1].split(';')[0]
        user_json = json.loads(user)
        cd_time = user_json['cd_time']
        normal = user_json['extra_info']['normal']

        if not normal:
            return ThanksgivingAccountReport(cd_time, last_id=1)

        for i in range(1, 100):
            if str(i) not in normal.keys():
                return ThanksgivingAccountReport(cd_time, last_id=i)

    async def roll(self, sign: str, uid: int, item_id: int):
        async with ClientSession() as session:
            roll = await session.get(f'{EVENT_URL}/event/thanksgiving_time/ajax.req.php',
                                     params={
                                         'apid': f'normal-{item_id}',
                                         'g_id': GAME_ID,
                                         'signed_key': sign,
                                         'uid': uid}, headers={
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 9; Pixel 2 XL Build/PPP3.180510.008) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Mobile Safari/537.36'}
                                     , proxy='http://alekssafonov01:7PYL4rWH9Z@109.172.115.218:50100')
            return await roll.text()
