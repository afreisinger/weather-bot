"""
Tests for the WeatherSkill — fully mocked, no network required.

Run:
    python -m pytest weather/tests/test_weather.py -v
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from weather.skills.weather.client import GeocodingError, WeatherAPIError
from weather.skills.weather.formatters import format_current, format_forecast, format_hourly, format_alerts, _alert_emoji
from weather.skills.weather import WeatherSkill

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

MOCK_GEOCODE = (34.61, -58.38, "Buenos Aires", "AR")

MOCK_ONECALL_CURRENT = {
    "timezone_offset": -10800,
    "current": {
        "dt": 1700000000,
        "temp": 22.5,
        "feels_like": 21.0,
        "humidity": 60,
        "wind_speed": 3.5,
        "weather": [{"description": "clear sky"}],
    },
}

MOCK_ONECALL_FORECAST = {
    "timezone_offset": -10800,
    "current": MOCK_ONECALL_CURRENT["current"],
    "daily": [
        {
            "dt": 1700000000 + 86400 * i,
            "temp": {"min": 15.0 + i, "max": 25.0 + i},
            "humidity": 55 + i,
            "wind_speed": 2.0 + i,
            "pop": 0.1 * i,
            "weather": [{"description": "few clouds"}],
        }
        for i in range(8)
    ],
}

MOCK_ONECALL_HOURLY = {
    "timezone_offset": -10800,
    "hourly": [
        {
            "dt": 1700000000 + 3600 * i,
            "temp": 20 + i,
            "humidity": 60,
            "wind_speed": 3.0,
            "weather": [{"description": "clear sky"}],
        }
        for i in range(24)
    ],
}

MOCK_ONECALL_ALERTS = {
    "alerts": [
        {
            "event": "Storm Warning",
            "description": "Heavy rain expected",
        }
    ]
}

# ---------------------------------------------------------------------------
# Formatter unit tests
# ---------------------------------------------------------------------------

class TestFormatters:
    def test_format_current_contains_city(self):
        text = format_current(MOCK_ONECALL_CURRENT, "Buenos Aires", "AR")
        assert "Buenos Aires" in text
        assert "AR" in text
        assert "22.5" in text

    def test_format_forecast_respects_days(self):
        text = format_forecast(MOCK_ONECALL_FORECAST, "Test", "XX", days=2)
        assert "2-day forecast" in text
        # Should contain exactly 2 day blocks
        lines_with_temp = [l for l in text.splitlines() if "🌡" in l]
        assert len(lines_with_temp) == 2

    def test_format_forecast_clamps_days(self):
        # Requesting more days than available still works (just returns fewer)
        text = format_forecast(MOCK_ONECALL_FORECAST, "City", "CC", days=20)
        # data has 8 entries, so we get at most 8
        lines_with_temp = [l for l in text.splitlines() if "🌡" in l]
        assert len(lines_with_temp) <= 8

    def test_format_hourly_with_precipitation(self):
        """Test hourly formatting with rain and snow data."""
        hourly_data_with_rain = {
            "timezone_offset": -10800,
            "hourly": [
                {
                    "dt": 1700000000,
                    "temp": 20.0,
                    "humidity": 60,
                    "wind_speed": 3.0,
                    "weather": [{"description": "light rain"}],
                    "rain": {"1h": 1.5},
                    "pop": 0.8
                },
                {
                    "dt": 1700003600,
                    "temp": 19.5,
                    "humidity": 65,
                    "wind_speed": 2.5,
                    "weather": [{"description": "light snow"}],
                    "snow": {"1h": 0.5},
                    "pop": 0.6
                }
            ]
        }
        
        text = format_hourly(hourly_data_with_rain, "Test City", "TC", hours=2)
        assert "Test City" in text
        assert "Light Rain" in text  # Changed from "light rain"
        assert "Light Snow" in text  # Changed from "light snow"
        # Check for precipitation indicators
        assert "🌧" in text or "❄️" in text

    def test_alert_emoji_matching(self):
        """Test alert emoji matching logic."""
        # Test known keywords
        assert _alert_emoji("Thunderstorm Warning") == "⛈️"
        assert _alert_emoji("Tornado Alert") == "🌪️"
        assert _alert_emoji("Hurricane Advisory") == "🌀"
        assert _alert_emoji("Flood Watch") == "🌊"
        assert _alert_emoji("Heavy Rain") == "🌧️"
        assert _alert_emoji("Snow Storm") == "❄️"
        assert _alert_emoji("Ice Storm") == "🧊"
        assert _alert_emoji("High Wind") == "💨"
        assert _alert_emoji("Dense Fog") == "🌫️"
        assert _alert_emoji("Heat Wave") == "🔥"
        assert _alert_emoji("Wildfire") == "🔥"
        assert _alert_emoji("Dust Storm") == "🏜️"
        assert _alert_emoji("Extreme Cold") == "⚠️"
        
        # Test unknown keyword returns default
        assert _alert_emoji("Unknown Alert") == "⚠️"

    def test_format_alerts_long_message(self):
        """Test alert formatting with long messages that need splitting."""
        from weather.skills.weather.formatters import MAX_TELEGRAM_LEN
        
        # Create a very long description
        long_description = "A" * (MAX_TELEGRAM_LEN + 100)
        
        alerts_data = {
            "timezone_offset": -10800,
            "alerts": [
                {
                    "event": "Test Alert",
                    "sender_name": "Test Source",
                    "start": 1700000000,
                    "end": 1700086400,
                    "description": long_description
                }
            ]
        }
        
        result = format_alerts(alerts_data, "Test City", "TC")
        
        # Should return multiple strings due to splitting
        assert isinstance(result, list)
        assert len(result) > 1
        
        # Check that total content is preserved
        total_length = sum(len(msg) for msg in result)
        assert total_length >= len(long_description)


# ---------------------------------------------------------------------------
# Skill integration tests (mocked network)
# ---------------------------------------------------------------------------

class TestWeatherSkill:
    @pytest.mark.asyncio
    async def test_current_returns_string(self):
        with (
            patch("weather.skills.weather.skill.geocode", new_callable=AsyncMock, return_value=MOCK_GEOCODE),
            patch("weather.skills.weather.skill.onecall", new_callable=AsyncMock, return_value=MOCK_ONECALL_CURRENT),
        ):
            skill = WeatherSkill()
            result = await skill.current("Buenos Aires")
            assert isinstance(result, str)
            assert "Buenos Aires" in result

    @pytest.mark.asyncio
    async def test_forecast_returns_string(self):
        with (
            patch("weather.skills.weather.skill.geocode", new_callable=AsyncMock, return_value=MOCK_GEOCODE),
            patch("weather.skills.weather.skill.onecall", new_callable=AsyncMock, return_value=MOCK_ONECALL_FORECAST),
        ):
            skill = WeatherSkill()
            result = await skill.forecast("Buenos Aires", days=5)
            assert isinstance(result, str)
            assert "5-day forecast" in result

    @pytest.mark.asyncio
    async def test_current_defaults_to_configured_city(self):
        with (
            patch("weather.skills.weather.skill.geocode", new_callable=AsyncMock, return_value=MOCK_GEOCODE) as mock_geo,
            patch("weather.skills.weather.skill.onecall", new_callable=AsyncMock, return_value=MOCK_ONECALL_CURRENT),
        ):
            skill = WeatherSkill(default_city="Rosario")
            await skill.current()
            mock_geo.assert_awaited_once()
            assert mock_geo.call_args[0][0] == "Rosario"

    @pytest.mark.asyncio
    async def test_geocoding_error_propagates(self):
        with patch(
            "weather.skills.weather.skill.geocode",
            new_callable=AsyncMock,
            side_effect=GeocodingError("Not found"),
        ):
            skill = WeatherSkill()
            with pytest.raises(GeocodingError):
                await skill.current("Nonexistentville")

    @pytest.mark.asyncio
    async def test_skill_help_method(self):
        """Test the help method returns a string with command information."""
        skill = WeatherSkill()
        help_text = await skill.help()
        
        assert isinstance(help_text, str)
        assert "WeatherSkill — Available Commands" in help_text
        assert "/current" in help_text
        assert "/forecast" in help_text
        assert "/forecast_hourly" in help_text
        assert "/alerts" in help_text


# ---------------------------------------------------------------------------
# Schema handler tests
# ---------------------------------------------------------------------------

class TestSchemaHandler:
    @pytest.mark.asyncio
    async def test_weather_current_handler(self):
        from weather.skills.weather.schema import handle_tool_call

        with (
            patch("weather.skills.weather.skill.geocode", new_callable=AsyncMock, return_value=MOCK_GEOCODE),
            patch("weather.skills.weather.skill.onecall", new_callable=AsyncMock, return_value=MOCK_ONECALL_CURRENT),
        ):
            result = await handle_tool_call("weather_current", {"city": "Buenos Aires"})
            assert "Buenos Aires" in result

    @pytest.mark.asyncio
    async def test_weather_forecast_handler(self):
        from weather.skills.weather.schema import handle_tool_call

        with (
            patch("weather.skills.weather.skill.geocode", new_callable=AsyncMock, return_value=MOCK_GEOCODE),
            patch("weather.skills.weather.skill.onecall", new_callable=AsyncMock, return_value=MOCK_ONECALL_FORECAST),
        ):
            result = await handle_tool_call("weather_forecast", {"city": "Test", "days": 2})
            assert "2-day forecast" in result

    @pytest.mark.asyncio
    async def test_unknown_tool_raises(self):
        from weather.skills.weather.schema import handle_tool_call

        with pytest.raises(ValueError, match="Unknown weather tool"):
            await handle_tool_call("weather_magic", {"city": "X"})

    @pytest.mark.asyncio
    async def test_hourly_returns_string(self):
        with (
            patch("weather.skills.weather.skill.geocode", new_callable=AsyncMock, return_value=MOCK_GEOCODE),
            patch("weather.skills.weather.skill.onecall", new_callable=AsyncMock, return_value=MOCK_ONECALL_HOURLY),
        ):
            skill = WeatherSkill()
            result = await skill.forecast_hourly("Buenos Aires", hours=5)

            assert isinstance(result, str)
            assert "Buenos Aires" in result

    @pytest.mark.asyncio
    async def test_alerts_with_data(self):
        with (
            patch("weather.skills.weather.skill.geocode", new_callable=AsyncMock, return_value=MOCK_GEOCODE),
            patch("weather.skills.weather.skill.onecall", new_callable=AsyncMock, return_value=MOCK_ONECALL_ALERTS),
        ):
            skill = WeatherSkill()
            result = await skill.alerts("Buenos Aires")

            # Validar tipo
            assert isinstance(result, list)
            assert all(isinstance(r, str) for r in result)

            # Validar que hay alertas activas
            assert any("alert" in r.lower() or "tormentas" in r.lower() for r in result)

    @pytest.mark.asyncio
    async def test_alerts_empty(self):
        with (
            patch("weather.skills.weather.skill.geocode", new_callable=AsyncMock, return_value=MOCK_GEOCODE),
            patch("weather.skills.weather.skill.onecall", new_callable=AsyncMock, return_value={"alerts": []}),
        ):
            skill = WeatherSkill()
            result = await skill.alerts("Buenos Aires")

            # Validar tipo
            assert isinstance(result, list)
            assert all(isinstance(r, str) for r in result)

            # Validar que el mensaje de "no alertas" está presente
            assert any("no active weather alerts" in r.lower() for r in result)
    
    @pytest.mark.asyncio
    async def test_hourly_clamps_hours(self):
        with (
            patch("weather.skills.weather.skill.geocode", new_callable=AsyncMock, return_value=MOCK_GEOCODE),
            patch("weather.skills.weather.skill.onecall", new_callable=AsyncMock, return_value=MOCK_ONECALL_HOURLY),
        ):
            skill = WeatherSkill()
            result = await skill.forecast_hourly("Buenos Aires", hours=100)

            assert isinstance(result, str)