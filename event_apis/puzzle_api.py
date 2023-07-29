import asyncio
import json
import random

from aiohttp import ClientSession

from settings import EVENT_URL, GAME_ID
from user_agents import user_agents

class PuzzleApi:
    def __init__(self, signed_key: str, igg_id: int, game_id=GAME_ID):
        self.server_url = EVENT_URL
        self.igg_id = igg_id
        self.signed_key = signed_key

        self.default_params = {
            'g_id': game_id,
            'signed_key': self.signed_key,
            'uid': self.igg_id,
        }

    def assembly_params(self, params: dict):
        return {**self.default_params, **params}

    def get_headers(self):
        return {
            'User-Agent': random.choice(user_agents),
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f'https://event-eu-cc.igg.com/event/puzzle2/?g_id={GAME_ID}&signed_key={self.signed_key}&uid={self.igg_id}'
        }

    async def get_self(self):
        async with ClientSession() as session:
            resp = await session.get(f'{self.server_url}event/puzzle2/ajax.req.php',
                                     params=self.assembly_params({
                                         'action': 'get_resource',
                                     }), headers=self.get_headers()
                                     )
            return json.loads((await resp.text())[1:])

    async def claim(self, item_id: int):
        async with ClientSession() as session:
            resp = await session.get(f'{self.server_url}event/puzzle2/ajax.req.php',
                                     params=self.assembly_params({
                                         'action': 'claim',
                                         'id': item_id
                                     }),  headers=self.get_headers())
            return json.loads((await resp.text())[1:])

    async def exchange(self, item_id: int):
        async with ClientSession() as session:
            resp = await session.get(f'{self.server_url}event/puzzle2/ajax.req.php',
                                     params=self.assembly_params({
                                         'action': 'exchange',
                                         'id': item_id
                                     }), headers=self.get_headers())
            return json.loads((await resp.text())[1:])

    async def enter_code(self, friend_igg_id: int, puzzle: int):
        async with ClientSession() as session:
            resp = await session.get(f'{self.server_url}event/puzzle2/ajax.req.php',
                                     params=self.assembly_params({
                                         'action': 'claim_friend_puzzle',
                                         'friend_iggid': friend_igg_id,
                                         'puzzle': puzzle,
                                     }), headers=self.get_headers())
            return json.loads((await resp.text())[1:])


    async def gen_code(self):

        async with ClientSession() as session:
            for i in range(5):
                try:
                    resp = await session.get(f'{self.server_url}event/puzzle2/ajax.req.php',
                                             params=self.assembly_params({
                                                 'action': 'lottery',
                                             }), headers=self.get_headers())
                    break
                except Exception as e:
                    print(e)
            else:
                return {'data': [], 'error': 10, 'status': 0}

            try:
                j = json.loads((await resp.text())[1:])
            except json.decoder.JSONDecodeError as e:
                print('puzzle api error', e)
                return {'data': [], 'error': -1, 'status': 0}

        return j
