"""
Tests for the OpenWeather API client.

Run:
    python -m pytest tests/test_client.py -v
"""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from weather.skills.weather.client import (
    WeatherAPIError,
    GeocodingError,
    _validate_api_key,
    _cache_get,
    _cache_set,
    cache_clear,
    geocode,
    onecall,
    _fetch,
    API_KEY,
    CACHE_TTL,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_env_api_key():
    """Set up a mock API key in environment."""
    with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "test-api-key-123"}, clear=True):
        yield


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    return session


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------

class TestCache:
    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        cache_clear()  # Start with clean cache
        
        # Test setting and getting a value
        _cache_set("test_key", "test_value")
        result = _cache_get("test_key")
        assert result == "test_value"
    
    def test_cache_miss_returns_none(self):
        """Test cache miss returns None."""
        cache_clear()
        result = _cache_get("non_existent_key")
        assert result is None
    
    def test_cache_expiration(self, monkeypatch):
        """Test cache expiration after TTL."""
        cache_clear()
        
        # Mock time.monotonic to control time
        mock_time = 1000.0
        monkeypatch.setattr("weather.skills.weather.client.time.monotonic", lambda: mock_time)
        
        _cache_set("test_key", "test_value")
        
        # Should still be in cache
        assert _cache_get("test_key") == "test_value"
        
        # Simulate time passing beyond TTL
        monkeypatch.setattr("weather.skills.weather.client.time.monotonic", lambda: mock_time + CACHE_TTL + 1)
        
        # Should be expired
        assert _cache_get("test_key") is None
    
    def test_cache_clear(self):
        """Test clearing the entire cache."""
        _cache_set("key1", "value1")
        _cache_set("key2", "value2")
        
        assert _cache_get("key1") == "value1"
        assert _cache_get("key2") == "value2"
        
        cache_clear()
        
        assert _cache_get("key1") is None
        assert _cache_get("key2") is None


# ---------------------------------------------------------------------------
# API key validation tests
# ---------------------------------------------------------------------------

class TestAPIKeyValidation:
    def test_validate_api_key_with_key(self, mock_env_api_key):
        """Test API key validation when key is present."""
        # Should not raise
        _validate_api_key()
    
    def test_validate_api_key_without_key(self):
        """Test API key validation when key is missing."""
        with patch("weather.skills.weather.client.API_KEY", ""):
            with pytest.raises(EnvironmentError, match="OPENWEATHER_API_KEY is not set"):
                _validate_api_key()
    
    def test_validate_api_key_empty_string(self):
        """Test API key validation when key is empty string."""
        with patch("weather.skills.weather.client.API_KEY", ""):
            with pytest.raises(EnvironmentError, match="OPENWEATHER_API_KEY is not set"):
                _validate_api_key()


# ---------------------------------------------------------------------------
# Fetch tests
# ---------------------------------------------------------------------------

class TestFetch:
    @pytest.mark.asyncio
    async def test_fetch_cache_hit(self, mock_env_api_key):
        """Test fetch returns cached result when available."""
        test_url = "https://api.openweathermap.org/test"
        test_data = {"test": "data"}
        
        # Set cache
        _cache_set(test_url, test_data)
        
        # Mock aiohttp to ensure no HTTP request is made
        with patch("weather.skills.weather.client.aiohttp.ClientSession") as MockSession:
            # Should return cached data without making HTTP request
            result = await _fetch(test_url)
            assert result == test_data
            MockSession.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_fetch_invalid_url(self, mock_env_api_key):
        """Test fetch rejects non-OpenWeather URLs."""
        invalid_url = "https://evil.com/api"
        
        with pytest.raises(ValueError, match="Refusing to request non-OpenWeather URL"):
            await _fetch(invalid_url)


# ---------------------------------------------------------------------------
# Geocode tests
# ---------------------------------------------------------------------------

class TestGeocode:
    @pytest.mark.asyncio
    async def test_geocode_success(self, mock_env_api_key):
        """Test successful geocoding."""
        test_city = "Buenos Aires"
        mock_data = [{
            "lat": -34.61,
            "lon": -58.38,
            "name": "Buenos Aires",
            "country": "AR"
        }]
        
        with patch("weather.skills.weather.client._fetch", new_callable=AsyncMock, return_value=mock_data):
            result = await geocode(test_city)
            
            assert result == (-34.61, -58.38, "Buenos Aires", "AR")
    
    @pytest.mark.asyncio
    async def test_geocode_no_results(self, mock_env_api_key):
        """Test geocoding with no results raises GeocodingError."""
        test_city = "Nonexistent City"
        
        with patch("weather.skills.weather.client._fetch", new_callable=AsyncMock, return_value=[]):
            with pytest.raises(GeocodingError, match="Location not found"):
                await geocode(test_city)
    
    @pytest.mark.asyncio
    async def test_geocode_with_session(self, mock_env_api_key):
        """Test geocoding with provided session."""
        test_city = "London"
        mock_data = [{
            "lat": 51.51,
            "lon": -0.13,
            "name": "London",
            "country": "GB"
        }]
        
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        
        with patch("weather.skills.weather.client._fetch", new_callable=AsyncMock, return_value=mock_data) as mock_fetch:
            result = await geocode(test_city, session=mock_session)
            
            assert result == (51.51, -0.13, "London", "GB")
            mock_fetch.assert_called_once()
            # Check that session was passed to _fetch
            assert mock_fetch.call_args[1]["session"] == mock_session


# ---------------------------------------------------------------------------
# OneCall tests
# ---------------------------------------------------------------------------

class TestOneCall:
    @pytest.mark.asyncio
    async def test_onecall_success(self, mock_env_api_key):
        """Test successful onecall API request."""
        lat, lon = -34.61, -58.38
        units = "metric"
        exclude = "minutely"
        mock_data = {"current": {"temp": 22.5}}
        
        with patch("weather.skills.weather.client._fetch", new_callable=AsyncMock, return_value=mock_data):
            result = await onecall(lat, lon, units=units, exclude=exclude)
            
            assert result == mock_data
    
    @pytest.mark.asyncio
    async def test_onecall_invalid_units(self, mock_env_api_key):
        """Test onecall with invalid units raises ValueError."""
        lat, lon = -34.61, -58.38
        
        with pytest.raises(ValueError, match="Invalid units"):
            await onecall(lat, lon, units="invalid")
    
    @pytest.mark.asyncio
    async def test_onecall_with_session(self, mock_env_api_key):
        """Test onecall with provided session."""
        lat, lon = -34.61, -58.38
        mock_data = {"current": {"temp": 22.5}}
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        
        with patch("weather.skills.weather.client._fetch", new_callable=AsyncMock, return_value=mock_data) as mock_fetch:
            result = await onecall(lat, lon, session=mock_session)
            
            assert result == mock_data
            mock_fetch.assert_called_once()
            # Check that session was passed to _fetch
            assert mock_fetch.call_args[1]["session"] == mock_session
    
    @pytest.mark.asyncio
    async def test_onecall_allowed_units(self, mock_env_api_key):
        """Test onecall with all allowed units."""
        lat, lon = -34.61, -58.38
        mock_data = {"current": {"temp": 22.5}}
        
        allowed_units = ["metric", "imperial", "standard"]
        
        for units in allowed_units:
            with patch("weather.skills.weather.client._fetch", new_callable=AsyncMock, return_value=mock_data):
                result = await onecall(lat, lon, units=units)
                assert result == mock_data