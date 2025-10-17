"""Player-centric utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .cards import CardCatalog
from .economy import Wallet
from .exceptions import InsufficientCurrency, NoCardsAvailable
from ..storage.base import PlayerRecord, PlayerStore


@dataclass(slots=True)
class PlayerProfile:
    user_id: int
    username: str | None
    inventory: Mapping[str, int]
    wallet: Mapping[str, int]
    experience: int
    is_banned: bool


class PlayerService:
    """Expose read/write operations for player state."""

    def __init__(self, store: PlayerStore, *, catalog: CardCatalog | None = None) -> None:
        self._store = store
        self._catalog = catalog

    def attach_catalog(self, catalog: CardCatalog) -> None:
        """Attach a catalog post-instantiation (useful for tests)."""
        self._catalog = catalog

    async def fetch(self, user_id: int) -> PlayerProfile:
        record = await self._store.get_or_create(user_id)
        return self._to_profile(record)

    async def spend(self, user_id: int, currency: str, amount: int) -> PlayerProfile:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        record = await self._store.get_or_create(user_id)
        wallet = Wallet(balances=dict(record.wallet))
        try:
            wallet.debit(currency, amount)
        except ValueError as exc:  # convert to domain-specific error
            raise InsufficientCurrency(str(exc)) from exc
        record.wallet = dict(wallet.balances)
        await self._store.save(record)
        return self._to_profile(record)

    async def credit(self, user_id: int, currency: str, amount: int) -> PlayerProfile:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        record = await self._store.get_or_create(user_id)
        wallet = Wallet(balances=dict(record.wallet))
        wallet.credit(currency, amount)
        record.wallet = dict(wallet.balances)
        await self._store.save(record)
        return self._to_profile(record)

    async def clear_cooldown(self, user_id: int) -> PlayerProfile:
        record = await self._store.get_or_create(user_id)
        record.last_drop_at = None
        await self._store.save(record)
        return self._to_profile(record)

    async def add_card(self, user_id: int, card_id: str, quantity: int = 1) -> PlayerProfile:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        record = await self._store.get_or_create(user_id)
        current = record.inventory.get(card_id, 0)
        max_copies = None
        if self._catalog:
            card = self._catalog.get_card(card_id)
            max_copies = card.max_copies
        if max_copies is not None and current >= max_copies:
            raise NoCardsAvailable(f"Cannot grant card {card_id}: limit reached")
        record.inventory[card_id] = current + quantity
        await self._store.save(record)
        return self._to_profile(record)

    async def grant_experience(self, user_id: int, amount: int) -> PlayerProfile:
        if amount == 0:
            return await self.fetch(user_id)
        record = await self._store.get_or_create(user_id)
        record.experience = max(0, record.experience + amount)
        await self._store.save(record)
        return self._to_profile(record)

    def _to_profile(self, record: PlayerRecord) -> PlayerProfile:
        return PlayerProfile(
            user_id=record.user_id,
            username=record.username,
            inventory=dict(record.inventory),
            wallet=dict(record.wallet),
            experience=record.experience,
            is_banned=record.is_banned,
        )
