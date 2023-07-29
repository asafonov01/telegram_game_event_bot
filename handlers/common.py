import typing
from dataclasses import dataclass
from datetime import datetime

from aiogram import Router, F, html
from aiogram.dispatcher.filters.callback_data import CallbackData
from aiogram.dispatcher.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, CallbackQuery, InlineKeyboardButton
from aiogram.utils.i18n import lazy_gettext
from aiogram.utils.keyboard import KeyboardBuilder, ReplyKeyboardBuilder, InlineKeyboardBuilder
from babel.support import LazyProxy
from aiogram.utils.i18n import gettext as _

from commands import Commands, exit_keyboard
from settings import i18n_middleware, db
from states import BotStates


class LanguageCallback(CallbackData, prefix='lang'):
    lang: str


common_router = Router()


@common_router.message(F.text == Commands.CHANGE_LANGUAGE.name)
async def lang(message: Message):
    await message.answer(_('Выбери язык бота'),
                         reply_markup=InlineKeyboardBuilder()
                         .button(text='🇬🇧 English', callback_data=LanguageCallback(lang='en'))
                         .button(text='🇷🇺 Русский', callback_data=LanguageCallback(lang='ru'))
                         .button(text='🇺🇦 Українська', callback_data=LanguageCallback(lang='uk'))

                         .button(text='🇫🇷 Français', callback_data=LanguageCallback(lang='fr'))
                         .button(text='🇩🇪 Deutsche', callback_data=LanguageCallback(lang='de'))
                         .button(text='🇪🇸 Español', callback_data=LanguageCallback(lang='es'))
                         .button(text='🇦🇪 عربي', callback_data=LanguageCallback(lang='ar'))

                         .button(text='🇮🇹 Italiano', callback_data=LanguageCallback(lang='it'))
                         .button(text='🇹🇷 Türkçe', callback_data=LanguageCallback(lang='tr'))
                         .button(text='🇧🇾 Беларуская', callback_data=LanguageCallback(lang='be'))
                         .button(text='🇮🇩 Indonésie', callback_data=LanguageCallback(lang='id'))
                         .button(text='🇧🇷 Português (BR)', callback_data=LanguageCallback(lang='pt'))
                         .button(text='🇻🇳 Tiếng Việt', callback_data=LanguageCallback(lang='vi'))

                         .adjust(3)
                         .as_markup(),
                         )


@common_router.callback_query(LanguageCallback.filter(), state='*')
async def change_lang(query: CallbackQuery, state: FSMContext, callback_data: LanguageCallback, user):
    await i18n_middleware.set_locale(state, callback_data.lang)

    await start(query.message, state, user)

    await query.message.delete()
    await query.answer()


@common_router.callback_query(F.data == Commands.EXIT.callback_data, state='*')
async def go_to_main_menu(query: CallbackQuery, state: FSMContext, user):
    await state.set_state(None)
    await start(query.message, state, user)


@common_router.message(commands=['start', 'help'])
@common_router.message(F.text == Commands.EXIT.name)
async def start(message: Message, state: FSMContext, user):
    limits_string = ''

    puzzle_ranks = user['ranks'].get('1') or []

    total_puzzle_attempts = 0

    for rank in puzzle_ranks:
        if rank['id'] == 3 and rank['expires'] > datetime.now():
            total_puzzle_attempts += 30

    available_puzzle_attempts = total_puzzle_attempts
    if 'used_attempts' in user and 'puzzle' in user['used_attempts']:
        available_puzzle_attempts -= user['used_attempts']['puzzle']

    limits_string += _('{} / {} пазлов\n').format(max(0, available_puzzle_attempts), total_puzzle_attempts)

    await state.set_state(None)

    result_text = _(
        "<b>Здравствуйте</b>, <a href='tg://user?id={}'>{}</a>.\nВаш Telegram ID: <code>{}</code>\n\n<b>На балансе у Вас:</b>\n{} CastleCoin'ов\n") \
        .format(message.chat.id, html.quote(message.chat.first_name), message.chat.id, user.get('coins') or 0)
    if limits_string != '':
        result_text += limits_string
    result_text += _('\n• @CCletsplay_bot — <b>связь с технической поддержкой.</b>'
                     '\n• @letsplaycastleclash — <b>новостной канал об акциях и конкурсах.</b>'
                     '\n• letsplaycastleclash.com — <b>сайт проекта.</b>')

    inline_kb_full = ReplyKeyboardBuilder().button(text=str(Commands.EVENT_PUZZLES.name)).button(
        text=str(Commands.EVENT_TRADER.name)) \
        .button(text=str(Commands.EVENT_TEAM.name)).button(text=str(Commands.EVENT_THANKSGIVING.name)) \
        .button(text=str(Commands.DONATE.name)).button(text=str(Commands.CHANGE_LANGUAGE.name)).adjust(2)

    await message.answer(result_text, reply_markup=inline_kb_full.as_markup(resize_keyboard=True))


