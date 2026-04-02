"""
Telegram bot entrypoint.

Usage:
    python -m weather.bot.main
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from colorama import Fore, Style, init


from aiogram import Bot, Dispatcher, Router
from weather.bot.handlers import register_handlers
from weather.core.logging import logger


def _get_token() -> str:
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    if not token:
        logger.critical("TELEGRAM_TOKEN is not set — aborting")
        sys.exit(1)
    return token


async def main() -> None:
    bot = Bot(token=_get_token())
    dp = Dispatcher()

    # Create a router and register weather handlers
    router = Router(name="weather")
    register_handlers(router)
    dp.include_router(router)

    logger.info("Bot starting…  Press Ctrl+C to stop.")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
