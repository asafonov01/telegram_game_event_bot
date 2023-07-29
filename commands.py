from dataclasses import dataclass

from aiogram.types import InlineKeyboardButton
from aiogram.utils.i18n import lazy_gettext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from babel.support import LazyProxy
import typing


def __(*args: typing.Any, **kwargs: typing.Any) -> LazyProxy:
    return lazy_gettext(*args, **kwargs, enable_cache=False)


@dataclass
class CallbackMenuItem:
    name: LazyProxy or str
    callback_data: str

    def to_button(self, payload: str = ''):
        return InlineKeyboardButton(text=str(self.name), callback_data=payload or self.callback_data)

    def to_filter(self):
        return lambda c: c.data and c.data == self.callback_data


class Commands:
    EVENT_PUZZLES = CallbackMenuItem(__("Загадочный Пазл"), 'event_puzzle')
    EVENT_TRADER = CallbackMenuItem(__("Великий Торговец"), 'event_trader')

    EVENT_HOME = CallbackMenuItem(__("Возвращение Домой"), 'event_home')
    EVENT_THANKSGIVING = CallbackMenuItem(__("10 Дней Призов"), 'event_thanksgiving')
    EVENT_TEAM = CallbackMenuItem(__("Направляющая Рука"), 'event_team')
    VOLUNTARY_DONATION = CallbackMenuItem(__("Добровольное пожертвование"), 'voluntary_donation')

    DONATE = CallbackMenuItem(__("Купить CastleCoin"), 'donate')
    EXIT = CallbackMenuItem("«", 'exit')
    FREE_ATTEMPTS = CallbackMenuItem(__("Использовать бесплатные попытки"), 'use_free_attempts')
    CHANGE_LANGUAGE = CallbackMenuItem(__("Сменить язык 🇬🇧/🇷🇺"), 'change_language')

    DELETE_LINK = CallbackMenuItem(__('Удалить свою ссылку'), 'delete_link')


exit_keyboard = ReplyKeyboardBuilder().button(text=Commands.EXIT.name).as_markup(resize_keyboard=True)
