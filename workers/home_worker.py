import asyncio
import logging
import traceback
from multiprocessing import Pool

from aiogram.utils.i18n import I18n
import random

from bot import bot
from game_helper import GameHelper
from settings import home_collection, db, HOME_WORKER_LABEL, GAME_ID, LOCALES_DIR, I18N_DOMAIN
import time
from event_apis.home_api import CCHomeApi
from user_agents import user_agents

async def task(i: int):
    await asyncio.sleep(0.1 * i)

    while True:
        try:
            code_item = await home_collection.find_one_and_update(filter={
                '$where': '(this.in_processing < (this.limit * 5) && this.invited_accounts % 1000 < this.limit) && this.limit > 0  && !this.finished'},
                update={"$inc": {"in_processing": 1}},
                sort=[('_id', 1)])
            logging.info(f'Processing: {code_item}')

            if not code_item:
                print('Нет кодов в очереди')
                await asyncio.sleep(5)
                continue
            else:
                code = code_item['code']
                chat_id = code_item['chat_id']
                invited_accounts = code_item['invited_accounts']
                limit = code_item['limit']

                account = await db.igg_guest_new.find_one_and_update(
                    filter={"might_ru_new": {'$gt': 50_000}, f'{HOME_WORKER_LABEL}': {'$ne': True}},
                    update={"$set": {f"{HOME_WORKER_LABEL}": True}})
                print(account)

                user_lang = (await db.aiogram_data.find_one({'chat': chat_id}))['data'].get('locale') or 'ru'
                _ = I18n(path=LOCALES_DIR, default_locale=user_lang, domain=I18N_DOMAIN).gettext

                igg_id = account['igg_id']

                helper = GameHelper(GAME_ID)

                login = await helper.guest_login_by_igg(account['ad_id'].split('=')[1], headers={
                    'User-Agent': random.choice(user_agents),
                })
                access_key = login['access_key']
                print(login)

                await db.igg_guest_new.update_one(
                    filter={"igg_id": account["igg_id"]},
                    update={"$set": {"new_token": access_key}})

                api = CCHomeApi(access_key, igg_id)
                invite = await api.invite(code)
                print(invite)

                if invited_accounts + 1 >= limit:
                    if not (await home_collection.find_one({'_id': code_item['_id']})).get('notified'):
                        await home_collection.update_one({'_id': code_item['_id']}, {'$set': {'notified': True}})
                        try:
                            await bot.send_message(
                                chat_id,
                                _('✅ Награды по коду Акции {} полностью отправлены. Получите награды в игровом почтовом ящике.').format(
                                    code)
                            )
                        except Exception as e:
                            print(e)

                if invite.get('status') == 1:

                    await home_collection.update_one(
                        {'_id': code_item['_id']},
                        {
                            "$inc": {"invited_accounts": 1}
                        })

                elif type(invite.get('error')) == int:
                    continue

                elif 'Вы не подходите по требованиям' in invite.get('error'):
                    continue
                elif "You don't meet the requirements" in invite.get('error'):
                    continue
                elif 'Log in failed. Please try again' in invite.get('error'):
                    continue

                elif 'Login Fehlgeschlagen' in invite.get('error'):
                    continue

                elif 'Неожиданная ошибка' in invite.get('error'):
                    continue

                elif 'Вы использовали максимальное' in invite.get('error') or \
                        "You've redeemed the maximum" in invite.get('error') or \
                        'You entered an invalid code' in invite.get('error') or \
                        'не верный' in invite.get('error') or \
                        "Du hast die maximale Anzahl an Einladungscode-Belohnungen" in invite.get('error') or \
                        'Du hast einen ungültigen Code' in invite.get('error') or \
                        'Du hast einen ungültigen Code' in invite.get('error') or \
                        "邀請碼兌換次數已達上線，無法再進行兌換囉。" in invite.get('error'):

                    await db.igg_guest_new.update_one(
                        filter={"igg_id": account["igg_id"]},
                        update={"$set": {f"{HOME_WORKER_LABEL}": False}})

                    await home_collection.update_one(
                        {"_id": code_item["_id"]},
                        {
                            "$set": {"finished": True}
                        })

                elif invite.get('status') == 0:
                    print('Strange error')

                    await bot.send_message(
                        chat_id,
                        _('❌ Произошла ошибка {} у кода {}. Свяжитесь с поддержкой через @CCletsplay_bot со скриншотом ошибки для выяснения причины')
                            .format(invite.get("error"), code)
                    )
                    await home_collection.update_one(
                        {"code": code},
                        {
                            "$push": {"errors": invite}
                        })

                else:
                    print(invite)

        except Exception:
            print(traceback.format_exc())
            time.sleep(3)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*[task(i) for i in range(3)]))
