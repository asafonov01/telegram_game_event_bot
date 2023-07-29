import json
import random

from aiohttp import ClientSession

from settings import EVENT_URL, GAME_ID
from user_agents import user_agents

timeout = (3.05, 10)


class CCTeamApi:
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
            await session.get(f'{self.server_url}/event/team_up', params=self.default_params, timeout=timeout)

    async def invite(self, code: str):
        async with ClientSession() as session:
            for i in range(5):
                try:

                    headers = {
                        'User-Agent': random.choice(user_agents),
                        'X-Requested-With': 'XMLHttpRequest',
                        'Referer': f'https://event-eu-cc.igg.com/event/team_up/?g_id={GAME_ID}&signed_key={self.signed_key}&uid={self.igg_id}'

                    }

                    resp = await session.get(f'{self.server_url}event/team_up/ajax.req.php',
                                    params=self.assembly_params({
                                        'act': 'invite',
                                        'code': code,
                                        't': str(random.random())
                                    }), proxy='http://alekssafonov01:7PYL4rWH9Z@193.111.251.11:50100',headers=headers)
                    break
                except Exception as e:
                    print(e)
            else:
                return {'data': [], 'error': 10, 'status': 0}
            try:
                resp_text = await resp.text()
                print(resp_text[1:])
                return json.loads(resp_text[1:])
                print(await resp.text())
                return json.loads(await resp.text())
            except json.decoder.JSONDecodeError as e:
                raise e
                return {'data': [], 'error': -1, 'status': 0}

