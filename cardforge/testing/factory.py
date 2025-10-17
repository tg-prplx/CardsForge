"""Factories for tests and prototyping."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Iterable

from faker import Faker

from ..domain.cards import Card, CardReward, Rarity
from ..domain.player import PlayerProfile


@dataclass(slots=True)
class CardFactory:
    faker: Faker = field(default_factory=Faker)
    rng: Random = field(default_factory=Random)

    def build(self, rarity: Rarity | None = None) -> Card:
        rarity = rarity or self.rng.choice(list(Rarity))
        card_id = f"card_{self.faker.unique.lexify(text='????')}"
        reward = CardReward(
            currencies={"coins": self.rng.randint(1, 10)},
            experience=self.rng.randint(1, 5),
        )
        return Card(
            card_id=card_id,
            name=self.faker.word().title(),
            description=self.faker.sentence(),
            rarity=rarity,
            reward=reward,
        )

    def batch(self, count: int, rarity: Rarity | None = None) -> Iterable[Card]:
        for _ in range(count):
            yield self.build(rarity=rarity)


@dataclass(slots=True)
class PlayerFactory:
    faker: Faker = field(default_factory=Faker)

    def build_profile(self, user_id: int | None = None) -> PlayerProfile:
        user_id = user_id or self.faker.random_int()
        return PlayerProfile(
            user_id=user_id,
            username=self.faker.user_name(),
            inventory={},
            wallet={},
            experience=0,
            is_banned=False,
        )
