from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

from cardforge.telegram.api_utils import safe_api_call


class DummyForbidden(TelegramForbiddenError):
    def __init__(self) -> None:
        Exception.__init__(self, "forbidden")


class DummyRetryAfter(TelegramRetryAfter):
    def __init__(self, retry_after: float) -> None:
        Exception.__init__(self, f"retry after {retry_after}")
        self.retry_after = retry_after


@pytest.mark.asyncio()
async def test_safe_api_call_returns_result():
    async def ok() -> int:
        return 42

    result = await safe_api_call("test", ok)
    assert result == 42


@pytest.mark.asyncio()
async def test_safe_api_call_handles_forbidden():
    async def forbidden() -> None:
        raise DummyForbidden()

    result = await safe_api_call("forbidden", forbidden)
    assert result is None


@pytest.mark.asyncio()
async def test_safe_api_call_retries_on_retry_after(monkeypatch):
    mock_call = AsyncMock(side_effect=[DummyRetryAfter(0.0), 7])

    async def fake_sleep(delay: float) -> None:
        assert delay >= 0.0

    monkeypatch.setattr("cardforge.telegram.api_utils.asyncio.sleep", fake_sleep)

    result = await safe_api_call("retry", mock_call, retries=2)
    assert result == 7
    assert mock_call.await_count == 2
