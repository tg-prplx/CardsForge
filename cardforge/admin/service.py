"""Administrative operations for CardForge bots."""

from __future__ import annotations

from datetime import datetime, timezone

from ..domain.cards import CardCatalog
from ..domain.economy import CurrencyRegistry
from ..domain.events import EventBus
from ..domain.exceptions import NoCardsAvailable
from ..storage.base import AuditStore, PlayerStore


class AdminService:
    def __init__(
        self,
        player_store: PlayerStore,
        audit_store: AuditStore,
        catalog: CardCatalog,
        currencies: CurrencyRegistry,
        event_bus: EventBus,
    ) -> None:
        self._player_store = player_store
        self._audit_store = audit_store
        self._catalog = catalog
        self._currencies = currencies
        self._events = event_bus

    async def ban_user(self, user_id: int, *, reason: str | None = None) -> None:
        await self._player_store.mark_banned(user_id, True)
        await self._audit("ban", {"user_id": user_id, "reason": reason})
        await self._events.publish("admin.user.banned", {"user_id": user_id, "reason": reason})

    async def unban_user(self, user_id: int) -> None:
        await self._player_store.mark_banned(user_id, False)
        await self._audit("unban", {"user_id": user_id})
        await self._events.publish("admin.user.unbanned", {"user_id": user_id})

    async def grant_currency(self, user_id: int, currency: str, amount: int) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self._currencies.ensure_codes([currency])
        record = await self._player_store.get_or_create(user_id)
        record.wallet[currency] = record.wallet.get(currency, 0) + amount
        await self._player_store.save(record)
        await self._audit("grant_currency", {"user_id": user_id, "currency": currency, "amount": amount})
        await self._events.publish(
            "admin.currency.granted",
            {"user_id": user_id, "currency": currency, "amount": amount},
        )

    async def grant_card(self, user_id: int, card_id: str, quantity: int = 1) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        card = self._catalog.get_card(card_id)
        record = await self._player_store.get_or_create(user_id)
        current = record.inventory.get(card.card_id, 0)
        if card.max_copies is not None and current >= card.max_copies:
            raise NoCardsAvailable(f"Cannot grant card {card.card_id}: limit reached")
        record.inventory[card.card_id] = current + quantity
        await self._player_store.save(record)
        await self._audit(
            "grant_card", {"user_id": user_id, "card_id": card.card_id, "quantity": quantity}
        )
        await self._events.publish(
            "admin.card.granted",
            {"user_id": user_id, "card_id": card.card_id, "quantity": quantity},
        )

    async def adjust_experience(self, user_id: int, delta: int) -> None:
        record = await self._player_store.get_or_create(user_id)
        record.experience = max(0, record.experience + delta)
        await self._player_store.save(record)
        await self._audit("adjust_xp", {"user_id": user_id, "delta": delta})
        await self._events.publish("admin.xp.adjusted", {"user_id": user_id, "delta": delta})

    async def set_cooldown(self, user_id: int, timestamp: datetime | None) -> None:
        record = await self._player_store.get_or_create(user_id)
        record.last_drop_at = timestamp
        await self._player_store.save(record)
        await self._audit(
            "set_cooldown",
            {
                "user_id": user_id,
                "timestamp": timestamp.isoformat() if timestamp else None,
            },
        )

    async def _audit(self, action: str, payload: dict) -> None:
        await self._audit_store.add_entry(
            action,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **payload,
            },
        )
