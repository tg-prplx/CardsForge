from cardforge.domain.cards import Card, CardReward, Rarity
from cardforge.domain.player import PlayerProfile
from cardforge.telegram.aiogram_router import (
    format_collection_message,
    format_profile_message,
)


def test_format_profile_message_includes_wallet_and_cooldown():
    profile = PlayerProfile(
        user_id=1,
        username="tester",
        inventory={"alpha": 2},
        wallet={"coins": 10, "gems": 1},
        experience=15,
        is_banned=False,
    )
    text = format_profile_message(profile, cooldown=45)
    assert "tester" in text
    assert "coins" in text and "10" in text
    assert "45 сек" in text


def test_format_collection_message_lists_cards():
    profile = PlayerProfile(
        user_id=1,
        username=None,
        inventory={"alpha": 2},
        wallet={},
        experience=0,
        is_banned=False,
    )
    card = Card(
        card_id="alpha",
        name="Alpha",
        description="",
        rarity=Rarity.RARE,
        reward=CardReward(),
    )
    text = format_collection_message(profile.inventory, [card])
    assert "Alpha" in text
    assert "Rarity" not in text  # ensure value, not class repr
    assert "2 шт." in text
