import asyncio
import logging
import traceback
import random

from bot import bot
from event_apis.puzzle_api import PuzzleApi
from handlers.puzzles import send_reward_message
from settings import puzzles_autocollect_collection, tokens_collection, puzzles_collection, AUTOCOLLECT_FINISH_LABEL
import time


async def task(i: int):
    await asyncio.sleep(0.1 * i)

    while True:
        try:
            code_item = await puzzles_autocollect_collection.find_one_and_update({AUTOCOLLECT_FINISH_LABEL: {'$ne': True}},
                                                                                 update={"$inc": {"in_processing": 1}},
                                                                                 sort=[('_id', 1)])

            if not code_item:
                logging.info('Pass')
                await asyncio.sleep(5)
                continue

            logging.info(f'Processing: {code_item}')

            account = await tokens_collection.find_one({"_id": code_item['account_id']})

            if not account:
                await puzzles_autocollect_collection.update_one({'_id': code_item['_id']}, update={
                    "$set": {AUTOCOLLECT_FINISH_LABEL: True}})
                continue

            uid = account['uid']
            sign = account['sign']
            tg_id = account['tg_id']

            puzzles_api = PuzzleApi(sign, uid)

            me = await puzzles_api.get_self()
            if me.get('error') == '!LOGIN_FAIL!':
                await puzzles_autocollect_collection.update_one({'_id': code_item['_id']}, update={
                                                                    "$set": {AUTOCOLLECT_FINISH_LABEL: True}})

                await bot.send_message(chat_id=tg_id, text=f'Login to account {uid} failed')
            print(me)
            user = me['data']['user']
            data = me['data']['user']

            print(user)
            if user.get('extra_info'):
                friend_invites = user['extra_info'].get('friend') or []
                puzzle_prize = user['extra_info'].get('puzzle_prize') or []
            else:
                friend_invites = []
                puzzle_prize = []

            for i in range(30 - len(friend_invites)):
                puzzle = data['puzzle']
                for x in '123456789':
                    if x not in puzzle:
                        random_puzzle = int(x)
                        break
                else:
                    random_puzzle = random.randint(1, 9)
                puzzle = await puzzles_collection.find_one_and_update(
                    filter={"is_used": False, f"puzzles.{random_puzzle}": {"$gt": 1}},
                    update={"$set": {"is_used": True}})

                enter = await puzzles_api.enter_code(int(puzzle['igg_id']), random_puzzle)
                data = enter['data']
                time.sleep(2)
                print(enter)

            for i in range(int(user['ec_free'])):
                gen = await puzzles_api.gen_code()
                data = gen['data']

            for i in range(1, 8):
                if i not in puzzle_prize:
                    print(await puzzles_api.claim(i))

            await puzzles_autocollect_collection.update_one({'_id': code_item['_id']},
                                                            update={
                                                                "$set": {AUTOCOLLECT_FINISH_LABEL: True}})

            text, keyboard = await send_reward_message(tg_id, f'{account["_id"]}', 1, data['puzzle_left'], '')
            await bot.send_message(chat_id=tg_id, text=text, reply_markup=keyboard)

        except Exception:
            print(traceback.format_exc())
            time.sleep(3)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*[task(i) for i in range(1)]))
