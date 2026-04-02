"""OpenWeather API client — async, zero side-effects, retry-capable."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_KEY: str = os.environ.get("OPENWEATHER_API_KEY", "").strip()
BASE_URL: str = "https://api.openweathermap.org"
ALLOWED_UNITS = frozenset({"imperial", "metric", "standard"})
DEFAULT_TIMEOUT_SECS: int = 12
USER_AGENT: str = "openclaw-openweather-skill/1.0 (+https://openweathermap.org/)"
MAX_RETRIES: int = 3
RETRY_BACKOFF: float = 1.0  # seconds, doubles each retry

# ---------------------------------------------------------------------------
# Simple in-memory cache  (key → (timestamp, value))
# ---------------------------------------------------------------------------

_cache: Dict[str, Tuple[float, Any]] = {}
CACHE_TTL: int = 300  # 5 minutes


def _cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry is None:
        return None
    ts, value = entry
    if time.monotonic() - ts > CACHE_TTL:
        del _cache[key]
        return None
    return value


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (time.monotonic(), value)


def cache_clear() -> None:
    """Flush the entire in-memory cache."""
    _cache.clear()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class WeatherAPIError(Exception):
    """Raised when the OpenWeather API returns an error."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(f"API error {status}: {message}")


class GeocodingError(Exception):
    """Raised when a city cannot be geocoded."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_api_key() -> None:
    if not API_KEY:
        raise EnvironmentError(
            "OPENWEATHER_API_KEY is not set. "
            "Export it as an environment variable before running."
        )


async def _fetch(url: str, *, session: Optional[aiohttp.ClientSession] = None) -> Any:
    """
    GET *url* with retries and optional session reuse.

    Only OpenWeather HTTPS endpoints are allowed.
    """
    if not (
        url.startswith("https://api.openweathermap.org/")
        or url.startswith("https://openweathermap.org/")
    ):
        raise ValueError("Refusing to request non-OpenWeather URL")

    _validate_api_key()

    cached = _cache_get(url)
    if cached is not None:
        logger.debug("Cache hit: %s", url)
        return cached

    headers = {"User-Agent": USER_AGENT}
    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()

    last_exc: Optional[Exception] = None
    try:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug("GET %s  (attempt %d/%d)", url, attempt, MAX_RETRIES)
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT_SECS)
                ) as resp:
                    body = await resp.text()
                    # ───────── Log rate limit ─────────
                    remaining = resp.headers.get("X-RateLimit-Remaining")
                    limit = resp.headers.get("X-RateLimit-Limit")
                    if remaining is not None and limit is not None:
                        logger.info("OpenWeather API calls remaining: %s/%s", remaining, limit)
                    # ──────────────────────────────────
                    if resp.status >= 400:
                        try:
                            msg = json.loads(body).get("message", body)
                        except Exception:
                            msg = body
                        raise WeatherAPIError(resp.status, msg)
                    data = json.loads(body)
                    _cache_set(url, data)
                    return data
            except WeatherAPIError:
                raise  # don't retry client errors (4xx)
            except Exception as exc:
                last_exc = exc
                wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                logger.warning("Attempt %d failed (%s), retrying in %.1fs…", attempt, exc, wait)
                await asyncio.sleep(wait)
        raise last_exc  # type: ignore[misc]
    finally:
        if own_session:
            await session.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def geocode(
    city: str,
    *,
    session: Optional[aiohttp.ClientSession] = None,
) -> Tuple[float, float, str, str]:
    """
    Resolve *city* to ``(lat, lon, name, country)`` via OpenWeather Geocoding.
    """
    encoded = urllib.parse.quote(city)
    url = f"{BASE_URL}/geo/1.0/direct?q={encoded}&limit=1&appid={API_KEY}"
    results: List[Dict[str, Any]] = await _fetch(url, session=session)
    if not results:
        raise GeocodingError(
            f"Location not found: '{city}'. "
            "Try a more specific name, e.g. 'Springfield, IL, US'."
        )
    r = results[0]
    return r["lat"], r["lon"], r.get("name", city), r.get("country", "")


async def onecall(
    lat: float,
    lon: float,
    units: str = "metric",
    exclude: str = "",
    *,
    session: Optional[aiohttp.ClientSession] = None,
) -> Dict[str, Any]:
    """
    Fetch data from OneCall 3.0 for the given coordinates.
    """
    if units not in ALLOWED_UNITS:
        raise ValueError(f"Invalid units '{units}'. Must be one of {ALLOWED_UNITS}")
    url = (
        f"{BASE_URL}/data/3.0/onecall"
        f"?lat={lat}&lon={lon}&units={units}&exclude={exclude}&appid={API_KEY}"
    )
    return await _fetch(url, session=session)
