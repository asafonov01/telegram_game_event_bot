import asyncio
import logging
from aiogram.utils.i18n import I18n

from bot import bot
from event_apis.trader_api import CCTraderApi
from game_helper import GameHelper
from settings import trader_collection, LOCALES_DIR, I18N_DOMAIN, db, GAME_ID
import random

from user_agents import user_agents

accounts = []

KEY = 'access_key_v10'

async def user_task(i: int):
    logging.info(f'Worker {i} launched!')

    while True:
        code_item = await trader_collection.find_one_and_update(
            filter={"in_processing": False, "finished": {'$ne': True}},
            update={"$set": {"in_processing": True}})

        logging.info(f'Processing {code_item}')

        try:
            if code_item:
                logging.info(f'Processing code: {code_item}')
                code = code_item['code']
                friend_id = code_item['friend_id']
                item_id = code_item['item_id']
                chat_id = code_item['chat_id']

                user_lang = (await db.aiogram_data.find_one({'chat': chat_id}))['data'].get('locale') or 'ru'
                logging.info(f'User lang: {user_lang}')
                logging.info(f'User: {chat_id}')

                _ = I18n(path=LOCALES_DIR, default_locale=user_lang, domain=I18N_DOMAIN).gettext

                used_accounts = [] if 'used_accounts' not in code_item else code_item['used_accounts']
                #print(accounts, used_accounts)
                account = random.choice([x for x in accounts if int(x['iggid']) not in map(int, used_accounts)])
                await trader_collection.update_one({'_id': code_item['_id']},
                                                   {'$push': {'used_accounts': int(account['iggid'])}})
                used_accounts.append(account['iggid'])

                api = CCTraderApi(account[KEY], account['iggid'])

                item_ids = await api.get_item_ids()

                stop_list = [] if item_id is None else [x for x in item_ids if x != item_id]
                try:
                    await bot.send_message(chat_id, _('Код {} начал обрабатываться... ').format(code) )
                except Exception as e:
                    print(e)

                while len(stop_list) != len(item_ids):
                    account = random.choice([x for x in accounts if int(x['iggid']) not in map(int, used_accounts)])
                    await trader_collection.update_one({'_id': code_item['_id']},
                                                 {'$push': {'used_accounts': int(account['iggid'])}})
                    used_accounts.append(account['iggid'])

                    api = CCTraderApi(account[KEY], account['iggid'])

                    for item_id in [x for x in item_ids if x not in stop_list]:
                        await asyncio.sleep(1)
                        res = await api.friend_bargain(item_id, friend_id)
                        if 'error' in res.keys() and res['error']:
                            if res['error'] == 1:
                                stop_list.append(item_id)
                                await trader_collection.update_one({'_id': code_item['_id']},
                                                             {'$set': {"finished": True}})
                                try:
                                    await bot.send_message(chat_id,
                                        _('✅ Цена предмета по коду {} максимально снижена').format(code))
                                except Exception as e:
                                    print(e)

                                break

                            if res['error'] != 2 and res['error'] != 'Log in failed. Please try again.':
                                await trader_collection.update_many({'code': code},
                                                              {'$set': {"finished": True,
                                                                        "result_error": res['error']}})
                                print('Error found')

                                stop_list.append(item_id)
                                try:
                                    await bot.send_message(chat_id,
                                        _('✅ Цена предмета по коду {} максимально снижена').format(code))
                                except Exception as e:
                                    print(e)

                            else:
                                break
            else:
                await asyncio.sleep(5)
        except Exception as e:
            await trader_collection.update_one(filter={"_id": code_item["_id"]},
                                         update={"$set": {"in_processing": False}})
            raise e
            print(e)


workers_num = 1
logging.basicConfig(level=logging.INFO)


async def main():
    global accounts
    accounts = await db.keks_accounts.find({KEY: {'$exists': True}}).to_list(length=130)

    await trader_collection.update_many(
        {'finished': {'$ne': True}, "in_processing": True},
        {'$set': {"in_processing": False}}
    )
    tasks = [user_task(i) for i in range(workers_num)]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
