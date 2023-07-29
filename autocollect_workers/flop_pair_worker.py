import asyncio
from autocollect_workers.events_checker import EventsWatcher
import random

from aiohttp import ClientSession

from settings import GAME_ID, EVENT_URL, db
from user_agents import user_agents


class FlopPairWorker:

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

    async def flop(self, pair_id: int):
        headers = {
            'User-Agent': random.choice(user_agents),
        }
        async with ClientSession() as session:

            resp = await session.get(f'{self.server_url}event/regress_v2/ajax.req.php',
                                     params=self.assembly_params({
                                         'act': 'invite',
                                         'code': code,
                                         't': str(random.random())
                                     }), headers=headers)


async def watcher():
    keks_account = await db.keks_accounts.find_one({'access_key': {'$exists': True}})
    watcher = EventsWatcher(keks_account['access_key'], keks_account['iggid'])
    await watcher.check_events()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(watcher())
