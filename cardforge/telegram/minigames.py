"""Telegram-specific helpers for CardForge mini-games."""

from __future__ import annotations

from aiogram.types import Message

from ..app import BotApp
from ..domain.player import PlayerProfile


class TelegramMiniGameContext:
    """Implements MiniGameContext over Telegram message interactions."""

    def __init__(self, app: BotApp, message: Message, *, user_id: int, username: str | None):
        self._app = app
        self._message = message
        self.user_id = user_id
        self.username = username

    async def send_message(self, text: str) -> None:
        await self._message.answer(text)

    async def award_currency(self, currency: str, amount: int) -> PlayerProfile:
        profile = await self._app.player_service.credit(self.user_id, currency, amount)
        return profile

    async def spend_currency(self, currency: str, amount: int) -> PlayerProfile:
        profile = await self._app.player_service.spend(self.user_id, currency, amount)
        return profile

    async def grant_card(self, card_id: str, quantity: int = 1) -> PlayerProfile:
        profile = await self._app.player_service.add_card(self.user_id, card_id, quantity)
        return profile

    async def grant_experience(self, amount: int) -> PlayerProfile:
        profile = await self._app.player_service.grant_experience(self.user_id, amount)
        return profile

    async def get_profile(self) -> PlayerProfile:
        return await self._app.player_service.fetch(self.user_id)

    async def send_dice(self, emoji: str = "🎲") -> Message:
        """Send a dice with the given emoji and return the Telegram message."""
        return await self._message.answer_dice(emoji=emoji)

    async def roll_dice(self, emoji: str = "🎲") -> int:
        """Send a dice and return its rolled value (0 if unavailable)."""
        message = await self.send_dice(emoji=emoji)
        return message.dice.value if message.dice else 0
