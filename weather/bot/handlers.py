"""
Telegram command handlers for the Weather Skill.

Follows the ``register_handlers(router)`` pattern so the bot entrypoint
stays minimal and handler files stay self-contained.
"""

from __future__ import annotations

import logging

from aiogram import Router, types
from aiogram.filters import Command

from weather.skills.weather.skill import WeatherSkill

logger = logging.getLogger(__name__)

# One skill instance shared across all handlers in this module.
_skill = WeatherSkill()


def register_handlers(router: Router) -> None:
    """Attach all weather-related handlers to *router*."""

    @router.message(Command("weather"))
    async def cmd_weather(message: types.Message) -> None:
        """
        /weather         → current weather for the default city
        /weather <city>  → current weather for <city>
        """
        raw = (message.text or "").replace("/weather", "", 1).strip()
        # Support "/weather forecast <city> <days>"
        if raw.lower().startswith("forecast"):
            await _handle_forecast(message, raw)
            return
        if raw.lower().startswith("forecast_hourly"):
            await _handle_forecast_hourly(message, raw)
            return
        
        city = raw or None
        
        try:
            result = await _skill.current(city)
            await message.answer(result)
        except Exception as exc:
            logger.exception("Error in /weather handler")
            await message.answer(f"⚠️ Could not fetch weather: {exc}")

    @router.message(Command("forecast"))
    async def cmd_forecast(message: types.Message) -> None:
        """
        /forecast              → 3-day default city
        /forecast <city>       → 3-day for <city>
        /forecast <city> <n>   → n-day for <city>
        """
        raw = (message.text or "").replace("/forecast", "", 1).strip()
        await _handle_forecast(message, raw)

    @router.message(Command("forecast_hourly"))
    async def cmd_forecast_hourly(message: types.Message) -> None:
        """
        /forecast_hourly              → 12-hour default city
        /forecast_hourly <city>       → 12-hour for <city>
        /forecast_hourly <city> <n>   → n-hour for <city>
        """
        raw = (message.text or "").replace("/forecast_hourly", "", 1).strip()
        await _handle_forecast_hourly(message, raw)

    @router.message(Command("alerts"))
    async def cmd_alerts(message: types.Message) -> None:
        """
        /alerts         → alerts for default city
        /alerts <city>  → alerts for <city>
        """
        raw = (message.text or "").replace("/alerts", "", 1).strip()
        city = raw or None

        try:
            alert_messages = await _skill.alerts(city)  # ahora devuelve List[str]
            for msg in alert_messages:
                await message.answer(msg)
        except Exception as exc:
            logger.exception("Error in alerts handler")
            await message.answer(f"⚠️ Could not fetch alerts: {exc}")

    @router.message(Command("help"))
    async def cmd_help(message: types.Message) -> None:
        """
        /help → show this help text
        """
        try:
            result = await _skill.help()  # llama al método async help() de WeatherSkill
            await message.answer(result)
        except Exception as exc:
            logger.exception("Error in help handler")
            await message.answer(f"⚠️ Could not fetch help: {exc}")


async def _handle_forecast(message: types.Message, raw: str) -> None:
    """Common logic for parsing a forecast request from text."""
    parts = raw.split()
    # Try to pull a trailing integer as 'days'
    days = 3
    city_parts = parts
    if parts and parts[-1].isdigit():
        days = int(parts[-1])
        city_parts = parts[:-1]
    # Drop leading "forecast" keyword if present
    if city_parts and city_parts[0].lower() == "forecast":
        city_parts = city_parts[1:]
    city = " ".join(city_parts) or None
    try:
        result = await _skill.forecast(city, days=days)
        await message.answer(result)
    except Exception as exc:
        logger.exception("Error in forecast handler")
        await message.answer(f"⚠️ Could not fetch forecast: {exc}")

async def _handle_forecast_hourly(message: types.Message, raw: str) -> None:
    """Common logic for parsing an hourly forecast request from text."""
    parts = raw.split()

    hours = 12
    city_parts = parts

    # Detectar si el último argumento es número (hours)
    if parts and parts[-1].isdigit():
        hours = int(parts[-1])
        city_parts = parts[:-1]

    # Soporte para "/weather forecast_hourly ..."
    if city_parts and city_parts[0].lower() == "forecast_hourly":
        city_parts = city_parts[1:]

    city = " ".join(city_parts) or None

    try:
        result = await _skill.forecast_hourly(city, hours=hours)
        await message.answer(result)
    except Exception as exc:
        logger.exception("Error in hourly forecast handler")
        await message.answer(f"⚠️ Could not fetch hourly forecast: {exc}")

