from aiogram import Router, F
from aiogram.dispatcher.fsm.context import FSMContext
from aiogram.dispatcher.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from commands import Commands, exit_keyboard
from settings import IS_TEAM_ENABLED, IS_FREE_TEAM_ENABLED, FREE_TEAM_ATTEMPTS_NAME, FREE_TEAM_ATTEMPTS_COUNT, \
    TEAM_ATTEMPTS_LIMIT, team_collection, db, TEAM_ATTEMPT_PRICE
from aiogram.utils.i18n import gettext as _

from states import BotStates

team_router = Router()


class TeamStates(StatesGroup):
    select_code = State()
    select_attempts = State()


def gen_attempts_keyboard(user: dict):
    buttons = []
    markup = ReplyKeyboardBuilder()
    for attempts_num in [1]:
        markup.button(text=f'{attempts_num}')

    markup.add(*buttons)
    if IS_FREE_TEAM_ENABLED and FREE_TEAM_ATTEMPTS_NAME not in user:
        markup.button(text=str(Commands.FREE_ATTEMPTS.name))

    markup.button(text=Commands.EXIT.name)

    return markup.adjust(2).as_markup(resize_keyboard=True)


@team_router.message(F.text == Commands.EVENT_TEAM.name, state='*')
async def team(message: Message, state: FSMContext, user: dict):
    if not IS_TEAM_ENABLED:
        return await message.reply(
            _('❌ События сейчас нет в игре. \n\nАнонс о запуске узнайте на канале @letsplaycastleclash'),
            reply_markup=ReplyKeyboardBuilder().button(text=Commands.EXIT.name).as_markup(resize_keyboard=True))

    await state.set_state(BotStates.event_team)
    await team_section(message, state)

@team_router.message(state=BotStates.event_team)
async def team_section(message: Message, state: FSMContext):
    await message.reply(_(
        'Выбран раздел: <b>Направляющая Рука</b>\n\n'
        'Как работает эвент?\n\n•  Мы предоставляем доступ ко всем наградам, доступным в акции\n•  Каждый заказ обрабатывается вручную\n•  Добавление учеников занимает время до часа\n•  Прокачка учеников в порядке очереди, награды можно забрать с первого дня "Фазы процесса"\n•  Стоимость услуги - 250 CastleCoin\n\n'
        'Если Вы ознакомились со всеми условиями, введите код из акции на английском языке...'),
        reply_markup=ReplyKeyboardBuilder().button(text=Commands.EXIT.name).as_markup(resize_keyboard=True),
        disable_web_page_preview=True)
    await state.set_state(TeamStates.select_code)


@team_router.message(state=TeamStates.select_code)
async def process_code(message: Message, state: FSMContext, user: dict):
    if len(message.text) != 8 or not all((x in 'ABCDEFabcdef0123456789' for x in message.text)):
        await message.reply(_(
            '❌ <b>Неверный код.</b> '
            'Правильный код состоит из 8 символов, написан на английском языке и содержит символы 0-9 и A-F, обновляется каждую акцию. '
            'Скопируйте свой код из Акции "Направляющая Рука" и введите заново:'),
            reply_markup=ReplyKeyboardBuilder().button(text=Commands.EXIT.name).as_markup(resize_keyboard=True))
        return

    code = message.text
    code = code.upper()

    await state.update_data(code=code)

    await message.reply(_(
        '''Нажмите кнопку <b>1</b>, чтобы получить Награды.'''),
        reply_markup=gen_attempts_keyboard(user))
    await state.set_state(TeamStates.select_attempts)


