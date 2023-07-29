import asyncio
import json
import time
import traceback
import random
from abc import abstractmethod, ABC
from datetime import datetime, timedelta
from typing import Optional

from aiohttp import ClientSession

from bot import bot, release_bot
from settings import GAME_ID, db, EVENT_URL

from user_agents import user_agents

class IggEvent(ABC):
    event_url: str
    name: str

    @abstractmethod
    async def is_available(self, event_page_content: str, params: dict={}) -> bool:
        pass

    async def fetch_start_date(self, event_page_content: str) -> Optional[int]:
        if 'ec_starttime":"' not in event_page_content:
            return None
        return int(event_page_content.split('ec_starttime":"')[1].split('"')[0])

    async def collect(self, params: dict, aggressive: bool = False):
        pass


class CarnivalEvent(IggEvent):
    async def is_available(self, event_page_content: str, params: dict={}):
        return '"chance":{"all":' in event_page_content and '"chance":{"all":0' not in event_page_content

    event_url = 'carnival_giftcard'
    name = 'Магическая Рулетка'


class DiceEvent(IggEvent):
    async def is_available(self, event_page_content: str, params: dict={}):
        return '"left":' in event_page_content and '"left":0' not in event_page_content

    event_url = 'dice'
    name = 'Настолка'

    async def collect(self, params: dict, aggressive: bool = False):
        event_info = await db.enabled_events.find_one({'event': self.event_url})
        if not event_info['status']:
            return False, "Завершено"
        collection_info = await db.collected_events.find_one(
            {'event': self.event_url, 'mark': f"{event_info['start_date']}", "igg_id": params["uid"]}
        )
        if collection_info:
            collection_date: datetime = collection_info['collection_date']
            recollection_time = (collection_date + timedelta(days=1)).replace(hour=8)

            if datetime.now() < recollection_time:
                return False, 'Уже собрано'

        async with ClientSession() as session:
            headers = {
                'User-Agent': random.choice(user_agents),
            }
            resp = await session.get(f'{EVENT_URL}/event/dice/ajax.req.php?action=lottery', params=params,
                                     timeout=1, headers=headers)
            resp_json = await resp.text()

            j = json.loads(resp_json[1:])
            if j['status']:
                await db.collected_events.insert_one(
                    {'event': self.event_url, 'mark': f"{event_info['start_date']}", "igg_id": params["uid"],
                     'response': j, 'collection_date': datetime.now()})
                return True, j['data']['msg']

            if j['error'] == 1:
                await db.collected_events.insert_one(
                    {'event': self.event_url, 'mark': f"{event_info['start_date']}", "igg_id": params["uid"],
                     'response': j, 'collection_date': datetime.now()})

            return False, resp_json


