import asyncio

from aiogram.exceptions import TelegramForbiddenError
from telethon.errors import UserDeactivatedError

from bot import release_bot
from commands import exit_keyboard
from settings import db

text = """🇷🇺 <a href="https://telegra.ph/file/0360a226ff83aefa35988.png">Друзья</a>, представляем Вашему вниманию услугу от партнеров Клуба Игроков Castle Clash. Все данные о событии Вы можете узнать в официальном <a href="https://discord.gg/mb6YyZpY6r">Discord канале Castle Clash</a> в вкладке "Уведомления".
В случае, если Вас заинтересовали награды или есть вопросы, обращайтесь в бота @letsplaycastleclash_creative_bot.
Событие проходит за пределами игры, награда начисляется разработчиками и занимает время. 
Не забывайте подписываться, у них бывают интересные события и скидки.

🇬🇧 Friends, we present to your attention a service from the partners of the Castle Clash Players Club. All information about the event can be found in the official Castle Clash Discord channel (https://discord.gg/mb6YyZpY6r) in the "Notifications" tab.
If you are interested in rewards or have questions, please contact @letsplaycastleclash_creative_bot.
The event takes place outside the game, the reward is awarded by the developers and takes time.
Don't forget to subscribe, they have interesting events and even discounts."""

notification_label = 'reklama_creative_may_2023'


async def main():
    while True:
        user = await db.users.find_one({notification_label: {'$ne': True}})
        print(user)
        if not user:
            break
        try:
            await release_bot.send_message(
                chat_id=user['chat_id'],
                text=text,
                reply_markup=exit_keyboard
            )

            await db.users.update_one({'_id': user['_id']}, {'$set': {notification_label: True}})

        except UserDeactivatedError:
            await db.users.update_one({'_id': user['_id']},
                                      {'$set': {'status': 'deactivated', notification_label: True}})

        except TelegramForbiddenError:
            await db.users.update_one({'_id': user['_id']},
                                      {'$set': {'status': 'bot_blocked', notification_label: True}})

        except Exception as e:
            raise e


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())