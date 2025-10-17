"""Reusable aiogram filters for CardForge bots."""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from ..config import CardForgeConfig
from ..domain.inventory import InventoryService


class AdminFilter(BaseFilter):
    def __init__(self, config: CardForgeConfig) -> None:
        self._admins = set(config.admin.admin_ids)

    async def __call__(self, message: Message) -> bool:
        user = message.from_user
        return bool(user and user.id in self._admins)


class NotBannedFilter(BaseFilter):
    def __init__(self, inventory: InventoryService) -> None:
        self._inventory = inventory

    async def __call__(self, message: Message) -> bool:
        user = message.from_user
        if not user:
            return False
        return not await self._inventory.is_banned(user.id)


class DropCooldownFilter(BaseFilter):
    """Filter that provides remaining cooldown if active."""

    def __init__(self, inventory: InventoryService) -> None:
        self._inventory = inventory

    async def __call__(self, message: Message) -> dict | bool:
        user = message.from_user
        if not user:
            return False
        remaining = await self._inventory.cooldown_remaining(user.id)
        if remaining > 0:
            return {"cooldown": remaining}
        return {}
