from aiogram import Router, F
from aiogram.dispatcher.fsm.context import FSMContext
from aiogram.dispatcher.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from commands import Commands, exit_keyboard
from settings import IS_HOME_ENABLED, IS_FREE_HOME_ENABLED, FREE_HOME_ATTEMPTS_NAME, FREE_HOME_ATTEMPTS_COUNT, \
    HOME_ATTEMPTS_LIMIT, home_collection, db, HOME_ATTEMPT_PRICE
from aiogram.utils.i18n import gettext as _

from states import BotStates

home_router = Router()


class HomeStates(StatesGroup):
    select_code = State()
    select_attempts = State()


def gen_attempts_keyboard(user: dict):
    buttons = []
    markup = ReplyKeyboardBuilder()
    for attempts_num in [25, 30]:
        markup.button(text=f'{attempts_num}')

    markup.add(*buttons)
    if IS_FREE_HOME_ENABLED and FREE_HOME_ATTEMPTS_NAME not in user:
        markup.button(text=str(Commands.FREE_ATTEMPTS.name))

    markup.button(text=Commands.EXIT.name)

    return markup.adjust(2).as_markup(resize_keyboard=True)


@home_router.message(F.text == Commands.EVENT_HOME.name, state='*')
async def home(message: Message, state: FSMContext, user: dict):
    if not IS_HOME_ENABLED:
        return await message.reply(
            _('❌ События сейчас нет в игре. \n\nАнонс о запуске узнайте на канале @letsplaycastleclash'),
            reply_markup=ReplyKeyboardBuilder().button(text=Commands.EXIT.name).as_markup(resize_keyboard=True))

    await state.set_state(BotStates.event_home)
    await home_section(message, state)


@home_router.message(state=BotStates.event_home)
async def home_section(message: Message, state: FSMContext):
    await message.reply(_(
        'Выбран раздел: <b>Возвращение Домой</b>\n\n'
        '• <a href="https://letsplaycastleclash.com/faq"><b>Ознакомьтесь с FAQ</b></a> Возвращения Домой.\n'
        '• Введите код из акции на английском языке...'),
        reply_markup=ReplyKeyboardBuilder().button(text=Commands.EXIT.name).as_markup(resize_keyboard=True),
        disable_web_page_preview=True)
    await state.set_state(HomeStates.select_code)


@home_router.message(state=HomeStates.select_code)
async def process_code(message: Message, state: FSMContext, user: dict):
    if len(message.text) != 8 or not all((x in 'ABCDEFabcdef0123456789' for x in message.text)):
        await message.reply(_(
            '❌ <b>Неверный код.</b> '
            'Правильный код состоит из 8 символов, написан на английском языке и содержит символы 0-9 и A-F, обновляется каждую акцию. '
            'Скопируйте свой код из Акции "Возвращение Домой" и введите заново:'),
            reply_markup=ReplyKeyboardBuilder().button(text=Commands.EXIT.name).as_markup(resize_keyboard=True))
        return

    code = message.text
    code = code.upper()

    await state.update_data(code=code)

    await message.reply(_(
        '''Нажмите кнопку <b>30</b>, чтобы выбрать число вводов кодов и получить Награды.'''),
        reply_markup=gen_attempts_keyboard(user))
    await state.set_state(HomeStates.select_attempts)


