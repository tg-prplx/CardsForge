"""Strategies controlling duplicate card handling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .cards import Card, CardReward
from ..config import DropConfig
from ..storage.base import PlayerRecord


class DuplicateStrategy(ABC):
    """Define how duplicates are handled."""

    @abstractmethod
    def handle(
        self,
        *,
        card: Card,
        player: PlayerRecord,
        config: DropConfig,
    ) -> CardReward:
        """Return additional reward granted for duplicate card."""


@dataclass(slots=True)
class PenaltyDuplicateStrategy(DuplicateStrategy):
    """Default behaviour: apply duplicate_penalty to card reward."""

    def handle(
        self,
        *,
        card: Card,
        player: PlayerRecord,
        config: DropConfig,
    ) -> CardReward:
        if config.duplicate_penalty <= 0:
            return CardReward()

        currencies = {
            currency: int(amount * config.duplicate_penalty)
            for currency, amount in card.reward.currencies.items()
        }
        return CardReward(
            currencies=currencies,
            experience=int(card.reward.experience * config.duplicate_penalty),
        )


@dataclass(slots=True)
class DustDuplicateStrategy(DuplicateStrategy):
    """Convert duplicates into specified currency amount."""

    currency: str
    amount: int

    def handle(
        self,
        *,
        card: Card,
        player: PlayerRecord,
        config: DropConfig,
    ) -> CardReward:
        if self.amount <= 0:
            return CardReward()
        return CardReward(currencies={self.currency: self.amount}, experience=0)
