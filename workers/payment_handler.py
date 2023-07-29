import asyncio
import hashlib
import hmac
from aiogram.utils.i18n import I18n
from aiohttp import web
from aiohttp.web_request import BaseRequest

from bot import bot
from settings import QIWI_PRIVATE_KEY_2, db, LOCALES_DIR, I18N_DOMAIN

qiwi_routes = web.RouteTableDef()
yoomoney_routes = web.RouteTableDef()
monobank_routes = web.RouteTableDef()


@qiwi_routes.post('/f95a_v2_qiwi_handler')
async def payment_handler_qiwi(request: BaseRequest):
    if 'X-Api-Signature-SHA256' not in request.headers:
        print('No sign')
        return web.Response(text="")

    json = await request.json()
    bill = json['bill']

    await db.qiwi_v2_payments.insert_one(json)

    sign = request.headers['X-Api-Signature-SHA256']

    validation_staring = f'{bill["amount"]["currency"]}|{bill["amount"]["value"]}|{bill["billId"]}|{bill["siteId"]}|{bill["status"]["value"]}'
    h = hmac.new(QIWI_PRIVATE_KEY_2.encode(), validation_staring.encode(), hashlib.sha256)
    if h.hexdigest() != sign:
        print(f'Mismatched sign: excepted {sign}, found {h.hexdigest()}. Val string: {validation_staring}')
        return web.Response(text="Err")

    if bill["status"]["value"] != "PAID":
        print(f'Unknown status: {bill["status"]["value"]}')

    comment: str = bill['comment']
    if ' ' not in comment:
        await db.qiwi_v2_payment_errors.insert_one(json)
        return web.Response(text="Invalid user tg id")

    split_comment = comment.split(' ')
    user_id = split_comment[-1]
    sale = 0
    if 'промокодом' in split_comment:
        promo_index = split_comment.index('промокодом')
        promo = split_comment[promo_index+1].lower()

        if all(x.isdigit() or x.isascii() or x == '_' for x in promo):

            code = await db.site_promocodes.find_one({'code': promo.lower()})
            if code:
                 sale = code['sale']
            else:
                await db.qiwi_v2_payment_errors.insert_one({'error': f'Unknown promocode: {promo}'})

        else:
            await db.qiwi_v2_payment_errors.insert_one({'error': f'Invalid promocode: {promo}'})

    if not user_id.isdigit():
        await db.qiwi_v2_payment_errors.insert_one(json)
        return web.Response(text="Invalid user tg id")

    user_id = int(user_id)

    currency = bill['amount']['currency']
    if currency != 'RUB':
        await db.qiwi_v2_payment_errors.insert_one(json)
        return web.Response(text="Invalid currency")

    price = bill['amount']['value']

    coins = int(float(price)/(1-sale/100.0))

    await db.users.update_one(
        {"chat_id": user_id},
        {'$inc': {
            f'coins': coins
        }
        })

    user_lang = (await db.aiogram_data.find_one({'chat': user_id}))['data'].get('locale') or 'en'

    _ = I18n(path=LOCALES_DIR, default_locale=user_lang, domain=I18N_DOMAIN).gettext

    await bot.send_message(user_id, text=_('✅ Вам было успешно начислено {} CastleCoin. Приятной игры.').format(coins))

    return web.Response(text="OK")


