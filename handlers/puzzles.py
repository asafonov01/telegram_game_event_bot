import random
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.dispatcher.filters.callback_data import CallbackData
from aiogram.dispatcher.fsm.context import FSMContext
from aiogram.types import Message, KeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from bson import ObjectId
from pydantic import typing
from pymongo import ReturnDocument

from commands import Commands, exit_keyboard
from event_apis.puzzle_api import PuzzleApi
from settings import IS_PUZZLES_ENABLED, DEBUG, puzzles_collection, db, tokens_collection, \
    puzzles_autocollect_collection, LOCALES_DIR, I18N_DOMAIN
from states import BotStates
from aiogram.utils.i18n import gettext as _, lazy_gettext, I18n
from babel.support import LazyProxy


class CollectPuzzleRewardCallback(CallbackData, prefix='collect_puzzle_reward'):
    account_id: str
    item_id: int
    batch_size: int


class ChoosePuzzleRewardBatchSizeCallback(CallbackData, prefix='choose_puzzle_reward_batch_size'):
    account_id: str
    batch_size: int
    puzzle_left: int


def __(*args: typing.Any, **kwargs: typing.Any) -> LazyProxy:
    return lazy_gettext(*args, **kwargs, enable_cache=False)


class PuzzleCommands:
    RANDOM_PUZZLE_PACK = __("10 случайных пазлов")
    BUY_PUZZLES = __("Активировать доступ к Загадочному Пазлу")
    BUY_PUZZLE_PACK = __("Подтвердить покупку")
    AUTO_COLLECT = __("Автосбор")


puzzles_router = Router()


@puzzles_router.message(F.text == Commands.EVENT_PUZZLES.name)
async def puzzles(message: Message, state: FSMContext, user: dict):
    if not IS_PUZZLES_ENABLED:
        return await message.reply(
            _('❌ События сейчас нет в игре. \n\nАнонс о запуске узнайте на канале @letsplaycastleclash'),
            reply_markup=ReplyKeyboardBuilder().button(text=Commands.EXIT.name).as_markup(resize_keyboard=True)
        )

    await state.set_state(BotStates.event_puzzles)
    await puzzles_section(message, state, user)


async def gen_puzzles_keyboard(user: dict):
    markup = ReplyKeyboardBuilder()
    markup.button(text=str(PuzzleCommands.AUTO_COLLECT))
    markup.button(text=str(PuzzleCommands.BUY_PUZZLES))
    for x in range(1, 10):
        if DEBUG:
            markup.button(text=_('{} {} шт').format(x, (
                await puzzles_collection.count_documents({f"puzzles.{x}": {"$gt": 1}, "is_used": False}))))
        else:
            markup.button(text=f'{x}')

    markup.row(KeyboardButton(text=str(PuzzleCommands.RANDOM_PUZZLE_PACK)))

    markup.row(KeyboardButton(text=str(Commands.EXIT.name)))

    markup.adjust(2, 3, 3, 3, 2)

    return markup.as_markup(resize_keyboard=True)


@puzzles_router.message(state=BotStates.event_puzzles)
async def puzzles_section(message: Message, state: FSMContext, user: dict):
    text = _(
        'Выбран раздел: <b>Загадочный пазл</b>\n\n• <a href="https://letsplaycastleclash.com/faq"><b>Ознакомьтесь с FAQ</b></a> Загадочного пазла.\n• Нажмите на кнопку<b> «Активировать доступ к пазлам»</b>, подтвердите покупку тарифа ещё раз, нажав <b>«Подтвердить покупку»</b>.\n• После активации, заново зайдите в раздел Загадочный Пазл, чтобы начать пользоваться.')

    await message.reply(text, reply_markup=await gen_puzzles_keyboard(user), disable_web_page_preview=True)
    await state.set_state(BotStates.event_puzzles_select_puzzle)


@puzzles_router.message(F.text == PuzzleCommands.BUY_PUZZLES, state=BotStates.event_puzzles_select_puzzle)
async def buy_puzzles(message: Message, user: dict, state: FSMContext):
    markup = ReplyKeyboardBuilder().button(text=PuzzleCommands.BUY_PUZZLE_PACK.value).button(
        text=Commands.EXIT.name).as_markup(resize_keyboard=True)

    await message.reply(text=_(
        '<b>Активировать доступ к пазлам</b> \n\n'
        '• За 30 CastleCoin вы получаете 30 кодов друга на один аккаунт по правилам События. \n'
        '• Покупка тарифа не ограничена.'),
        reply_markup=markup)


PRICE = 30


