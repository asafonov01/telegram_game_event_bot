from aiogram import Router, F
from aiogram.dispatcher.fsm.context import FSMContext
from aiogram.types import Message

from commands import exit_keyboard, Commands
from settings import trader_collection, TRADER_ACCOUNT_IGG_ID, TRADER_ACCOUNT_TOKEN
from aiogram.utils.i18n import gettext as _

from states import BotStates
from event_apis.trader_api import CCTraderApi

trader_router = Router()


@trader_router.message(F.text == Commands.EVENT_TRADER.name)
async def trader_section(message: Message, state: FSMContext):
    await message.reply(
        _('Выбран раздел: <b>Великий Торговец</b>\n\n'
          '• <a href="https://letsplaycastleclash.com/faq"><b>Ознакомьтесь с FAQ</b></a> Великого Торговца.\n'
          '• Отправьте код предмета, чтобы снизить цену'),
        reply_markup=exit_keyboard,
        disable_web_page_preview=True)
    await state.set_state(BotStates.event_trader_select_code)


@trader_router.message(state=BotStates.event_trader_select_code)
async def trader_code_receiver(message: Message):
    if len(message.text) != 8 or not all((x.isdigit() or x.isalpha() for x in message.text)):
        await message.reply(
            _('❌ Ошибка: неверный код. Скопируйте код предмета из Акции "Великий Торговец" и введите заново:'),
            reply_markup=exit_keyboard)
        return

    code = message.text

    if await trader_collection.find_one({'code': code}):
        await message.reply(_('⚠ Код уже в очереди.'))
        return

    api = CCTraderApi(TRADER_ACCOUNT_TOKEN, TRADER_ACCOUNT_IGG_ID)
    view = await api.view(code)
    if 'data' not in view or 'iggid' not in view['data']:
        return await message.reply(_('❌ <b>Неверный код.</b> Пожалуйста, отправьте код из Великого Торговца...'),
                                   reply_markup=exit_keyboard)

    friend_id = int(view['data']['iggid'])
    item_id = int(view['data']['item']['ap_id'])

    await message.reply(_('✅ Код {} добавлен в очередь.').format(code), reply_markup=exit_keyboard)

    await trader_collection.insert_one(
        {'code': code, 'friend_id': friend_id,
         'item_id': item_id, 'chat_id': message.chat.id,
         'in_processing': False,
         'finished': False, 'used_attempts': 0})
