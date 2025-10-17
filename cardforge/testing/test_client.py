"""Async test client that bypasses Telegram transport."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from ..domain.inventory import InventoryService
from ..domain.player import PlayerService


@dataclass(slots=True)
class TestMessage:
    __test__ = False

    text: str
    metadata: Dict[str, Any]


class TestClient:
    __test__ = False

    """Facilitate scenario testing without Telegram HTTP calls."""

    def __init__(self, inventory: InventoryService, player_service: PlayerService) -> None:
        self._inventory = inventory
        self._players = player_service
        self._log: List[TestMessage] = []

    async def drop(self, user_id: int, pack_id: str, username: str | None = None) -> None:
        outcome = await self._inventory.drop_from_pack(user_id, pack_id, username=username)
        self._log.append(
            TestMessage(
                text=f"Dropped {', '.join(card.card_id for card in outcome.cards)}",
                metadata={
                    "cards": [card.card_id for card in outcome.cards],
                    "reward": outcome.reward.currencies,
                    "duplicates": [card.card_id for card in outcome.duplicates],
                },
            )
        )

    async def spend(self, user_id: int, currency: str, amount: int) -> None:
        profile = await self._players.spend(user_id, currency, amount)
        self._log.append(
            TestMessage(
                text=f"Spent {amount} {currency}",
                metadata={"wallet": profile.wallet},
            )
        )

    def history(self) -> List[TestMessage]:
        return list(self._log)
