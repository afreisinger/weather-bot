"""Human-readable formatting of OpenWeather API responses."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

MAX_TELEGRAM_LEN = 4000

# Severity keyword → emoji (best-effort matching on alert event names)
_ALERT_EMOJI: dict[str, str] = {
    "thunderstorm": "⛈️",
    "tornado":      "🌪️",
    "hurricane":    "🌀",
    "cyclone":      "🌀",
    "flood":        "🌊",
    "rain":         "🌧️",
    "snow":         "❄️",
    "ice":          "🧊",
    "wind":         "💨",
    "fog":          "🌫️",
    "heat":         "🔥",
    "fire":         "🔥",
    "dust":         "🏜️",
    "extreme":      "⚠️",
}


def _alert_emoji(event: str) -> str:
    low = event.lower()
    for keyword, emoji in _ALERT_EMOJI.items():
        if keyword in low:
            return emoji
    return "⚠️"


def _fmt_time(ts: int, offset: int = 0) -> str:
    """Format a UNIX timestamp as HH:MM (local offset applied)."""
    dt = datetime.fromtimestamp(ts + offset, tz=timezone.utc)
    return dt.strftime("%H:%M")


def _fmt_date(ts: int, offset: int = 0) -> str:
    """Format a UNIX timestamp as a short weekday + date."""
    dt = datetime.fromtimestamp(ts + offset, tz=timezone.utc)
    return dt.strftime("%a %d %b")


def _unit_symbol(units: str) -> str:
    return {"metric": "°C", "imperial": "°F", "standard": "K"}.get(units, "°C")


# ---------------------------------------------------------------------------
# Current weather
# ---------------------------------------------------------------------------

def format_current(data: Dict[str, Any], name: str, country: str, units: str = "metric") -> str:
    """Build a pretty string for current weather conditions."""
    c = data["current"]
    offset = data.get("timezone_offset", 0)
    sym = _unit_symbol(units)

    lines = [
        f"🌤  {name}, {country}",
        f"{c['weather'][0]['description'].title()}",
        f"🌡  Temp: {c['temp']}{sym}  (feels like {c['feels_like']}{sym})",
        f"💧 Humidity: {c['humidity']}%",
        f"💨 Wind: {c['wind_speed']} m/s",
        f"🕒 Local time: {_fmt_time(c['dt'], offset)}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Daily forecast
# ---------------------------------------------------------------------------

def format_forecast(
    data: Dict[str, Any],
    name: str,
    country: str,
    days: int = 3,
    units: str = "metric",
) -> str:
    """Build a pretty multi-day forecast string."""
    offset = data.get("timezone_offset", 0)
    daily = data.get("daily", [])[:days]
    sym = _unit_symbol(units)

    header = f"📅 {days}-day forecast for {name}, {country}\n"
    blocks: list[str] = []
    for day in daily:
        date_str = _fmt_date(day["dt"], offset)
        desc = day["weather"][0]["description"].title()
        t_min = day["temp"]["min"]
        t_max = day["temp"]["max"]
        humidity = day["humidity"]
        wind = day.get("wind_speed", "?")
        pop = int(day.get("pop", 0) * 100)  # probability of precipitation %
        blocks.append(
            f"  {date_str}: {desc}\n"
            f"    🌡 {t_min}{sym} / {t_max}{sym}  💧 {humidity}%  💨 {wind} m/s  🌧 {pop}%"
        )
    return header + "\n".join(blocks)


# ---------------------------------------------------------------------------
# Hourly forecast
# ---------------------------------------------------------------------------

def format_hourly(
    data: Dict[str, Any],
    name: str,
    country: str,
    hours: int = 12,
    units: str = "metric",
) -> str:
    """
    Build a compact hour-by-hour forecast string.

    OneCall returns up to 48 hourly entries; we surface the first *hours*.
    Each row: local time · description · temperature · precip % · wind.
    """
    offset = data.get("timezone_offset", 0)
    hourly = data.get("hourly", [])[:hours]
    sym = _unit_symbol(units)

    header = f"🕐 {hours}h forecast for {name}, {country}\n"
    rows: list[str] = []
    for h in hourly:
        time_str = _fmt_time(h["dt"], offset)
        desc     = h["weather"][0]["description"].title()
        temp     = h["temp"]
        pop      = int(h.get("pop", 0) * 100)
        wind     = h.get("wind_speed", "?")
        precip   = ""
        if "rain" in h:
            precip = f"  🌧 {h['rain'].get('1h', 0):.1f}mm"
        elif "snow" in h:
            precip = f"  ❄️ {h['snow'].get('1h', 0):.1f}mm"
        rows.append(
            f"  {time_str}  {desc:<22} {temp}{sym}  💨 {wind} m/s  🌂 {pop}%{precip}"
        )
    return header + "\n".join(rows)


# ---------------------------------------------------------------------------
# Weather alerts
# ---------------------------------------------------------------------------

# def format_alerts(
#     data: Dict[str, Any],
#     name: str,
#     country: str,
# ) -> str:
#     """
#     Build a formatted string for active weather alerts.

