"""Card domain models and utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping, Sequence


class Rarity(str, Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass(slots=True)
class CardReward:
    """Resources granted when a card is collected."""

    currencies: Mapping[str, int] = field(default_factory=dict)
    experience: int = 0

    def merge(self, other: "CardReward") -> "CardReward":
        merged = dict(self.currencies)
        for name, amount in other.currencies.items():
            merged[name] = merged.get(name, 0) + amount
        return CardReward(currencies=merged, experience=self.experience + other.experience)


@dataclass(slots=True)
class Card:
    """Definition of a collectible card."""

    card_id: str
    name: str
    description: str
    rarity: Rarity = Rarity.COMMON
    max_copies: int | None = None
    reward: CardReward = field(default_factory=CardReward)
    tags: tuple[str, ...] = field(default_factory=tuple)
    image_url: str | None = None
    image_caption: str | None = None
    image_path: str | None = None
    drop_weight: float | None = None


@dataclass(slots=True)
class CardPack:
    """Declarative drop configuration."""

    pack_id: str
    name: str
    cards: Sequence[str]
    allow_duplicates: bool = True
    max_per_roll: int = 1
    card_weights: Mapping[str, float] | None = None
    rarity_weights: Mapping[str, float] | None = None


class CardCatalog:
    """Registry of cards and packs."""

    def __init__(self) -> None:
        self._cards: dict[str, Card] = {}
        self._packs: dict[str, CardPack] = {}

    def register_card(self, card: Card) -> None:
        if card.card_id in self._cards:
            raise ValueError(f"Card {card.card_id} already registered")
        self._cards[card.card_id] = card

    def register_cards(self, cards: Iterable[Card]) -> None:
        for card in cards:
            self.register_card(card)

    def get_card(self, card_id: str) -> Card:
        try:
            return self._cards[card_id]
        except KeyError as exc:
            raise KeyError(f"Card {card_id} not found") from exc

    def register_pack(self, pack: CardPack) -> None:
        if pack.pack_id in self._packs:
            raise ValueError(f"Pack {pack.pack_id} already registered")
        self._packs[pack.pack_id] = pack

    def get_pack(self, pack_id: str) -> CardPack:
        try:
            return self._packs[pack_id]
        except KeyError as exc:
            raise KeyError(f"Pack {pack_id} not found") from exc

    def iter_cards(self) -> Iterable[Card]:
        return self._cards.values()

    def iter_packs(self) -> Iterable[CardPack]:
        return self._packs.values()
