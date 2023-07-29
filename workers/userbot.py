from datetime import datetime

from aiogram.utils.i18n import I18n
from bson import ObjectId

from telethon import TelegramClient, events

from bot import bot
from settings import MONGO_URL, MONGO_PORT, db, db_keks, LOCALES_DIR, I18N_DOMAIN, HOME_CODES_SUPPORT, TEAM_CODES_SUPPORT, STONKS, STONKS_ALL
import logging

logging.basicConfig(level=logging.INFO)

tg_client = TelegramClient('premium_user_bot', api_id=1910146, api_hash='1558300910a39d704a25846b3337bbba')


async def calc_stonks():
    qiwi_coins = 0
    yoomoney_coins = 0
    keks_coins = 0

    for qiwi_payment in await db.qiwi_v2_payments.find({'_id': {'$gt': ObjectId(STONKS)}}).to_list(None):
        qiwi_coins += float(qiwi_payment['bill']['amount']['value'])

    for yoomoney_payment in await db.yoomoney.find({'_id': {'$gt': ObjectId(STONKS)}}).to_list(None):
        if 'amount' in yoomoney_payment:
            yoomoney_coins += float(yoomoney_payment['amount'])

    for yoomoney_payment in await db_keks.payments.find({'_id': {'$gt': ObjectId(STONKS)}}).to_list(None):
         if 'amount' in yoomoney_payment:
            keks_coins += float(yoomoney_payment['amount'])

    yoomoney_coins = int(yoomoney_coins)
    qiwi_coins = int(qiwi_coins)
    keks_coins = int(keks_coins)

    result = ''
    result += f'Qiwi: {qiwi_coins}\n'
    result += f'Yoomoney: {yoomoney_coins}\n'
    result += f'Keks_bot: {keks_coins}\n'
    result += f'Total: {qiwi_coins + yoomoney_coins + keks_coins}\n'

    return result


async def calc_stonks_all():
    qiwi_coins = 0
    yoomoney_coins = 0
    keks_coins = 0

    for qiwi_payment in await db.qiwi_v2_payments.find({'_id': {'$gt': ObjectId(STONKS_ALL)}}).to_list(None):
        qiwi_coins += float(qiwi_payment['bill']['amount']['value'])

    for yoomoney_payment in await db.yoomoney.find({'_id': {'$gt': ObjectId(STONKS_ALL)}}).to_list(None):
        if 'amount' in yoomoney_payment:
            yoomoney_coins += float(yoomoney_payment['amount'])

    for yoomoney_payment in await db_keks.payments.find({'_id': {'$gt': ObjectId(STONKS)}}).to_list(None):
         if 'amount' in yoomoney_payment:
            keks_coins += float(yoomoney_payment['amount'])

    yoomoney_coins = int(yoomoney_coins)
    qiwi_coins = int(qiwi_coins)
    result = ''
    result += f'Qiwi: {qiwi_coins}\n'
    result += f'Yoomoney: {yoomoney_coins}\n'
    result += f'Total: {qiwi_coins + yoomoney_coins}\n'

    return result

@tg_client.on(events.NewMessage(pattern="/who"))
async def who(event: events.NewMessage):
    reply = await event.get_reply_message()
    if reply.from_id:
        await event.reply(f'Tg id: {reply.from_id.user_id}')
    elif reply.is_private:
        await event.reply(f'Tg id: {reply.peer_id.user_id}')

@tg_client.on(events.NewMessage(pattern="/chat_id"))
async def chat_id(event: events.NewMessage):
    await event.reply(f'Chat id: {event.chat_id}')


@tg_client.on(events.NewMessage(pattern="/stonks"))
async def stonks(event: events.NewMessage):
    if event.chat_id == -1001805743283:
        await event.reply(f'Стонкс: \n{await calc_stonks()}')


@tg_client.on(events.NewMessage(pattern="/all"))
async def stonks_all(event: events.NewMessage):
    if event.chat_id == -1001805743283:
        await event.reply(f'Стонкс весь: \n{await calc_stonks_all()}')