@yoomoney_routes.post('/yoomoney_payment_callback_78582566954')
async def payment_handler(request: BaseRequest):

    payload = await request.post()
    print(dict(payload))
    await db.yoomoney.insert_one(dict(payload))

    tg_id = 0
    sale = 0
    if ':' in payload['label']:
        promo, tg_id = payload['label'].split(':')
        promo = promo.lower()
        tg_id = int(tg_id)

        if all(x.isdigit() or x.isascii() or x == '_' for x in promo):

            code = await db.site_promocodes.find_one({'code': promo.lower()})
            if code:
                 sale = code['sale']
            else:
                await db.qiwi_v2_payment_errors.insert_one({'error': f'Unknown promocode: {promo} (yoomoney)'})

        else:
            await db.qiwi_v2_payment_errors.insert_one({'error': f'Invalid promocode: {promo} (yoomoney)'})

    else:
        tg_id = int(payload['label'])

    price = float(payload['withdraw_amount'])

    coin_count = int(price/(1-sale/100.0))
    sign = payload['sha1_hash']

    notification_type = payload['notification_type']
    operation_id = payload['operation_id']
    amount = payload['amount']
    currency = payload['currency']
    datetime = payload['datetime']
    sender = payload['sender']
    codepro = payload['codepro']
    notification_secret = '+sGflYYNDP5zpavUeQrG41WE'
    label = payload['label']

    if currency != '643':
        await db.yoomoney_errors.insert_one(dict(payload))
        return web.Response(text="ERROR", status=300)

    val_string = f'{notification_type}&{operation_id}&{amount}&{currency}&{datetime}&{sender}&{codepro}&{notification_secret}&{label}'
    signature = hashlib.sha1(val_string.encode()).hexdigest()

    if signature != sign:
        print(f'Sign error, original: {sign}, actual: {signature}')
        print(f'Sign string: {val_string}')
        return web.Response(text="ERROR", status=300)

    await db.users.update_one(
        {"chat_id": tg_id},
        {'$inc': {
            f'coins': coin_count
        }
        })

    user_lang = (await db.aiogram_data.find_one({'chat': tg_id}))['data'].get('locale') or 'en'

    _ = I18n(path=LOCALES_DIR, default_locale=user_lang, domain=I18N_DOMAIN).gettext

    await bot.send_message(tg_id, text=_('✅ Вам было успешно начислено {} CastleCoin. Приятной игры.').format(coin_count))

    return web.Response(text="OK")


@monobank_routes.get('/monobank_payment_callback_ak4nfGK27h07')
async def payment_handler_monobank_get(request: BaseRequest):
    return web.Response(text="Ok!", status=200)


@monobank_routes.post('/monobank_payment_callback_ak4nfGK27h07')
async def payment_handler_monobank(request: BaseRequest):
    json = await request.json()

    await db.monobank_payments.insert_one(json)

    comment: str = json['data']['statementItem'].get('comment')
    if not comment:
        return web.Response(text=f"Без комментариев...")
    if 'пользователем' not in comment:
        await db.monobank_payments_errors.insert_one(json)
        return web.Response(text=f"Invalid description: {comment}")

    if ' ' not in comment:
        await db.monobank_payments_errors.insert_one(json)
        return web.Response(text="Invalid user tg id")

    split_comment = comment.split(' ')
    user_id = split_comment[-1]
    sale = 0
    if 'промокодом' in split_comment:
        promo_index = split_comment.index('промокодом')
        promo = split_comment[promo_index+1].lower()

        if all(x.isdigit() or x.isascii() or x == '_' for x in promo):

            code = await db.site_promocodes.find_one({'code': promo.lower()})
            if code:
                 sale = code['sale']
            else:
                await db.monobank_payments_errors.insert_one({'error': f'Unknown promocode: {promo}'})

        else:
            await db.monobank_payments_errors.insert_one({'error': f'Invalid promocode: {promo}'})

    if not user_id.isdigit():
        await db.monobank_payments_errors.insert_one(json)
        print()
        return web.Response(text="Invalid user tg id")

    user_id = int(user_id)

    price = json['data']['statementItem']['amount'] * 2 // 100

    coins = int(float(price)/(1-sale/100.0))

    await db.users.update_one(
        {"chat_id": user_id},
        {'$inc': {
            f'coins': coins
        }
        })

    user_lang = (await db.aiogram_data.find_one({'chat': user_id}))['data'].get('locale') or 'en'

    _ = I18n(path=LOCALES_DIR, default_locale=user_lang, domain=I18N_DOMAIN).gettext

    await bot.send_message(user_id, text=_('✅ Вам было успешно начислено {} CastleCoin. Приятной игры.').format(coins))

    return web.Response(text="OK")

runners = []


async def start_site(app, port):
    runner = web.AppRunner(app)
    runners.append(runner)
    await runner.setup()
    site = web.TCPSite(runner, port=port)
    await site.start()

if __name__ == '__main__':
    qiwi_handler = web.Application()
    qiwi_handler.add_routes(qiwi_routes)

    yoomoney_handler = web.Application()
    yoomoney_handler.add_routes(yoomoney_routes)

    monobank_handler = web.Application()
    monobank_handler.add_routes(monobank_routes)

    loop = asyncio.get_event_loop()

    loop.create_task(start_site(qiwi_handler, port=25015))
    loop.create_task(start_site(yoomoney_handler, port=25027))
    loop.create_task(start_site(monobank_handler, port=25024))

    try:
        loop.run_forever()
    except:
        pass
    finally:
        for runner in runners:
            loop.run_until_complete(runner.cleanup())