def gen_donate_keyboard(user_lang):
    markup = ReplyKeyboardBuilder()

    for price in [10, 50, 100, 150, 200, 300, 500, 1000]:
        markup.button(text=_('{} CastleCoin - {} руб').format(price, price if user_lang == 'ru' else price // 2 ))

    markup.button(text=Commands.EXIT.name)

    return markup.adjust(2).as_markup(resize_keyboard=True)


@common_router.message(F.text == Commands.DONATE.name)
async def donate(message: Message, state: FSMContext):
    user_lang = (await db.aiogram_data.find_one({'chat': message.from_user.id}))['data'].get('locale') or 'ru'
    if user_lang in ['ru', 'uk']:
        await state.set_state(BotStates.donate)
        await message.reply(_('Выбран раздел: <b>Купить CastleCoin</b> \n\n'
                              '<b>Курс:</b>\n'
                              '• 1 CastleCoin = ₽1\n'
                              '• 160 CastleCoin = €2\n'
                              '• 10 CastleCoin = ₴5\n'
                              '• 100 CastleCoin = ₴50\n'
                              '• 1 CastleCoin = <a href="https://google.com/search?q=1+тенге+в+руб">мониторинг ₸</a>\n'
                              '• 1 CastleCoin = <a href="https://google.com/search?q=1+BYN+в+руб"> маніторынг BYN</a>\n\n'
                              'Пожалуйста, ознакомьтесь с прейскурантом событий letsplaycastleclash.com/#price'),

                            reply_markup=gen_donate_keyboard(user_lang), disable_web_page_preview=True)
    else:
        await message.reply(_('''
Если у Вас не получается купить CastleCoin'ы на сайте, предлагаем следующие варианты для самостоятельного перевода:

• Сбербанк: <code>4276380220016518</code>
• Tinkoff: <code>5536913939647661</code>
• ВТБ: <code>2200240467204455</code>
• Альфа: <code>5559492516306829</code>
• Monobank (Украина): <code>4441114425412671</code>
• Международный перевод через бота <b>[все страны]</b> <a href="https://t.me/letsplaycastleclash/3251"><b>@donate</b></a>

❗После оплаты с помощью самостоятельного перевода, <b>обязательно</b> пришлите чек в поддержку: @CCletsplay_bot с указанием времени проведения платежа, иначе CastleCoin'ы <b>не</b> будут зачислены на счёт.'''
), reply_markup=exit_keyboard, disable_web_page_preview=True)


@common_router.message(state=BotStates.donate)
async def donate(message: Message, state: FSMContext, user: dict):
    coin_count = message.text.split(' ', maxsplit=1)[0]
    if not coin_count.isdigit() or len(coin_count) > 5:
        await message.reply(_('Неверная цена. Введи верную цену!'), reply_markup=gen_donate_keyboard())
        return
    coin_count = int(coin_count)
    user_lang = (await db.aiogram_data.find_one({'chat': message.from_user.id}))['data'].get('locale') or 'ru'

    if not 2 <= coin_count <= 14999:
        return await message.reply(_('Слишком большая или маленькая цена. Введи верную цену!'),
                                   reply_markup=gen_donate_keyboard(user_lang))

    text = _('''<b>Выбрано {} CastleCoin'ов за {} рублей</b>.

<a href="https://letsplaycastleclash.com/payment?tg_id={}&count={}"><b>Оплатить можно по ссылке на сайте (только для пользователей РФ и Украины)</b></a>.

• Monobank (Украина): <code>4441114425412671</code>
Если у Вас не получается купить CastleCoin'ы на сайте, уточняйте реквизиты для оплаты в чате поддержки: @CCletsplay_bot. После оплаты Вам начислится баланс.'''
             ).format(coin_count, coin_count if user_lang != 'uk' else coin_count // 2, message.chat.id, coin_count)
    await message.reply(text, reply_markup=exit_keyboard, disable_web_page_preview=True)