@tg_client.on(events.NewMessage(pattern="\+[-\d+]"))
async def add_coins(event: events.NewMessage):
    coins = int(event.text[1:])

    if event.chat_id == -1001218999907:
        reply = await event.get_reply_message()
        print(reply.text)
        if '\n' in reply.text and reply.text.startswith('```') and all([x.isdigit() for x in reply.text[3:].split('\n')[0]]):
            user_id = int(reply.text[3:].split('\n')[0])
            print(user_id)

            await db.users.update_one(
                {"chat_id": user_id},
                {'$inc': {
                    f'coins': coins
                }
                })
            if coins >= 0:
                await event.respond(f'Начислено {coins} пользователю {user_id}', parse_mode='md')
            else:
                await event.respond(f'Списано {-coins} у пользователя {user_id}', parse_mode='md')
            user_lang = (await db.aiogram_data.find_one({'chat': user_id}))['data'].get('locale') or 'ru'
            _ = I18n(path=LOCALES_DIR, default_locale=user_lang, domain=I18N_DOMAIN).gettext
            if coins >= 0:
                await bot.send_message(user_id, text=_('✅ Вам было успешно начислено {} CastleCoin. Приятной игры.').format(coins))
            else:
                await bot.send_message(user_id, text=_('С вашего баланса было списано {} CastleCoin.').format(-coins))


@tg_client.on(events.NewMessage(pattern='/sueta'))
async def sueta(event: events.NewMessage):
    await event.respond(f'Никакой суеты!')


@tg_client.on(events.NewMessage(pattern="/user_.*"))
async def info2(event: events.NewMessage):
    if event.chat_id == -1001218999907:
        user_id = event.text[6:]
        user_id = int(user_id)
        report = ''
        user = await db.users.find_one({'chat_id': user_id})
        report += f'```{user_id}\n```'
        report += f'User coins: {user.get("coins")}\n\n'

        async for code in HOME_CODES_SUPPORT.find({'chat_id': user_id}):
            report += f'Код: {code["code"]}, limit: {code["limit"]}, invited: {code["invited_accounts"]}, server, finished: {code["finished"]}\n'
        async for code in TEAM_CODES_SUPPORT.find({'chat_id': user_id}):
            report += f'Код: {code["code"]}, limit: {code["limit"]}, invited: {code["invited_accounts"]}, finished: {code["finished"]}\n'

        await event.respond(report, parse_mode='md')


@tg_client.on(events.NewMessage(pattern="", from_users=[890476075]))

async def info(event: events.NewMessage):
    if '&' in event.text:
        text: str = event.text
        user_id = text[text.index('&') + 1:].replace(']', ' ')
        user_id = user_id[: user_id.index(' ')]

        print(user_id)
        user_id = int(user_id)
        report = ''
        user = await db.users.find_one({'chat_id': user_id})

        puzzle_ranks = user['ranks'].get('1') or []
        rank_infos = []
        for rank in puzzle_ranks:
            if rank['id'] == 3 and rank['expires'] > datetime.now():
                rank_infos.append(rank['expires'])

        report += f'```{user_id}\n```'
        report += f'User coins: {user.get("coins")}\n'
        report += f'Puzzle ranks: ' + ", ".join([f"Магистр до {x.strftime('%d-%m-%Y %H:%M')}" for x in rank_infos]) + "\n\n"


        async for code in HOME_CODES_SUPPORT.find({'chat_id': user_id}):
            report += f'Код: {code["code"]}, limit: {code["limit"]}, invited: {code["invited_accounts"]}, finished: {code["finished"]}\n'

        async for code in TEAM_CODES_SUPPORT.find({'chat_id': user_id}):
            report += f'Код: {code["code"]}, limit: {code["limit"]}, invited: {code["invited_accounts"]}, finished: {code["finished"]}\n'

        await event.respond(report, parse_mode='md')

        reply = await event.get_reply_message()
        if reply:
            if ' ' in reply.text:
                command = reply.text[reply.text.index(' ') + 1:]
                print(f'COMMAND: {command}')


if __name__ == '__main__':
    tg_client.start()
    tg_client.run_until_disconnected()
