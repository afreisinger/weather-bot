"""
Tests for the Telegram sender utility.

Run:
    python -m pytest weather/tests/test_telegram.py -v
"""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.helpers.telegram_sender import send_telegram_message, send_telegram_message_sync


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(ok: bool = True) -> MagicMock:
    """Create a fake aiohttp response context manager."""
    body = json.dumps({"ok": ok, "result": {"message_id": 42}})
    resp = AsyncMock()
    resp.text = AsyncMock(return_value=body)
    resp.status = 200
    return resp


def _make_error_response() -> MagicMock:
    """Create a fake aiohttp response with error."""
    body = json.dumps({"ok": False, "description": "Bad Request: chat not found"})
    resp = AsyncMock()
    resp.text = AsyncMock(return_value=body)
    resp.status = 400
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSendTelegramMessage:
    @pytest.mark.asyncio
    async def test_successful_send(self):
        fake_resp = _make_response(ok=True)

        with patch("tests.helpers.telegram_sender.aiohttp.ClientSession") as MockSession:
            session_instance = MagicMock()
            MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            
            mock_post_ctx = AsyncMock()
            mock_post_ctx.__aenter__.return_value = fake_resp
            mock_post_ctx.__aexit__.return_value = False

            session_instance.post.return_value = mock_post_ctx

            result = await send_telegram_message(
                "Hello, test!",
                bot_token="fake-token",
                chat_id="8585050505",
            )
            assert result is not None
            assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_missing_env_raises(self):
        """Without explicit tokens and missing env vars, it should raise."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(EnvironmentError, match="TELEGRAM_API_KEY_WEATHER"):
                await send_telegram_message("boom")

    @pytest.mark.asyncio
    async def test_missing_chat_id_env_raises(self):
        """Test missing chat ID environment variable raises error."""
        with patch.dict("os.environ", {"TELEGRAM_API_KEY_WEATHER": "test-token"}, clear=True):
            with pytest.raises(EnvironmentError, match="TELEGRAM_CHAT_ID_WEATHER"):
                await send_telegram_message("test")

    @pytest.mark.asyncio
    async def test_api_error_returns_response(self):
        fake_resp = _make_response(ok=False)

        with patch("tests.helpers.telegram_sender.aiohttp.ClientSession") as MockSession:
            session_instance = MagicMock()
            MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            
            mock_post_ctx = AsyncMock()
            mock_post_ctx.__aenter__.return_value = fake_resp
            mock_post_ctx.__aexit__.return_value = False

            session_instance.post.return_value = mock_post_ctx

            result = await send_telegram_message(
                "fail",
                bot_token="tok",
                chat_id="1",
            )
            # Should still return the parsed body, not None
            assert result is not None
            assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_send_with_parse_mode(self):
        """Test sending message with parse mode."""
        fake_resp = _make_response(ok=True)

        with patch("tests.helpers.telegram_sender.aiohttp.ClientSession") as MockSession:
            session_instance = MagicMock()
            MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            
            mock_post_ctx = AsyncMock()
            mock_post_ctx.__aenter__.return_value = fake_resp
            mock_post_ctx.__aexit__.return_value = False

            session_instance.post.return_value = mock_post_ctx

            result = await send_telegram_message(
                "Hello, **test**!",
                bot_token="fake-token",
                chat_id="8585050505",
                parse_mode="MarkdownV2",
            )
            assert result is not None
            assert result["ok"] is True
            
            # Check that parse_mode was included in payload
            call_args = session_instance.post.call_args
            assert call_args is not None
            json_payload = call_args[1]["json"]
            assert json_payload["parse_mode"] == "MarkdownV2"

    @pytest.mark.asyncio
    async def test_retry_on_exception(self):
        """Test retry mechanism when requests fail."""
        fake_resp = _make_response(ok=True)

        with patch("tests.helpers.telegram_sender.aiohttp.ClientSession") as MockSession:
            session_instance = MagicMock()
            MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            
            mock_post_ctx = AsyncMock()
            mock_post_ctx.__aenter__.return_value = fake_resp
            mock_post_ctx.__aexit__.return_value = False

            # First call raises exception, second succeeds
            session_instance.post.side_effect = [
                Exception("Network error"),
                mock_post_ctx
            ]

            result = await send_telegram_message(
                "Hello after retry!",
                bot_token="fake-token",
                chat_id="8585050505",
            )
            assert result is not None
            assert result["ok"] is True
            assert session_instance.post.call_count == 2

    @pytest.mark.asyncio
    async def test_all_retries_fail(self):
        """Test when all retry attempts fail."""
        with patch("tests.helpers.telegram_sender.aiohttp.ClientSession") as MockSession:
            session_instance = MagicMock()
            MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            
            # All calls raise exceptions
            session_instance.post.side_effect = Exception("Persistent network error")

            result = await send_telegram_message(
                "This will fail",
                bot_token="fake-token",
                chat_id="8585050505",
            )
            # Should return None after all retries fail
            assert result is None

    @pytest.mark.asyncio
    async def test_uses_env_vars_when_no_explicit_tokens(self):
        """Test that function uses environment variables when tokens not provided."""
        fake_resp = _make_response(ok=True)

        with (
            patch.dict(
                "os.environ",
                {
                    "TELEGRAM_API_KEY_WEATHER": "env-token",
                    "TELEGRAM_CHAT_ID_WEATHER": "env-chat-id"
                },
                clear=True
            ),
            patch("tests.helpers.telegram_sender.aiohttp.ClientSession") as MockSession
        ):
            session_instance = MagicMock()
            MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            
            mock_post_ctx = AsyncMock()
            mock_post_ctx.__aenter__.return_value = fake_resp
            mock_post_ctx.__aexit__.return_value = False

            session_instance.post.return_value = mock_post_ctx

            result = await send_telegram_message("Hello from env!")
            assert result is not None
            assert result["ok"] is True

    def test_send_telegram_message_sync(self):
        """Test the synchronous wrapper function."""
        fake_resp = _make_response(ok=True)

        with patch("tests.helpers.telegram_sender.aiohttp.ClientSession") as MockSession:
            session_instance = MagicMock()
            MockSession.return_value.__aenter__ = AsyncMock(return_value=session_instance)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
            
            mock_post_ctx = AsyncMock()
            mock_post_ctx.__aenter__.return_value = fake_resp
            mock_post_ctx.__aexit__.return_value = False

            session_instance.post.return_value = mock_post_ctx

            result = send_telegram_message_sync(
                "Hello, sync test!",
                bot_token="fake-token",
                chat_id="8585050505",
            )
            assert result is not None
            assert result["ok"] is True
