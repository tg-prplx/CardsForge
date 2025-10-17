import json
from pathlib import Path

import pytest

from cardforge.app import BotApp
from cardforge.config import CardForgeConfig
from cardforge.loaders import (
    load_catalog_from_json,
    parse_catalog_dict,
    validate_catalog_dict,
)


def test_parse_catalog_dict_supports_images():
    data = {
        "currencies": [{"code": "coins", "name": "Coins"}],
        "cards": [
            {
                "id": "wizard",
                "name": "Wizard",
                "description": "Magic master",
                "rarity": "epic",
                "reward": {"experience": 10, "currencies": {"coins": 5}},
                "image": {"url": "https://example.com/wizard.png", "caption": "Wizard art"},
                "tags": ["magic"],
                "weight": 2.5,
            }
        ],
        "packs": [
            {
                "id": "magic",
                "name": "Magic Pack",
                "cards": ["wizard"],
                "allowDuplicates": False,
                "rarityWeights": {"epic": 5.0},
            }
        ],
    }
    definition = parse_catalog_dict(data)
    assert definition.cards[0].image_url == "https://example.com/wizard.png"
    assert definition.cards[0].image_caption == "Wizard art"
    assert definition.cards[0].tags == ("magic",)
    assert definition.cards[0].drop_weight == 2.5
    assert definition.packs[0].rarity_weights["epic"] == 5.0


def test_parse_catalog_dict_missing_experience_raises():
    data = {
        "currencies": [{"code": "coins", "name": "Coins"}],
        "cards": [
            {
                "id": "faulty",
                "name": "Faulty",
                "description": "",
                "rarity": "common",
                "reward": {"currencies": {"coins": 1}},
            }
        ],
        "packs": [{"id": "default", "cards": ["faulty"]}],
    }
    with pytest.raises(ValueError):
        parse_catalog_dict(data)


def test_validate_catalog_dict_unknown_currency():
    data = {
        "currencies": [{"code": "coins", "name": "Coins"}],
        "cards": [
            {
                "id": "faulty",
                "name": "Faulty",
                "description": "",
                "rarity": "common",
                "reward": {"currencies": {"gems": 1}, "experience": 0},
            }
        ],
        "packs": [{"id": "default", "cards": ["faulty"]}],
    }
    errors = validate_catalog_dict(data)
    assert any("unknown currency" in err for err in errors)


@pytest.mark.asyncio()
async def test_load_catalog_from_json_registers_entities(tmp_path: Path):
    payload = {
        "currencies": [{"code": "coins", "name": "Coins"}],
        "cards": [
            {
                "id": "rogue",
                "name": "Rogue",
                "description": "Rogue desc",
                "rarity": "uncommon",
                "reward": {"experience": 3, "currencies": {"coins": 2}},
            }
        ],
        "packs": [{"id": "rogues", "cards": ["rogue"]}],
    }
    json_path = tmp_path / "catalog.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    app = BotApp(CardForgeConfig(bot_token="test"))
    load_catalog_from_json(app, json_path)

    card_ids = {card.card_id for card in app.cards.catalog.iter_cards()}
    assert "rogue" in card_ids
    pack_ids = {pack.pack_id for pack in app.cards.catalog.iter_packs()}
    assert "rogues" in pack_ids