@puzzles_router.message(F.text == PuzzleCommands.BUY_PUZZLE_PACK, state=BotStates.event_puzzles_select_puzzle)
async def buy_puzzle_pack(message: Message, user: dict):
    user_coins = user.get("coins", 0)
    if user_coins < PRICE:
        return await message.reply(
            _('У вас недостаточно CastleCoin\'ов для покупки. Нужно {}, у вас есть: {}').format(PRICE, user_coins),
            reply_markup=ReplyKeyboardBuilder().button(text=str(Commands.DONATE.name)).button(
                text=Commands.EXIT.name).as_markup(resize_keyboard=True))

    await db.users.find_one_and_update(
        filter={"chat_id": user['chat_id']},
        update={"$inc": {"coins": -PRICE}})

    expires = datetime.now() + timedelta(days=7)

    await db.users.update_one(
        {"chat_id": user['chat_id']},
        {'$push': {
            f'ranks.1':
                {'id': 3, 'expires': expires}
        }
        })

    result_string = _(
        '✅ Загадочный Пазл куплен до {} <a href="http://google.com/search?q=time+in+moscow+now"><b>Московское время</b></a>. \nПриятного пользования 😎 ') \
        .format(expires.strftime("%d-%m-%Y %H:%M GMT+3"))

    await message.reply(result_string,
                        reply_markup=ReplyKeyboardBuilder().button(
                            text=Commands.EXIT.name).as_markup(resize_keyboard=True), disable_web_page_preview=True)


@puzzles_router.message(F.text == PuzzleCommands.AUTO_COLLECT, state=BotStates.event_puzzles_select_puzzle)
async def auto_collect_puzzles(message: Message, state: FSMContext, user: dict):
    keyboard = ReplyKeyboardBuilder() \
        .button(text=Commands.EXIT.name).as_markup(resize_keyboard=True, one_time_keyboard=True)

    await message.reply(
        _('Выбран раздел: <b>Автосбор пазлов</b> \n\n'
          # 'Выберите свой аккаунт или введите ссылку нового для добавления:\n'
          '• Откройте любого Героя в Алтаре Героев >> под Героем синяя кнопка «Рекомендация», нажмите.\n'
          '• Вас перенаправит на страницу браузера. Из строки скопируйте ссылку >> отправьте ссылку боту. \n\n'
          '<b>⚠ Примечание:</b> Автосбор доступен при наличии 30 и более пазлов'),
        reply_markup=keyboard),
    await state.set_state(BotStates.event_puzzles_select_account_data)


@puzzles_router.message(state=BotStates.event_puzzles_select_account_data)
async def puzzles_account_receiver(message: Message, state: FSMContext, user: dict):
    await state.set_state(BotStates.event_puzzles_select_puzzle)

    puzzle_ranks = user['ranks'].get('1') or []

    total_puzzle_attempts = 0

    for rank in puzzle_ranks:
        if rank['id'] == 3 and rank['expires'] > datetime.now():
            total_puzzle_attempts += 30

    used_paid_attempts = 0
    if 'used_attempts' in user and 'puzzle' in user['used_attempts']:
        used_paid_attempts = user['used_attempts']['puzzle']

    if total_puzzle_attempts - used_paid_attempts < 30:
        return await message.reply(
            _('<b>❌ Доступно в платной версии</b>. Пожалуйста, активируйте Загадочный Пазл за 30 CastleCoin.'),
            reply_markup=await gen_puzzles_keyboard(user=user))

    if 'uid=' not in message.text or 'signed_key=' not in message.text:
        return await message.reply(
            _('❌ <b>Неверная ссылка.</b> Причины возникновения: \n\n'
              '1. <b>signed_key</b> — отсутствует в ссылке, неверный символ и/или ваш ключ истек. Возьмите новую ссылку с активным signed_key. \n'
              '2. <b>uid</b> — отсутствует в ссылке и/или неверный IGG ID. Проверьте корректность IGG ID.'),
            reply_markup=exit_keyboard, disable_web_page_preview=True)

    uid = message.text[message.text.index('uid=') + len('uid='):]
    if '&' in uid:
        uid = uid[:uid.index('&')]

    if not uid.isdigit():
        await message.reply(
            _(
                f'❌ <b>Неверная ссылка</b> \n\n <b>uid</b> — отсутствует в ссылке и/или неверный IGG ID.',
            ),
            reply_markup=exit_keyboard)

    uid = int(uid)

    sign = message.text[message.text.index('signed_key=') + len('signed_key='):]
    if '&' in sign:
        sign = sign[:sign.index('&')]

    puzzles_api = PuzzleApi(sign, uid)

    try:
        pass
       # me = await puzzles_api.get_self()

    except Exception as e:
        return await message.reply(
            _('❌ <b>Неверная ссылка</b> \n\n'
              '<b>Возможные причины:</b>\n'
              '— Signed_key недоступен для использования. Пожалуйста, возьмите новую ссылку из игры.'
              '— Ссылка не содержит знаки: <b>& =</b> \n'
              '— В ссылке есть пробел. Проверьте, чтобы было без пробела.\n'
              '— Отсутствует <b>signed_key</b> или <b>uid</b>.'),
            reply_markup=exit_keyboard)

    link = await tokens_collection.find_one_and_update(
        {"uid": uid},
        {"$set": {
            'tg_id': message.from_user.id,
            'sign': sign,
        }},
        upsert=True,
        return_document=ReturnDocument.AFTER)

    if await puzzles_autocollect_collection.find_one({'account_id': link['_id']}):
        await message.reply(_('Ваш аккаунт получил все 30 пазлов, доступное по правилам Акции.'))
        return

    await puzzles_autocollect_collection.update_one(
        {
            'account_id': link['_id'],
        }, {'$set': {}}, upsert=True
    )

    await db.users.update_one(
        {"chat_id": message.chat.id},
        {'$inc': {
            f'used_attempts.puzzle': 30,
        }
        })

    await message.reply(
        _('✅ <b>Ссылка добавлена.</b> Использовано 30 пазлов.'),
        reply_markup=exit_keyboard)


