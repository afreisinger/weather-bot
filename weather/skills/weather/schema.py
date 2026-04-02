"""
OpenClaw tool definitions for the Weather Skill.

Each entry follows the OpenAI / OpenClaw function-calling JSON Schema format.
Import ``TOOLS`` to register them with an agent.
"""

from __future__ import annotations

from typing import Any, Dict, List

TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "weather_current",
            "description": (
                "Get the current weather conditions for a given city. "
                "Returns temperature, humidity, wind speed, and a short description."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, optionally with state/country (e.g. 'London, GB').",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "weather_forecast",
            "description": (
                "Get a multi-day weather forecast for a given city. "
                "Returns daily high/low temperatures, precipitation probability, "
                "and wind speed for the requested number of days (1–8)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, optionally with state/country.",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of forecast days (1–8). Defaults to 3.",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 8,
                    },
                },
                "required": ["city"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Handler dispatcher — call from your agent runtime
# ---------------------------------------------------------------------------

async def handle_tool_call(
    name: str,
    arguments: Dict[str, Any],
) -> str:
    """
    Dispatch an OpenClaw tool call to the appropriate ``WeatherSkill`` method.

    Parameters
    ----------
    name:
        The function name from the schema (``weather_current`` or ``weather_forecast``).
    arguments:
        The parsed JSON arguments dict.

    Returns
    -------
    str
        Formatted weather text suitable for returning to the model.
    """
    # Import here to avoid circular deps when only the schema is needed.
    from weather.skills.weather.skill import WeatherSkill

    skill = WeatherSkill()

    if name == "weather_current":
        return await skill.current(city=arguments["city"])
    elif name == "weather_forecast":
        days = arguments.get("days", 3)
        return await skill.forecast(city=arguments["city"], days=days)
    else:
        raise ValueError(f"Unknown weather tool: {name}")
