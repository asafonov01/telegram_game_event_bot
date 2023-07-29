import json
from typing import List
from aiohttp import ClientSession, ClientTimeout
import httpx
timeout = 1

headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6,zh-TW;q=0.5,zh;q=0.4'
                }

class CCTraderApi:
    def __init__(self, signed_key: str, igg_id: int, server_url: str = 'http://event-eu-cc.igg.com/'):
        self.server_url = server_url
        self.igg_id = igg_id
        self.signed_key = signed_key

        self.default_params = {
            'signed_key': self.signed_key,
            'uid': self.igg_id,
        }

    def assembly_params(self, params: dict):
        return {**self.default_params, **params}

    async def request_config(self) -> dict:
        async with httpx.AsyncClient(http2=True) as session:
            resp = await session.get(
                f'{self.server_url}event/promotion/ajax.req.php',
                params=self.assembly_params({'action': 'init'}),timeout=timeout,
            headers=headers)
            return json.loads(resp.content.decode('utf-8-sig'))

    async def get_item_ids(self) -> List[int]:
        c = await self.request_config()
        return [int(x['ap_id']) for x in c['data']['user']['items_show']]

    async def friend_bargain(self, item_id: int, friend_id: int):
        async with httpx.AsyncClient(http2=True) as session:
            resp = await session.get(f'{self.server_url}event/promotion/ajax.req.php',
                                     params=self.assembly_params({
                                         'action': 'friend_bargain',
                                         'item': item_id,
                                         'friend': friend_id
                                     }),timeout=timeout,
                                     headers=headers
                                     )
            resp = json.loads(resp.content.decode('utf-8-sig'))
        print(resp)
        return resp

    async def view(self, code):
        async with httpx.AsyncClient(http2=True, proxies='http://alekssafonov01:7PYL4rWH9Z@193.111.251.11:50100') as session:
            resp = await session.get(f'{self.server_url}event/promotion/ajax.req.php',
                                     params=self.assembly_params({
                                         'action': 'view',
                                         'code': code
                                     }), timeout=1, headers=headers)
            resp = json.loads(resp.content.decode('utf-8-sig'))
        print(resp)
        return resp
