"""
CLI interface for the Weather Skill.

Usage:
    python -m weather.cli.weather_cli current "Buenos Aires"
    python -m weather.cli.weather_cli forecast "Córdoba" --days 5
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from weather.skills.weather.skill import WeatherSkill


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weather",
        description="Query current weather or multi-day forecasts from the terminal.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # --- current --------------------------------------------------------
    p_cur = sub.add_parser("current", help="Show current weather for a city.")
    p_cur.add_argument("city", help="City name, e.g. 'London' or 'Springfield, IL, US'.")

    # --- forecast -------------------------------------------------------
    p_fc = sub.add_parser("forecast", help="Show multi-day forecast for a city.")
    p_fc.add_argument("city", help="City name.")
    p_fc.add_argument(
        "--days", "-d",
        type=int,
        default=3,
        help="Number of forecast days (1–8, default 3).",
    )

    return parser


async def _run(args: argparse.Namespace) -> None:
    skill = WeatherSkill()
    if args.command == "current":
        print(await skill.current(args.city))
    elif args.command == "forecast":
        print(await skill.forecast(args.city, days=args.days))


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )

    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