#     Returns a calm 'no alerts' message when the list is empty.
#     """
#     alerts = data.get("alerts", [])
#     if not alerts:
#         return f"✅ No active weather alerts for {name}, {country}."

#     offset = data.get("timezone_offset", 0)
#     header = f"🚨 Active alerts for {name}, {country} — {len(alerts)} alert(s)\n"
#     blocks: list[str] = []
#     messages: List[str] = [header]
#     for i, alert in enumerate(alerts, 1):
#         event   = alert.get("event", "Unknown event")
#         sender  = alert.get("sender_name", "Unknown source")
#         start   = _fmt_time(alert["start"], offset) if "start" in alert else "?"
#         end     = _fmt_time(alert["end"],   offset) if "end"   in alert else "?"
        
#         # desc_raw = alert.get("description", "").strip()
#         # desc = (desc_raw[:280] + "…") if len(desc_raw) > 280 else desc_raw
#         desc = alert.get("description", "").strip()
#         emoji = _alert_emoji(event)
#         block = (
#             f"{emoji} [{i}] {event}\n"
#             f"   📡 Source : {sender}\n"
#             f"   🕒 Period : {start} → {end}\n"
#             f"   📝 {desc}"
#         )

#         if len(block) > MAX_TELEGRAM_LEN:
#             for j in range(0, len(block), MAX_TELEGRAM_LEN):
#                 messages.append(block[j:j+MAX_TELEGRAM_LEN])
#         else:
#             messages.append(block)

#     return messages

def format_alerts(
    data: Dict[str, Any],
    name: str,
    country: str,
) -> list[str]:
    """
    Build a formatted string for active weather alerts.

    Returns a calm 'no alerts' message as a list when empty.
    """
    alerts = data.get("alerts", [])
    if not alerts:
        return [f"✅ No active weather alerts for {name}, {country}."]

    offset = data.get("timezone_offset", 0)
    header = f"🚨 Active alerts for {name}, {country} — {len(alerts)} alert(s)\n"
    messages: list[str] = [header]

    for i, alert in enumerate(alerts, 1):
        event   = alert.get("event", "Unknown event")
        sender  = alert.get("sender_name", "Unknown source")
        start   = _fmt_time(alert["start"], offset) if "start" in alert else "?"
        end     = _fmt_time(alert["end"],   offset) if "end"   in alert else "?"
        desc    = alert.get("description", "").strip()
        emoji   = _alert_emoji(event)

        block = (
            f"{emoji} [{i}] {event}\n"
            f"   📡 Source : {sender}\n"
            f"   🕒 Period : {start} → {end}\n"
            f"   📝 {desc}"
        )

        # dividir si excede límite Telegram
        if len(block) > MAX_TELEGRAM_LEN:
            for j in range(0, len(block), MAX_TELEGRAM_LEN):
                messages.append(block[j:j+MAX_TELEGRAM_LEN])
        else:
            messages.append(block)

    return messages