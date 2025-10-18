from datetime import datetime, timedelta, timezone

import pytest

from cardforge.app import BotApp
from cardforge.config import CardForgeConfig, DropConfig
from cardforge.domain.cards import Card, CardPack, CardReward, Rarity
from cardforge.domain.drop_strategies import DustDuplicateStrategy
from cardforge.domain.exceptions import CooldownActive, NoCardsAvailable
from cardforge.domain.economy import Currency


@pytest.fixture()
def app():
    config = CardForgeConfig(
        bot_token="test",
        drop=DropConfig(base_cooldown_seconds=0, allow_duplicates=False),
    )
    app = BotApp(config)
    card = Card(
        card_id="alpha",
        name="Alpha",
        description="Alpha card",
        rarity=Rarity.COMMON,
        reward=CardReward(currencies={"coins": 5}, experience=2),
    )
    app.cards.card(card)
    app.cards.pack(
        CardPack(pack_id="starters", name="Starter Pack", cards=("alpha",))
    )
    return app


@pytest.mark.asyncio()
async def test_drop_grants_rewards(app):
    outcome = await app.inventory_service.drop_from_pack(1, "starters")
    assert outcome.reward.currencies["coins"] == 5
    profile = await app.player_service.fetch(1)
    assert profile.wallet["coins"] == 5
    assert profile.inventory["alpha"] == 1


@pytest.mark.asyncio()
async def test_drop_respects_cooldown(app):
    app.config.drop.base_cooldown_seconds = 3600
    await app.inventory_service.drop_from_pack(1, "starters")
    with pytest.raises(CooldownActive):
        await app.inventory_service.drop_from_pack(1, "starters")


@pytest.mark.asyncio()
async def test_drop_handles_no_cards(app):
    app.cards.pack(CardPack(pack_id="empty", name="Empty", cards=()))
    with pytest.raises(NoCardsAvailable):
        await app.inventory_service.drop_from_pack(1, "empty")


@pytest.mark.asyncio()
async def test_weighted_drop_prefers_heavier_card():
    config = CardForgeConfig(
        bot_token="test",
        rng_seed=1,
        drop=DropConfig(base_cooldown_seconds=0, allow_duplicates=True),
    )
    app = BotApp(config)
    app.cards.card(
        Card(
            card_id="common",
            name="Common",
            description="",
            rarity=Rarity.COMMON,
            reward=CardReward(),
        )
    )
    app.cards.card(
        Card(
            card_id="rare",
            name="Rare",
            description="",
            rarity=Rarity.RARE,
            reward=CardReward(),
        )
    )
    app.cards.pack(
        CardPack(
            pack_id="weighted",
            name="Weighted Pack",
            cards=("common", "rare"),
            card_weights={"common": 0.1, "rare": 10.0},
        )
    )
    outcome = await app.inventory_service.drop_from_pack(1, "weighted")
    assert outcome.cards[0].card_id == "rare"


@pytest.mark.asyncio()
async def test_duplicate_strategy_custom_reward():
    config = CardForgeConfig(
        bot_token="test",
        drop=DropConfig(base_cooldown_seconds=0, allow_duplicates=True),
    )
    app = BotApp(config, duplicate_strategy=DustDuplicateStrategy(currency="dust", amount=5))
    app.currencies.currency(Currency(code="dust", name="Dust"))
    app.cards.card(
        Card(
            card_id="unique",
            name="Unique",
            description="",
            rarity=Rarity.LEGENDARY,
            reward=CardReward(currencies={"coins": 10}),
            max_copies=1,
        )
    )
    app.cards.pack(
        CardPack(
            pack_id="uniques",
            name="Uniques",
            cards=("unique",),
        )
    )
    await app.inventory_service.drop_from_pack(1, "uniques")
    outcome = await app.inventory_service.drop_from_pack(1, "uniques")
    profile = await app.player_service.fetch(1)
    assert outcome.duplicates[0].card_id == "unique"
    assert profile.wallet.get("dust") == 5


@pytest.mark.asyncio()
async def test_cooldown_remaining_handles_naive_timestamp(app):
    app.config.drop.base_cooldown_seconds = 5
    record = await app.player_store.get_or_create(42)
    record.last_drop_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=10)
    await app.player_store.save(record)

    remaining = await app.inventory_service.cooldown_remaining(42)
    assert remaining == 0