@puzzles_router.message(state=BotStates.event_puzzles_select_puzzle)
async def puzzles_giver(message: Message, state: FSMContext, user: dict):
    puzzle_ranks = user['ranks'].get('1') or []

    total_puzzle_attempts = 0

    for rank in puzzle_ranks:
        if rank['id'] == 3 and rank['expires'] > datetime.now():
            total_puzzle_attempts += 30

    used_paid_attempts = 0
    if 'used_attempts' in user and 'puzzle' in user['used_attempts']:
        used_paid_attempts = user['used_attempts']['puzzle']

    if message.text == PuzzleCommands.RANDOM_PUZZLE_PACK:
        if used_paid_attempts < total_puzzle_attempts:
            left_puzzles = total_puzzle_attempts - used_paid_attempts
            puzzles_to_give = min(left_puzzles, 10)
            errors_num = 0
            codes = []
            for i in range(puzzles_to_give):
                random_puzzle = random.randint(1, 9)
                puzzle = await puzzles_collection.find_one_and_update(
                    filter={"is_used": False, f"puzzles.{random_puzzle}": {"$gt": 1}},
                    update={"$set": {"is_used": True}})

                if puzzle is None:
                    codes.append(_('😔 К сожалению, эти коды закончились. Сообщите в поддержку @CCletsplay_bot.'))
                    errors_num += 1
                else:
                    codes.append(puzzle["code"])

            await db.users.update_one(
                {"chat_id": message.chat.id},
                {'$inc': {
                    f'used_attempts.puzzle': puzzles_to_give - errors_num,
                }
                })

            await message.reply('\n'.join([f'<code>{x}</code>' for x in codes]),
                                reply_markup=await gen_puzzles_keyboard(user=user))
        else:
            return await message.reply(
                _('<b>❌ Доступно в платной версии</b>. Пожалуйста, активируйте Загадочный Пазл за 30 CastleCoin.'),
                reply_markup=await gen_puzzles_keyboard(user=user))

    elif message.text and message.text[0].isdigit():
        if used_paid_attempts >= total_puzzle_attempts:
            return await message.reply(
                _('<b>❌ Доступно в платной версии</b>. Пожалуйста, активируйте Загадочный Пазл за 30 CastleCoin.'),
                reply_markup=await gen_puzzles_keyboard(user=user))

        puzzle_id = message.text[0]

        puzzle = await puzzles_collection.find_one_and_update(
            filter={"is_used": False, f"puzzles.{puzzle_id}": {"$gt": 1}},
            update={"$set": {"is_used": True}})

        if puzzle is None:
            return await message.reply(_('😔 К сожалению, эти коды закончились. Сообщите в поддержку @CCletsplay_bot.'),
                                       reply_markup=await gen_puzzles_keyboard(user=user))
        else:
            await db.users.update_one(
                {"chat_id": message.chat.id},
                {'$inc': {
                    f'used_attempts.puzzle': 1
                }
                })

            return await message.reply(_('Ваш код для {} пазла: <code>{}</code>').format(puzzle_id, puzzle["code"]),
                                       reply_markup=await gen_puzzles_keyboard(user=user))

    else:
        await message.reply(_('⚠ Пожалуйста, воспользуйтесь кнопками бота'),
                            reply_markup=await gen_puzzles_keyboard(user=user))


