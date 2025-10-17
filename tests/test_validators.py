from cardforge import BotApp, CardForgeConfig
from cardforge.domain.cards import Card, CardPack, CardReward, Rarity
from cardforge.validators import validate_app


def test_validate_app_detects_missing_currency():
    config = CardForgeConfig(bot_token="test")
    app = BotApp(config)
    app.currencies.registry = type(app.currencies.registry)()  # wipe currencies
    app.cards.card(
        Card(
            card_id="alpha",
            name="Alpha",
            description="",
            rarity=Rarity.COMMON,
            reward=CardReward(currencies={"coins": 1}, experience=1),
        )
    )
    app.cards.pack(CardPack(pack_id="default", name="Default", cards=("alpha",)))
    issues = validate_app(app)
    assert any("Currency 'coins' must be registered" in issue for issue in issues)


def test_validate_app_success():
    config = CardForgeConfig(bot_token="test")
    app = BotApp(config)
    app.cards.card(
        Card(
            card_id="alpha",
            name="Alpha",
            description="",
            rarity=Rarity.COMMON,
            reward=CardReward(currencies={"coins": 1}, experience=1),
        )
    )
    app.cards.pack(CardPack(pack_id="default", name="Default", cards=("alpha",)))
    assert validate_app(app) == []
