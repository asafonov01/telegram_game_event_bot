import asyncio

from aiohttp import web
from aiohttp.abc import BaseRequest
from urllib import parse
from telethon import TelegramClient, events
import logging

logging.basicConfig(level=logging.INFO)

tg_client = TelegramClient('premium_user_bot1', api_id=1910146, api_hash='1558300910a39d704a25846b3337bbba')

forward_routes = web.RouteTableDef()


@forward_routes.post('/sms_forward')
async def payment_handler_qiwi2(request: BaseRequest):
    parsed = parse.parse_qs(await request.text())

    print(parsed)

    print(parsed['aaa'][0])
    async with tg_client:
        print(await tg_client.send_message(-1001805743283, f'Sms: {parsed["aaa"][0]}'))

    return web.Response(text="OK")

if __name__ == '__main__':
    forward_handler = web.Application()
    forward_handler.add_routes(forward_routes)
    loop = asyncio.get_event_loop()

    loop.create_task(tg_client.connect())



    web.run_app(forward_handler, port=9538, host='0.0.0.0')
