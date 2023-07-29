import json
import random

from aiohttp import ClientSession

from settings import EVENT_URL, GAME_ID
from user_agents import user_agents

timeout = (3.05, 10)


class FlopPairApi:
    def __init__(self, signed_key: str, igg_id: int):
        self.server_url = EVENT_URL
        self.game_id = GAME_ID
        self.igg_id = igg_id
        self.signed_key = signed_key

        self.default_params = {
            'g_id': self.game_id,
            'signed_key': self.signed_key,
            'uid': self.igg_id,
        }

    def assembly_params(self, params: dict):
        return {**self.default_params, **params}

    async def init_session(self):
        async with ClientSession() as session:
            await session.get(f'{self.server_url}/event/flop_pair', params=self.default_params, timeout=timeout)

    async def get_pairs(self, code: str):
        async with ClientSession() as session:
                headers = {
                    'User-Agent': random.choice(user_agents),
                }

                resp = await session.get(f'{self.server_url}event/flop_pair',
                                params=self.assembly_params({
                                    'act': 'invite',
                                    'code': code,
                                    't': str(random.random())
                                }), proxy='http://Sc1qEc:VCpzAe@194.28.211.39:9951',headers=headers)
                print(await resp.text())


