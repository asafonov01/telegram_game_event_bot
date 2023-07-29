from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.dispatcher.filters.callback_data import CallbackData
from aiogram.dispatcher.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from pymongo import ReturnDocument

from commands import exit_keyboard, Commands
from settings import thanksgiving_collection, tokens_collection
from aiogram.utils.i18n import gettext as _

from states import BotStates
from event_apis.thanksgiving_api import ThanksgivingManager

thanksgiving_router = Router()


class RemoveLinkCallback(CallbackData, prefix='remove_lik'):
    igg_id: int


@thanksgiving_router.message(F.text == Commands.EVENT_THANKSGIVING.name)
async def trader_section(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardBuilder() \
        .button(text=str(Commands.DELETE_LINK.name)) \
        .button(text=Commands.EXIT.name).as_markup(resize_keyboard=True, one_time_keyboard=True)

    await message.reply(
        _('Выбран раздел: <b>10 дней призов</b> \n\n'
          '❓Как получить ссылку\n\n'
          'Android: перейдите к уведомлению о глобальном клиенте, нажмите. Вас перебросит в браузер, нужно скопировать ссылку от туда и добавить в бота в раздел "10 дней призов".\n'
          'iOS: https://t.me/letsplaycastleclash/3556\n'
          '• Вас перенаправит на страницу браузера. Из строки скопируйте ссылку >> отправьте ссылку боту.'),
        reply_markup=keyboard, disable_web_page_preview=True),
    await state.set_state(BotStates.event_thanksgiving_select_account_data)


@thanksgiving_router.message(F.text == Commands.DELETE_LINK.name)
async def delete_link(message: Message, state: FSMContext):
    user_links = [link['uid'] async for link in tokens_collection.find({'tg_id': message.from_user.id})]
    keyboard = InlineKeyboardBuilder()

    for igg_id in user_links:
        keyboard.button(text=_('Удалить данные с IGG ID {}').format(igg_id), callback_data=RemoveLinkCallback(igg_id=igg_id).pack())
    keyboard.button(text=Commands.EXIT.name, callback_data=Commands.EXIT.callback_data)
    keyboard = keyboard.adjust(1).as_markup(resize_keyboard=True)

    if user_links:
        await message.reply(
            _('Выберите, какие данные нужно удалить:'),
            reply_markup=keyboard,
        )
    else:
        await message.reply(
            _('Вы еще не добавили ни одной ссылки в бота'),
            reply_markup=exit_keyboard,
        )

    await state.set_state(BotStates.event_thanksgiving_select_account_data)


@thanksgiving_router.callback_query(RemoveLinkCallback.filter(), state='*')
async def delete_link(query: CallbackQuery, state: FSMContext, callback_data: RemoveLinkCallback, user):
    await query.message.reply(
            _('Вы успешно удалили ссылку с IGG ID: {}').format(callback_data.igg_id),
            reply_markup=exit_keyboard,
        )
    await tokens_collection.delete_one({'tg_id': query.from_user.id, 'uid': callback_data.igg_id})
    await query.answer()


@thanksgiving_router.message(state=BotStates.event_thanksgiving_select_account_data)
async def thanksgiving_account_receiver(message: Message, state: FSMContext, user: dict):
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

    thg_m = ThanksgivingManager()

    try:
        report = await thg_m.load_account_info(sign, uid)
    except Exception as e:
        await message.reply(
            _('❌ <b>Неверная ссылка</b> \n\n'
              '<b>Возможные причины:</b>\n'
              '— Signed_key недоступен для использования. Пожалуйста, возьмите новую ссылку из игры.'
              '— Ссылка не содержит знаки: <b>& =</b> \n'
              '— В ссылке есть пробел. Проверьте, чтобы было без пробела.\n'
              '— Отсутствует <b>signed_key</b> или <b>uid</b>.'),
            reply_markup=exit_keyboard)

    cd_finish = datetime.now() + timedelta(seconds=report.cd_time / 1000)
    link = await tokens_collection.find_one_and_update(
        {"uid": uid},
        {"$set": {
            'tg_id': message.from_user.id,
            'sign': sign,
        }},
        upsert=True,
        return_document=ReturnDocument.AFTER)

    await thanksgiving_collection.insert_one(
        {
            'account_id': link['_id'],
            'cd_time': cd_finish,
            'last_id': report.last_id
        }
    )

    await message.reply(
        _('✅ <b>Ссылка добавлена.</b>\n\n'
          '‼️ Политика конфиденциальности: letsplaycastleclash.com/policy'),
        disable_web_page_preview=True, reply_markup=exit_keyboard)
