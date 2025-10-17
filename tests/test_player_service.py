import pytest

from cardforge.app import BotApp
from cardforge.config import CardForgeConfig
from cardforge.domain.cards import Card, CardReward, Rarity
from cardforge.domain.exceptions import NoCardsAvailable


@pytest.mark.asyncio()
async def test_add_card_respects_max_copies():
    app = BotApp(CardForgeConfig(bot_token="test"))
    app.cards.card(
        Card(
            card_id="unique",
            name="Unique Card",
            description="",
            rarity=Rarity.LEGENDARY,
            reward=CardReward(),
            max_copies=1,
        )
    )
    profile = await app.player_service.add_card(1, "unique")
    assert profile.inventory["unique"] == 1
    with pytest.raises(NoCardsAvailable):
        await app.player_service.add_card(1, "unique")


@pytest.mark.asyncio()
async def test_grant_experience_updates_profile():
    app = BotApp(CardForgeConfig(bot_token="test"))
    profile = await app.player_service.grant_experience(1, 10)
    assert profile.experience == 10
    profile = await app.player_service.grant_experience(1, -5)
    assert profile.experience == 5
