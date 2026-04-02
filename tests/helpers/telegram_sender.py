"""
Standalone Telegram message sender (no bot framework required).

Uses only ``aiohttp`` + stdlib.  Includes logging, retry, and env-var config.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE: str = "https://api.telegram.org"
MAX_RETRIES: int = 3
RETRY_BACKOFF: float = 1.0  # seconds; doubles each attempt


def _get_config() -> tuple[str, str]:
    """Return ``(bot_token, chat_id)`` or raise if not configured."""
    bot_token = os.environ.get("TELEGRAM_API_KEY_WEATHER", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID_WEATHER", "").strip()
    if not bot_token:
        raise EnvironmentError("TELEGRAM_API_KEY_WEATHER is not set")
    if not chat_id:
        raise EnvironmentError("TELEGRAM_CHAT_ID_WEATHER is not set")
    return bot_token, chat_id


async def send_telegram_message(
    text: str,
    *,
    parse_mode: Optional[str] = None,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Send *text* to a Telegram chat.

    Parameters
    ----------
    text:
        The message body.
    parse_mode:
        Optional Telegram parse mode (``HTML``, ``MarkdownV2``).
    bot_token / chat_id:
        Override env-var values for testing.

    Returns
    -------
    dict | None
        The Telegram API response on success, ``None`` on failure.
    """
    if bot_token is None or chat_id is None:
        _token, _chat = _get_config()
        bot_token = bot_token or _token
        chat_id = chat_id or _chat

    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    payload: Dict[str, Any] = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    logger.debug("Sending Telegram message → chat_id=%s", chat_id)

    last_exc: Optional[Exception] = None
    async with aiohttp.ClientSession() as session:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    body = await resp.text()
                    parsed = json.loads(body)
                    if not parsed.get("ok"):
                        logger.error("Telegram API error: %s", parsed)
                        return parsed
                    logger.info("Message sent successfully to Telegram")
                    return parsed
            except Exception as exc:
                last_exc = exc
                wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                logger.warning(
                    "Telegram attempt %d/%d failed (%s), retrying in %.1fs…",
                    attempt, MAX_RETRIES, exc, wait,
                )
                await asyncio.sleep(wait)

    logger.exception("Failed to send Telegram message after %d retries", MAX_RETRIES, exc_info=last_exc)
    return None


# ---------------------------------------------------------------------------
# Synchronous convenience wrapper (for scripts that are not already async)
# ---------------------------------------------------------------------------

def send_telegram_message_sync(text: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """Blocking wrapper around :func:`send_telegram_message`."""
    return asyncio.run(send_telegram_message(text, **kwargs))
