"""Inventory management and drop logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from random import Random
from typing import Iterable, Sequence

from .cards import Card, CardCatalog, CardPack, CardReward, Rarity
from .economy import CurrencyRegistry, Wallet
from .events import EventBus
from .exceptions import CooldownActive, NoCardsAvailable, PlayerBanned
from .drop_strategies import DuplicateStrategy, PenaltyDuplicateStrategy
from ..config import DropConfig
from ..storage.base import DropHistoryRecord, DropHistoryStore, PlayerRecord, PlayerStore


@dataclass(slots=True)
class DropOutcome:
    cards: Sequence[Card]
    reward: CardReward
    duplicates: Sequence[Card]
    next_drop_at: datetime


class InventoryService:
    """Operate on player inventory, applying cooldowns and rewards."""

    def __init__(
        self,
        catalog: CardCatalog,
        player_store: PlayerStore,
        history_store: DropHistoryStore,
        currency_registry: CurrencyRegistry,
        drop_config: DropConfig,
        event_bus: EventBus,
        *,
        rng: Random | None = None,
        duplicate_strategy: DuplicateStrategy | None = None,
    ) -> None:
        self._catalog = catalog
        self._player_store = player_store
        self._history_store = history_store
        self._currency_registry = currency_registry
        self._drop = drop_config
        self._event_bus = event_bus
        self._rng = rng or Random()
        self._duplicate_strategy = duplicate_strategy or PenaltyDuplicateStrategy()

    async def drop_from_pack(
        self, user_id: int, pack_id: str, *, username: str | None = None
    ) -> DropOutcome:
        record = await self._player_store.get_or_create(user_id, username)
        if record.is_banned:
            raise PlayerBanned(f"User {user_id} is banned")

        now = datetime.now(timezone.utc)
        remaining = self._cooldown_remaining(record, now)
        if remaining > 0:
            raise CooldownActive(remaining)

        pack = self._catalog.get_pack(pack_id)
        allow_duplicates = self._drop.allow_duplicates and pack.allow_duplicates
        cards = [self._catalog.get_card(cid) for cid in pack.cards]

        eligible = self._filter_cards(cards, record, allow_duplicates)
        if not eligible:
            raise NoCardsAvailable(f"No cards available for pack {pack_id}")

        draw_count = min(pack.max_per_roll, self._drop.max_cards_per_drop, len(eligible))
        drawn_cards = self._draw_cards(pack, eligible, draw_count, allow_duplicates)

        duplicates: list[Card] = []
        reward = CardReward()
        for card in drawn_cards:
            current_qty = record.inventory.get(card.card_id, 0)
            if not allow_duplicates and current_qty:
                duplicates.append(card)
                reward = reward.merge(
                    self._duplicate_strategy.handle(card=card, player=record, config=self._drop)
                )
                continue

            if card.max_copies is not None and current_qty >= card.max_copies:
                duplicates.append(card)
                reward = reward.merge(
                    self._duplicate_strategy.handle(card=card, player=record, config=self._drop)
                )
                continue

            record.inventory[card.card_id] = current_qty + 1
            reward = reward.merge(card.reward)

        if reward.currencies:
            self._currency_registry.ensure_codes(reward.currencies.keys())

        wallet = Wallet(balances=dict(record.wallet))
        wallet.merge(reward.currencies)
        record.wallet = dict(wallet.balances)
        record.experience += reward.experience

        record.last_drop_at = now
        await self._player_store.save(record)

        await self._history_store.add_record(
            DropHistoryRecord(
                user_id=user_id,
                card_ids=[card.card_id for card in drawn_cards],
                timestamp=now,
                rewards=reward.currencies,
            )
        )

        await self._event_bus.publish(
            "player.drop.completed",
            {
                "user_id": user_id,
                "pack_id": pack_id,
                "cards": [card.card_id for card in drawn_cards],
                "reward": reward.currencies,
            },
        )

        next_drop = now + timedelta(seconds=self._drop.base_cooldown_seconds)
        return DropOutcome(
            cards=drawn_cards,
            reward=reward,
            duplicates=duplicates,
            next_drop_at=next_drop,
        )

    def _filter_cards(
        self, cards: Iterable[Card], record: PlayerRecord, allow_duplicates: bool
    ) -> list[Card]:
        filtered: list[Card] = []
        for card in cards:
            owned = record.inventory.get(card.card_id, 0)
            if not allow_duplicates and owned > 0:
                continue
            if card.max_copies is not None and owned >= card.max_copies and not allow_duplicates:
                continue
            filtered.append(card)
        return filtered

    def _draw_cards(
        self,
        pack: CardPack,
        cards: Sequence[Card],
        amount: int,
        allow_duplicates: bool,
    ) -> list[Card]:
        weights = [self._card_weight(card, pack) for card in cards]
        if allow_duplicates:
            return [self._weighted_choice(cards, weights) for _ in range(amount)]
        else:
            selections: list[Card] = []
            cards_pool = list(cards)
            weights_pool = list(weights)
            for _ in range(min(amount, len(cards_pool))):
                index = self._weighted_index(weights_pool)
                selections.append(cards_pool.pop(index))
                weights_pool.pop(index)
            return selections

    async def is_banned(self, user_id: int) -> bool:
        record = await self._player_store.get_or_create(user_id)
        return record.is_banned

    async def cooldown_remaining(self, user_id: int) -> int:
        record = await self._player_store.get_or_create(user_id)
        return self._cooldown_remaining(record, datetime.now(timezone.utc))

    def _cooldown_remaining(self, record: PlayerRecord, now: datetime) -> int:
        if not record.last_drop_at:
            return 0
        last_drop_at = record.last_drop_at
        if last_drop_at.tzinfo is None or last_drop_at.tzinfo.utcoffset(last_drop_at) is None:
            last_drop_at = last_drop_at.replace(tzinfo=timezone.utc)
        else:
            last_drop_at = last_drop_at.astimezone(timezone.utc)

        if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
            now = now.replace(tzinfo=timezone.utc)
        else:
            now = now.astimezone(timezone.utc)

        delta = now - last_drop_at
        remaining = self._drop.base_cooldown_seconds - int(delta.total_seconds())
        return max(0, remaining)

    def _card_weight(self, card: Card, pack: CardPack) -> float:
        # Per-card weight in pack overrides everything.
        if pack.card_weights and card.card_id in pack.card_weights:
            weight = pack.card_weights[card.card_id]
            if weight > 0:
                return float(weight)
        # Card-specific weight.
        if card.drop_weight and card.drop_weight > 0:
            return float(card.drop_weight)
        # Pack rarity overrides.
        if pack.rarity_weights:
            rarity_weight = pack.rarity_weights.get(card.rarity.value)
            if rarity_weight and rarity_weight > 0:
                return float(rarity_weight)
        # Global rarity weights.
        rarity_weight = self._drop.rarity_weights.get(card.rarity.value)
        if rarity_weight and rarity_weight > 0:
            return float(rarity_weight)
        return 1.0

    def _weighted_choice(self, cards: Sequence[Card], weights: Sequence[float]) -> Card:
        index = self._weighted_index(weights)
        return cards[index]

    def _weighted_index(self, weights: Sequence[float]) -> int:
        total = sum(weights)
        if total <= 0:
            return self._uniform_index(weights)
        threshold = self._rng.random() * total
        cumulative = 0.0
        for idx, weight in enumerate(weights):
            cumulative += weight
            if threshold <= cumulative:
                return idx
        return len(weights) - 1

    def _uniform_index(self, weights: Sequence[float]) -> int:
        return int(self._rng.random() * len(weights))
