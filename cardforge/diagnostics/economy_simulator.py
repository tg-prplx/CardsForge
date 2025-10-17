"""Economy simulation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Dict

from ..app import BotApp
from ..domain.cards import Card


@dataclass(slots=True)
class SimulationResult:
    pulls: int
    rewards: Dict[str, int] = field(default_factory=dict)
    experience: int = 0
    duplicates: int = 0
    uniques: int = 0

    def merge(self, card: Card, is_duplicate: bool) -> None:
        if is_duplicate:
            self.duplicates += 1
        else:
            self.uniques += 1
        for currency, amount in card.reward.currencies.items():
            self.rewards[currency] = self.rewards.get(currency, 0) + amount
        self.experience += card.reward.experience


class EconomySimulator:
    """Monte-Carlo simulation to evaluate drop outcomes."""

    def __init__(self, app: BotApp, *, rng: Random | None = None) -> None:
        self._app = app
        self._rng = rng or Random()

    def simulate(self, pack_id: str, *, pulls: int = 1000) -> SimulationResult:
        pack = self._app.cards.catalog.get_pack(pack_id)
        config = self._app.config.drop
        allow_duplicates = config.allow_duplicates and pack.allow_duplicates
        result = SimulationResult(pulls=pulls)
        owned: dict[str, int] = {}

        cards = [self._app.cards.catalog.get_card(cid) for cid in pack.cards]
        for _ in range(pulls):
            card = self._rng.choice(cards)
            owned_count = owned.get(card.card_id, 0)
            is_duplicate = owned_count > 0 and not allow_duplicates
            if not is_duplicate:
                owned[card.card_id] = owned_count + 1
            result.merge(card, is_duplicate)
        return result