class CatcherEvent(IggEvent):
    event_url = 'ufo_catcher'
    name = 'Хватайка'

    async def is_available(self, event_page_content: str, params: dict={}):
        return '"free":{"all"' in event_page_content and '"free":{"all":0' not in event_page_content

    async def collect(self, params: dict, aggressive: bool = False):
        event_info = await db.enabled_events.find_one({'event': self.event_url})
        if not event_info['status']:
            return False, "Завершено"

        collection_info = await db.collected_events.find_one(
            {'event': self.event_url, 'mark': f"{event_info['start_date']}", "igg_id": params["uid"]}
        )

        if collection_info:
            return False, 'Уже собрано'

        async with ClientSession() as session:
            headers = {
                'User-Agent': random.choice(user_agents),
            }
            resp = await session.get(f'{EVENT_URL}/event/ufo_catcher/ajax.req.php?action=lottery', params=params,
                                     timeout=1, headers=headers)
            resp_json = await resp.text()

            if '!LOGIN_FAIL!' in resp_json:
                return False, '!LOGIN_FAIL!'

            j = json.loads(resp_json[1:])
            if j['status']:
                await db.collected_events.insert_one(
            {'event': self.event_url, 'mark': f"{event_info['start_date']}", "igg_id": params["uid"], 'response': j})
                if aggressive and j['data']['credit'] >= 5:
                    credits = j['data']['credit']
                    for i in range(0, credits // 10):
                        await session.get(f'{EVENT_URL}/event/ufo_catcher/ajax.req.php?action=exchange&apid=35835',
                                                 params=params,
                                                 timeout=1, headers=headers)

                    for i in range(0, credits // 5):
                        await session.get(f'{EVENT_URL}/event/ufo_catcher/ajax.req.php?action=exchange&apid=35834',
                                                 params=params,
                                                 timeout=1, headers=headers)

                return True, j['data']['msg']

            if j['error'] == 1:
                await db.collected_events.insert_one(
                    {'event': self.event_url, 'mark': f"{event_info['start_date']}", "igg_id": params["uid"],
                     'response': j})

            return False, resp_json


class CastleWishEvent(IggEvent):
    event_url = 'castle_wish'
    name = 'Фонарики Желаний'

    async def is_available(self, event_page_content: str, params: dict={}):
        return '"light_finish":0' in event_page_content


class MineEvent(IggEvent):
    event_url = 'mine'
    name = 'В Поисках Сокровищ'

    async def is_available(self, event_page_content: str, params: dict={}):
        return 'Событие завершено' not in event_page_content


class GasEvent(IggEvent):
    event_url = 'gas'
    name = 'Маленькая помощь'

    async def is_available(self, event_page_content: str, params: dict={}):
        return "gifts-get-btn" in event_page_content#'"chance":{"all":' in event_page_content and '"chance":{"all":0' not in event_page_content

    async def collect(self, params: dict, aggressive: bool = False):
        event_info = await db.enabled_events.find_one({'event': self.event_url})
        if not event_info['status']:
            return False, "Завершено"

        collection_info = await db.collected_events.find_one(
            {'event': self.event_url, 'mark': f"{event_info['start_date']}", "igg_id": params["uid"]}
        )

        if collection_info:
            return False, 'Уже собрано'

        async with ClientSession() as session:
            headers = {
                'User-Agent': random.choice(user_agents),
            }
            resp = await session.get(f'{EVENT_URL}/event/gas/ajax.req.php?action=battlepower', params=params,
                                     timeout=1, headers=headers)
            resp_json = await resp.text()

            j = json.loads(resp_json[1:])
            if j['status']:
                await db.collected_events.insert_one(
            {'event': self.event_url, 'mark': f"{event_info['start_date']}", "igg_id": params["uid"], 'response': j})
                return True, j['data']['msg']

            if j['error'] == 1:
                await db.collected_events.insert_one(
                    {'event': self.event_url, 'mark': f"{event_info['start_date']}", "igg_id": params["uid"],
                     'response': j})

            return False, resp_json


lock = asyncio.Lock()


class XmasSignin(IggEvent):
    event_url = 'xmas_signin'
    name = 'Входите Ежедневно и Получайте Награды'

    async def is_available(self, event_page_content: str, params: dict={}):
        return 'user_claim_status = ' in event_page_content and 'user_claim_status = 0' not in event_page_content

    async def collect(self, params: dict, aggressive: bool = False):
        event_info = await db.enabled_events.find_one({'event': self.event_url})
        if not event_info['status']:
            return False, "Завершено"

        collection_info = await db.collected_events.find_one(
            {'event': self.event_url, 'mark': f"{event_info['start_date']}", "igg_id": params["uid"]}
        )
        if collection_info:
            collection_date: datetime = collection_info['collection_date']
            recollection_time = (collection_date + timedelta(days=1)).replace(hour=8)

            if datetime.now() < recollection_time:
                return False, 'Уже собрано'

        async with ClientSession() as session:
            headers = {
                'User-Agent': random.choice(user_agents),
            }
            async with lock:
                resp = await session.get(f'{EVENT_URL}/event/xmas_signin/ajax.req.php', params=params,
                                     timeout=1, headers=headers)
                resp_json = await resp.text()

            j = json.loads(resp_json[1:])
            if j['status']:
                await db.collected_events.insert_one(
                    {'event': self.event_url, 'mark': f"{event_info['start_date']}", "igg_id": params["uid"],
                     'response': j, 'collection_date': datetime.now()})
                return True, j['data']['msg']

            if j['error'] == 1:
                await db.collected_events.insert_one(
                    {'event': self.event_url, 'mark': f"{event_info['start_date']}", "igg_id": params["uid"],
                     'response': j, 'collection_date': datetime.now()})

            return False, resp_json


class MagicHouse(IggEvent):
    event_url = 'magic_house'
    name = 'Волшебная Кузница'

    async def is_available(self, event_page_content: str, params: dict={}):
        return '"chance":{"all":' in event_page_content and '"chance":{"all":0' not in event_page_content


class CastleMachine(IggEvent):
    event_url = 'castle_machine'
    name = 'Создающая Машина'

    async def is_available(self, event_page_content: str, params: dict={}):
        return '"extra_info":{"free":' in event_page_content and '"extra_info":{"free":0' not in event_page_content


class CastleStar(IggEvent):
    event_url = 'castle_star'
    name = 'Обожание Героев'

    async def is_available(self, event_page_content: str, params: dict={}):
        return event_page_content.count('100%</span>') == 5


class DragonQuest(IggEvent):
    event_url = 'dragon_quest'
    name = 'Рыцари и Драконы'

    async def is_available(self, event_page_content: str, params: dict={}):
        async with ClientSession() as session:
            headers = {
                'User-Agent': random.choice(user_agents),
            }
            resp = await session.get(f'{EVENT_URL}/event/dragon_quest/ajax.req.php?action=init', params=params,
                                     timeout=1, headers=headers)
            resp_text = await resp.text()
            return '"all":1' in resp_text

class FlopPair(IggEvent):
    event_url = 'flop_pair'
    name = 'Найди Пару'

    async def is_available(self, event_page_content: str, params: dict={}):
        return '"chance":{"all":' in event_page_content and '"chance":{"all":0' not in event_page_content


class Puzzle(IggEvent):
    event_url = 'puzzle2'
    name = 'Загадочный Паззл'

    async def is_available(self, event_page_content: str, params: dict={}):
        return False


class ThanksgivingTime(IggEvent):
    event_url = 'thanksgiving_time'
    name = '10 дней призов'

    async def is_available(self, event_page_content: str, params: dict={}):
        return 'willget' in event_page_content

class SignContinue(IggEvent):
    event_url = 'sign_continue'
    name = 'Войди в игру и получи приз'

    async def is_available(self, event_page_content: str, params: dict={}):
        return '"continue":1' in event_page_content


class WishTree(IggEvent):
    event_url = 'wish_tree'
    name = 'Выращивай призы'

    async def is_available(self, event_page_content: str, params: dict={}):
        return '"shovel"' in event_page_content



event_apis = [
    WishTree(), SignContinue(), ThanksgivingTime(), CarnivalEvent(), DiceEvent(), CatcherEvent(), CastleWishEvent(), MineEvent(), GasEvent(), XmasSignin(),
    MagicHouse(), CastleMachine(), CastleStar(), DragonQuest(), FlopPair(), Puzzle()
]


class EventsWatcher:
    def __init__(self, signed_key: str, igg_id: int, game_id=GAME_ID):
        self.server_url = EVENT_URL
        self.igg_id = igg_id
        self.signed_key = signed_key

        self.default_params = {
            'g_id': game_id,
            'signed_key': self.signed_key,
            'uid': self.igg_id,
        }

    async def check_events(self):
        for event in event_apis:
            async with ClientSession() as session:
                headers = {
                    'User-Agent': random.choice(user_agents),
                }
                resp = await session.get(f'{EVENT_URL}/event/{event.event_url}', params=self.default_params,
                                         timeout=1, headers=headers)
                resp_text = await resp.text()

            print(resp.url)

            was_started = (await db.enabled_events.find_one({'event': event.event_url}) or {'status': False})['status']
            is_started = await event.is_available(resp_text, self.default_params)

            if not is_started and was_started:
                await db.enabled_events.update_one({'event': event.event_url},
                                                   {'$set': {'status': False, 'finish_time': datetime.now()}})
                await release_bot.send_message('@CCEventNotification', f'❌ Ended event: {event.name}')

            if is_started and not was_started:
                await db.enabled_events.update_one({'event': event.event_url},
                                                   {'$set': {'status': is_started, 'start_date': await event.fetch_start_date(resp_text) or int(time.time())}},
                                                   upsert=True)

                await release_bot.send_message('@CCEventNotification', f'✅ Started event: {event.name}')


async def watcher():
    while True:
        keks_account = await db.keks_accounts.find_one({'access_key': {'$exists': True}}, sort=[('uid', -1)])
        watcher = EventsWatcher(keks_account['access_key'], keks_account['iggid'])
        await watcher.check_events()
        await asyncio.sleep(60*60 * 5)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(watcher())
