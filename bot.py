import typing
from aiogram import Bot, Dispatcher
from aiogram.utils.i18n import FSMI18nMiddleware, lazy_gettext
from babel.support import LazyProxy

from settings import DEBUG
import logging

logging.basicConfig(level=logging.DEBUG)


def __(*args: typing.Any, **kwargs: typing.Any) -> LazyProxy:
    return lazy_gettext(*args, **kwargs, enable_cache=False)

if DEBUG:
    bot = debug_bot
else:
    bot = release_bot