@home_router.message(state=HomeStates.select_attempts)
async def process_attempts(message: Message, state: FSMContext, user: dict):
    if IS_FREE_HOME_ENABLED and message.text.lower() == Commands.FREE_ATTEMPTS.name.lower():
        if FREE_HOME_ATTEMPTS_NAME in user:
            return await message.reply(
                _('На этот код уже использованы бесплатные попытки ({}/{}). '
                  'Следите за новостями на канале @letsplaycastleclash').format(
                    FREE_HOME_ATTEMPTS_COUNT,
                    FREE_HOME_ATTEMPTS_COUNT)
            )

        attempts_num = FREE_HOME_ATTEMPTS_COUNT
        is_free_attempts = True

    elif not message.text.isdigit() or len(message.text) > 4:
        return await message.reply(_('Ошибка: неверное число попыток. Введите верное число попыток'))

    else:
        attempts_num = int(message.text)
        if attempts_num > HOME_ATTEMPTS_LIMIT:
            return await message.reply(
                _(
                    '❌ Лимит попыток превышен. '
                    'Введите не более {} попыток для продолжения, или нажмите кнопку 30 попыток.'
                ).format(HOME_ATTEMPTS_LIMIT))
        is_free_attempts = False

    data = await state.get_data()
    code = data['code']

    db_code = await home_collection.find_one({'code': code})
    if db_code:
        if db_code['limit'] + attempts_num > HOME_ATTEMPTS_LIMIT:
            await message.reply(
                _('⚠ Введено слишком большое количество попыток. '
                  'Изменено на {} попыток. '
                  'По правилам Акции можно получить не больше - {} вводов.')
                    .format(HOME_ATTEMPTS_LIMIT - db_code["limit"], HOME_ATTEMPTS_LIMIT))
            attempts_num = max(0, HOME_ATTEMPTS_LIMIT - db_code["limit"])

    if is_free_attempts:
        if db_code:
            if db_code['limit'] >= HOME_ATTEMPTS_LIMIT:
                await message.reply(
                    _('На этом коде уже введено {} попыток, больше ввести нельзя по правилам Акции.').format(
                        HOME_ATTEMPTS_LIMIT),
                    reply_markup=ReplyKeyboardBuilder().button(text=Commands.EXIT.name).as_markup(resize_keyboard=True)
                )
                return

            if FREE_HOME_ATTEMPTS_NAME in db_code:
                await message.reply(
                    _('На этот код уже использованы бесплатные попытки ({}/{}). '
                      'Следите за новостями на канале @letsplaycastleclash').format(FREE_HOME_ATTEMPTS_COUNT,
                                                                                    FREE_HOME_ATTEMPTS_COUNT),
                    reply_markup=exit_keyboard
                )
                return

            await db.users.find_one_and_update(
                filter={"_id": user['_id']},
                update={"$set": {FREE_HOME_ATTEMPTS_NAME: True}})

            await home_collection.update_one({'_id': db_code['_id']},
                                             {'$inc': {'limit': attempts_num}, "$set": {FREE_HOME_ATTEMPTS_NAME: True}})

            return await message.reply(
                _('Добавляю попытки к коду... <i>(максимум {} попыток по правилам акции. '
                  'Купите  240 \`ов для получения фулл наград.)</i>').format(HOME_ATTEMPTS_LIMIT),
                reply_markup=exit_keyboard)

        else:
            await home_collection.insert_one(
                {'code': code, 'chat_id': message.chat.id, 'in_processing': 0,
                 'finished': False, 'invited_accounts': 0, 'limit': attempts_num, FREE_HOME_ATTEMPTS_NAME: True})
            await db.users.find_one_and_update(
                filter={"_id": user['_id']},
                update={"$set": {FREE_HOME_ATTEMPTS_NAME: True}})
            return await message.reply(_(
                '<code>{}</code> успешно добавлен в очередь! '
                'Вы получите уведомление, когда закончится обработка кода. <i>(максимум {} попыток по правилам акции. '
                'Купите  240 \`ов для получения фулл наград.)</i>').format(code, HOME_ATTEMPTS_LIMIT),
                                       reply_markup=gen_attempts_keyboard(user))

    already_used_attempts = 0

    if db_code:
        already_used_attempts = db_code['limit']

    left_igg_attempts = HOME_ATTEMPTS_LIMIT - already_used_attempts

    if left_igg_attempts <= 0:
        return await message.reply(_('Ваш код получил все 30 попыток, доступное по правилам Акции.'))

    coin_count = user.get("coins", 0)

    available_coin_attempts = coin_count // HOME_ATTEMPT_PRICE

    if available_coin_attempts < attempts_num:
        return await message.reply(
            _('❌ На балансе недостаточно CastleCoin\'ов: необходимо {} CastleCoin, '
              'у вас доступно {} CastleCoin\'ов').format(attempts_num * HOME_ATTEMPT_PRICE, coin_count),
            reply_markup=ReplyKeyboardBuilder()
                .button(text=str(Commands.DONATE.name))
                .button(text=Commands.EXIT.name).as_markup(resize_keyboard=True)
        )

    coin_attempts_to_use = min(left_igg_attempts, available_coin_attempts, attempts_num)
    coins_to_use = coin_attempts_to_use * HOME_ATTEMPT_PRICE

    await message.reply(
        _('✅ <code>{}</code> добавлен в очередь. Использовано {} CastleCoin\'ов ({}) попыток.')
            .format(data["code"], coins_to_use, attempts_num),
        reply_markup=exit_keyboard
    )

    await db.users.find_one_and_update(
        filter={"_id": user['_id']},
        update={"$inc": {"coins": -coins_to_use}})

    if db_code:
        await home_collection.update_one({'_id': db_code['_id']}, {'$inc': {'limit': attempts_num}})
    else:
        await home_collection.insert_one(
            {'code': code, 'chat_id': message.chat.id, 'in_processing': 0,
             'finished': False, 'invited_accounts': 0, 'limit': attempts_num})