@team_router.message(state=TeamStates.select_attempts)
async def process_attempts(message: Message, state: FSMContext, user: dict):
    if IS_FREE_TEAM_ENABLED and message.text.lower() == Commands.FREE_ATTEMPTS.name.lower():
        if FREE_TEAM_ATTEMPTS_NAME in user:
            return await message.reply(
                _('На этот код уже использованы бесплатные попытки ({}/{}). '
                  'Следите за новостями на канале @letsplaycastleclash').format(
                    FREE_TEAM_ATTEMPTS_COUNT,
                    FREE_TEAM_ATTEMPTS_COUNT)
            )

        attempts_num = FREE_TEAM_ATTEMPTS_COUNT
        is_free_attempts = True

    elif not message.text.isdigit() or len(message.text) > 4:
        return await message.reply(_('Ошибка: неверное число попыток. Введите верное число попыток'))

    else:
        attempts_num = int(message.text)
        if attempts_num > TEAM_ATTEMPTS_LIMIT:
            return await message.reply(
                _(
                    '❌ Лимит попыток превышен. '
                    'Введите не более {} попыток для продолжения, или нажмите кнопку 3 попытки.'
                ).format(TEAM_ATTEMPTS_LIMIT))
        is_free_attempts = False

    data = await state.get_data()
    code = data['code']

    db_code = await team_collection.find_one({'code': code})
    if db_code:
        if db_code['limit'] + attempts_num > TEAM_ATTEMPTS_LIMIT:
            await message.reply(
                _('⚠ Введено слишком большое количество попыток. '
                  'Изменено на {} попыток. '
                  'По правилам Акции можно получить не больше - {} вводов.')
                    .format(TEAM_ATTEMPTS_LIMIT - db_code["limit"], TEAM_ATTEMPTS_LIMIT))
            attempts_num = max(0, TEAM_ATTEMPTS_LIMIT - db_code["limit"])

    if is_free_attempts:
        if db_code:
            if db_code['limit'] >= TEAM_ATTEMPTS_LIMIT:
                await message.reply(
                    _('На этом коде уже введено {} попыток, больше ввести нельзя по правилам Акции.').format(
                        TEAM_ATTEMPTS_LIMIT),
                    reply_markup=ReplyKeyboardBuilder().button(text=Commands.EXIT.name).as_markup(resize_keyboard=True)
                )
                return

            if FREE_TEAM_ATTEMPTS_NAME in db_code:
                await message.reply(
                    _('На этот код уже использованы бесплатные попытки ({}/{}). '
                      'Следите за новостями на канале @letsplaycastleclash').format(FREE_TEAM_ATTEMPTS_COUNT,
                                                                                    FREE_TEAM_ATTEMPTS_COUNT),
                    reply_markup=exit_keyboard
                )
                return

            await db.users.find_one_and_update(
                filter={"_id": user['_id']},
                update={"$set": {FREE_TEAM_ATTEMPTS_NAME: True}})

            await team_collection.update_one({'_id': db_code['_id']},
                                             {'$inc': {'limit': attempts_num}, "$set": {FREE_TEAM_ATTEMPTS_NAME: True}})

            return await message.reply(
                _('Добавляю попытки к коду... <i>(максимум {} попыток по правилам акции. '
                  'Купите 250 CastleCoin\`ов для получения фулл наград.)</i>').format(TEAM_ATTEMPTS_LIMIT),
                reply_markup=exit_keyboard)

        else:
            await team_collection.insert_one(
                {'code': code, 'chat_id': message.chat.id, 'in_processing': 0,
                 'finished': False, 'invited_accounts': 0, 'limit': attempts_num, FREE_TEAM_ATTEMPTS_NAME: True})
            await db.users.find_one_and_update(
                filter={"_id": user['_id']},
                update={"$set": {FREE_TEAM_ATTEMPTS_NAME: True}})
            return await message.reply(_(
                '<code>{}</code> успешно добавлен в очередь! '
                'Вы получите уведомление, когда закончится обработка кода. <i>(максимум {} попыток по правилам акции. '
                'Купите 250 CastleCoin\`ов для получения фулл наград.)</i>').format(code, TEAM_ATTEMPTS_LIMIT),
                                       reply_markup=gen_attempts_keyboard(user))

    already_used_attempts = 0

    if db_code:
        already_used_attempts = db_code['limit']

    left_igg_attempts = TEAM_ATTEMPTS_LIMIT - already_used_attempts

    if left_igg_attempts <= 0:
        return await message.reply(_('Ваш код получил все 3 попытки, доступные по правилам Акции.'))

    coin_count = user.get("coins", 0)

    available_coin_attempts = coin_count // TEAM_ATTEMPT_PRICE

    if available_coin_attempts < attempts_num:
        return await message.reply(
            _('❌ На балансе недостаточно CastleCoin\'ов: необходимо {} CastleCoin, '
              'у вас доступно {} CastleCoin\'ов').format(attempts_num * TEAM_ATTEMPT_PRICE, coin_count),
            reply_markup=ReplyKeyboardBuilder()
                .button(text=str(Commands.DONATE.name))
                .button(text=Commands.EXIT.name).as_markup(resize_keyboard=True)
        )

    coin_attempts_to_use = min(left_igg_attempts, available_coin_attempts, attempts_num)
    coins_to_use = coin_attempts_to_use * TEAM_ATTEMPT_PRICE

    await message.reply(
        _('✅ <code>{}</code> добавлен в очередь. Использовано {} CastleCoin\'ов ({}) попыток.')
            .format(data["code"], coins_to_use, attempts_num),
        reply_markup=exit_keyboard
    )

    await db.users.find_one_and_update(
        filter={"_id": user['_id']},
        update={"$inc": {"coins": -coins_to_use}})

    if db_code:
        await team_collection.update_one({'_id': db_code['_id']}, {'$inc': {'limit': attempts_num}})
    else:
        await team_collection.insert_one(
            {'code': code, 'chat_id': message.chat.id, 'in_processing': 0,
             'finished': False, 'invited_accounts': 0, 'limit': attempts_num})
