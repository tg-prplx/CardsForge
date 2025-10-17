import pytest

from cardforge.admin.service import AdminService
from cardforge.app import BotApp
from cardforge.config import CardForgeConfig
from cardforge.domain.cards import Card, CardReward, Rarity
from cardforge.storage.memory import (
    InMemoryAuditStore,
    InMemoryDropHistoryStore,
    InMemoryPlayerStore,
)


@pytest.fixture()
def admin_app():
    config = CardForgeConfig(bot_token="test")
    player_store = InMemoryPlayerStore()
    audit_store = InMemoryAuditStore()
    history_store = InMemoryDropHistoryStore()
    app = BotApp(
        config,
        player_store=player_store,
        history_store=history_store,
        audit_store=audit_store,
    )
    app.cards.card(
        Card(
            card_id="alpha",
            name="Alpha",
            description="",
            rarity=Rarity.COMMON,
            reward=CardReward(),
        )
    )
    return app


@pytest.mark.asyncio()
async def test_grant_card(admin_app):
    service = AdminService(
        player_store=admin_app.player_store,
        audit_store=admin_app.audit_store,
        catalog=admin_app.cards.catalog,
        currencies=admin_app.currencies.registry,
        event_bus=admin_app.event_bus,
    )
    await service.grant_card(1, "alpha")
    profile = await admin_app.player_service.fetch(1)
    assert profile.inventory["alpha"] == 1


@pytest.mark.asyncio()
async def test_ban_unban(admin_app):
    service = AdminService(
        player_store=admin_app.player_store,
        audit_store=admin_app.audit_store,
        catalog=admin_app.cards.catalog,
        currencies=admin_app.currencies.registry,
        event_bus=admin_app.event_bus,
    )
    await service.ban_user(42, reason="test")
    assert await admin_app.inventory_service.is_banned(42)
    await service.unban_user(42)
    assert not await admin_app.inventory_service.is_banned(42)
