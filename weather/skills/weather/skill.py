"""WeatherSkill — the reusable, async, transport-agnostic core."""

from __future__ import annotations

import logging
from typing import Optional

import aiohttp

from weather.core.config import settings
from weather.skills.weather.client import geocode, onecall
from weather.skills.weather.formatters import format_current, format_forecast, format_hourly, format_alerts


logger = logging.getLogger(__name__)

# DEFAULT_CITY: str = "Buenos Aires"
# DEFAULT_UNITS: str = "metric"
# DEFAULT_FORECAST_DAYS: int = 3
# DEFAULT_FORECAST_HOURS: int = 12


class WeatherSkill:
    """
    High-level weather operations.

    Can optionally share a single ``aiohttp.ClientSession`` for connection
    pooling when used inside a long-running process (bot, server).
    """

    def __init__(
        self,
        *,
        # default_city: str = DEFAULT_CITY,
        # units: str = DEFAULT_UNITS,
        # session: Optional[aiohttp.ClientSession] = None,
        default_city: Optional[str] = None,
        units: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        # self._default_city = default_city
        # self._units = units
        # self._session = session
        self._default_city = default_city or settings.default_city
        self._units = units or settings.units
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def current(self, city: Optional[str] = None) -> str:
        """Return a formatted current-weather string for *city*."""
        city = city or self._default_city
        logger.info("Fetching current weather for '%s'", city)
        lat, lon, name, country = await geocode(city, session=self._session)
        data = await onecall(
            lat, lon,
            units=self._units,
            exclude="minutely,hourly,daily,alerts",
            session=self._session,
        )
        return format_current(data, name, country, units=self._units)

    async def forecast(self, city: Optional[str] = None, days: Optional[int] = None) -> str:
        """Return a formatted multi-day forecast string for *city*."""
        city = city or self._default_city
        days = days or settings.forecast_days
        days = max(1, min(days, 8))  # OneCall provides up to 8 days
        logger.info("Fetching %d-day forecast for '%s'", days, city)
        lat, lon, name, country = await geocode(city, session=self._session)
        data = await onecall(
            lat, lon,
            units=self._units,
            exclude="minutely,hourly,alerts",
            session=self._session,
        )
        return format_forecast(data, name, country, days=days, units=self._units)

    
    async def forecast_hourly(self, city: Optional[str] = None, hours: Optional[int] = None) -> str:
        """Return a formatted hourly forecast string for *city*."""
        city = city or self._default_city
        hours = hours or settings.forecast_hours
        hours = max(1, min(hours, 48))  # OpenWeather da hasta 48 horas    
        logger.info("Fetching %d-hour forecast for '%s'", hours, city)
        lat, lon, name, country = await geocode(city, session=self._session)
        data = await onecall(
            lat, lon,
            units=self._units,
            exclude="minutely,alerts",  # 👈 importante
            session=self._session,
        )
        return format_hourly(data,name, country, hours=hours, units=self._units)
    

    async def alerts(self, city: Optional[str] = None) -> str:
        """Return weather alerts for *city*."""
        city = city or self._default_city
        logger.info("Fetching alerts for '%s'", city)
        lat, lon, name, country = await geocode(city, session=self._session)
        data = await onecall(
            lat, lon,
            units=self._units,
            exclude="hourly,daily",
            session=self._session,
        )
        return format_alerts(data, name, country)
    
    async def help(self) -> str:
        """
        Return a help string listing all available commands and their parameters.
        """
        return (
            "🌤 WeatherSkill — Available Commands:\n\n"
            "1. /current <city>\n"
            "   - Get current weather for a city.\n"
            f"   - Default city: {self._default_city}\n\n"
            "2. /forecast <city> [days]\n"
            "   - Get multi-day forecast (1–8 days).\n"
            f"   - Default city: {self._default_city}, Default days: {settings.forecast_days}\n\n"
            "3. /forecast_hourly <city> [hours]\n"
            "   - Get hourly forecast (1–48 hours).\n"
            f"   - Default city: {self._default_city}, Default hours: {settings.forecast_hours}\n\n"
            "4. /alerts <city>\n"
            "   - Get current weather alerts.\n"
            f"   - Default city: {self._default_city}\n\n"
            "ℹ️ You can omit <city> to use the default."
        )