async def send_reward_message(tg_id: int, account_id: str, batch_size: int, puzzle_left: int, log: str):
    user_lang = (await db.aiogram_data.find_one({'chat': tg_id}))['data'].get('locale') or 'ru'

    _ = I18n(path=LOCALES_DIR, default_locale=user_lang, domain=I18N_DOMAIN).gettext

    items = (
        (37305, _('Карта Созвездий *1'), 1),
        (37306, _('Книга Навыка Супер-Питомца*30'), 1),
        (37307, _('Сумка Питомцев IV*30'), 1),
        (37308, _('Ящик с частями Обликов Зданий I*20'), 1),
        (37309, _('Магическая Пыльца*10'), 2),
        (37310, _('Сундук Замка VI*4'), 2),
        (37311, _('Сундук Замка V*4'), 2),
        (37312, _('Мешок выбора Облика Эпич. Героя I*5'), 5),
        (37313, _('Мешок выбора Осколков Эпич. Героя I*5'), 5)
    )

    keyboard = InlineKeyboardBuilder()

    x1_prefix, x10_prefix = '', ''
    if batch_size == 10:
        x10_prefix = '✅ '
    else:
        x1_prefix = '✅ '

    keyboard.button(text=f'{x1_prefix}X1', callback_data=ChoosePuzzleRewardBatchSizeCallback(account_id=account_id, batch_size=1, puzzle_left=puzzle_left))
    keyboard.button(text=f'{x10_prefix}X10', callback_data=ChoosePuzzleRewardBatchSizeCallback(account_id=account_id, batch_size=10, puzzle_left=puzzle_left))

    for (item_id, item_name, item_price) in items:
        keyboard.button(text='{} – {}'.format(item_name, item_price),
                        callback_data=CollectPuzzleRewardCallback(item_id=item_id,
                                                                  account_id=account_id,
                                                                  batch_size=batch_size).pack())
    keyboard.adjust(2, 1)

    keyboard = keyboard.as_markup(resize_keyboard=True)

    account = await tokens_collection.find_one({"_id": ObjectId(account_id)})
    uid = account['uid']

    text = _(
        '✅ Пазлы успешно введены на аккаунте IGG ID {}.\n\n Выберите следующие награды ниже. Доступно повторов пазлов: {}'
    ).format(uid, puzzle_left) + f'\n\nLOG: {log}'
    return text, keyboard


@puzzles_router.callback_query(ChoosePuzzleRewardBatchSizeCallback.filter(), state='*')
async def choose_puzzle_reward_batch_size(query: CallbackQuery, state: FSMContext, callback_data: ChoosePuzzleRewardBatchSizeCallback):
    await query.answer()
    text, keyboard = await send_reward_message(query.from_user.id, callback_data.account_id, callback_data.batch_size, callback_data.puzzle_left, '')
    await query.message.edit_reply_markup(keyboard)


@puzzles_router.callback_query(CollectPuzzleRewardCallback.filter(), state='*')
async def collect_reward(query: CallbackQuery, state: FSMContext, callback_data: CollectPuzzleRewardCallback):

    if 'LOG:' in query.message.text:
        old_log = query.message.text.split('LOG:')[1][1:]
    else:
        old_log = ''

    for i in range(callback_data.batch_size):
        account = await tokens_collection.find_one({"_id": ObjectId(callback_data.account_id)})
        uid = account['uid']
        sign = account['sign']
        tg_id = account['tg_id']

        user_lang = (await db.aiogram_data.find_one({'chat': tg_id}))['data'].get('locale') or 'en'

        servers = {
            'ru': 1030059902,
            'uk': 1030059902,
            'by': 1030059902,

            'en': 1030019902,
            'de': 1030039902,
            'fr': 1030049902,
            'es': 1030079902,
            'id': 1030099902,
            'it': 1030119902,
            'tr': 1030129902,
            'pt': 1030139902,
            'ar': 1030159902
        }

        puzzles_api = PuzzleApi(sign, uid, servers.get(user_lang) or 'en')
        ex = await puzzles_api.exchange(callback_data.item_id)

        if ex.get('error') == 2:
            await query.answer(_('Награда закончилась'))
            old_log += f"\n{_('Награда закончилась')}"
            text, keyboard = await send_reward_message(
                tg_id, callback_data.account_id,
                callback_data.batch_size,
                0,
                f"{old_log}\n{_('Награда закончилась')}")
            await query.message.edit_text(text=text, reply_markup=keyboard)
            break
        else:
            await query.answer(ex['data']['msg'])
            old_log += f"\n{ex['data']['msg']}"

            text, keyboard = await send_reward_message(tg_id, callback_data.account_id, callback_data.batch_size,
                                                       ex['data']['puzzle_left'],
                                                       f"{old_log}\n{ex['data']['msg']}")
            await query.message.edit_text(text=text, reply_markup=keyboard)
