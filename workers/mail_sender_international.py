import asyncio

from aiogram.exceptions import TelegramForbiddenError
from telethon.errors import UserDeactivatedError

from bot import release_bot
from commands import exit_keyboard
from settings import db

langs_to_send = ['ru']

text = """«Guiding Hand» | «Направляющая Рука»

Сегодня последний день, чтобы добавить студентов. Перейдите в раздел «Направляющая рука», чтобы добавить свой код и получить все награды за приглашение студентов, в соответствии с правилами мероприятия.

Стоимость 300 CastleCoin [300 RUB / 150 UAH].

Today is last day to add students. Go to «Guiding Hand» section to add your code and receive all rewards of invite students under the event rules. 

Cost 300 CastleCoin [3 USD / 3 EUR].
"""

notification_label = 'team_up_nov_2022_ended'


async def main():
    query = {notification_label: {'$ne': True}, 'chat': {'$gt': 0}}
    if 'ALL' in langs_to_send:
        pass
    elif '*' in langs_to_send:
        query |= {'$or': [{'data.locale': {'$in': langs_to_send}}, {'data.locale': {'$exists': False}}]}
    else:
        query |= {'data.locale': {'$in': langs_to_send}}

    count = await db.aiogram_data.count_documents(query)
    print(f'Рассылаю сообщение {count} пользователям...')

    sent_num = 0
    while True:
        user = await db.aiogram_data.find_one(query)
        print(f'Разослано {sent_num} / {count} пользователям')
        sent_num += 1

        if not user:
            break
        try:
            await release_bot.send_message(
                chat_id=user['chat'],
                text=text,
                reply_markup=exit_keyboard
            )

            await db.aiogram_data.update_one({'_id': user['_id']}, {'$set': {notification_label: True}})

        except UserDeactivatedError:
            await db.aiogram_data.update_one({'_id': user['_id']},
                                      {'$set': {'status': 'deactivated', notification_label: True}})

        except TelegramForbiddenError:
            await db.aiogram_data.update_one({'_id': user['_id']},
                                      {'$set': {'status': 'bot_blocked', notification_label: True}})

        except Exception as e:
            raise e


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())