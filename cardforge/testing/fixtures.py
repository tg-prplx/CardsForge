"""Pytest fixtures for CardForge."""

from __future__ import annotations

import pytest

from ..app import BotApp
from ..config import CardForgeConfig


@pytest.fixture()
def memory_app() -> BotApp:
    config = CardForgeConfig(bot_token="test", storage=CardForgeConfig().storage)
    return BotApp(config)


def app_fixture(bot_token: str = "test", **kwargs) -> BotApp:
    """Helper for ad-hoc tests where pytest is not available."""
    config = CardForgeConfig(bot_token=bot_token, **kwargs)
    return BotApp(config)
