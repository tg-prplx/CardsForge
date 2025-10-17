"""Load cards, packs, and currencies from JSON definitions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence, TYPE_CHECKING

from ..domain.cards import Card, CardPack, CardReward, Rarity
from ..domain.economy import Currency

if TYPE_CHECKING:
    from ..app import BotApp


@dataclass(slots=True)
class CatalogDefinition:
    cards: Sequence[Card]
    packs: Sequence[CardPack]
    currencies: Sequence[Currency]


def load_catalog_from_json(app: "BotApp", path: str | Path) -> CatalogDefinition:
    """Load cards/currencies/packs from a JSON file and register them on the app."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_catalog_dict(data)
    if errors:
        raise ValueError(_format_errors("Catalog validation failed", errors))
    definition = parse_catalog_dict(data)
    for currency in definition.currencies:
        try:
            app.currencies.currency(currency)
        except ValueError:
            # Currency already registered; skip to keep existing definition.
            continue
    for card in definition.cards:
        app.cards.catalog.register_card(card)
    for pack in definition.packs:
        app.cards.catalog.register_pack(pack)
    return definition


def parse_catalog_dict(data: dict[str, Any]) -> CatalogDefinition:
    """Parse a JSON dict (already decoded) into domain objects."""
    errors = validate_catalog_dict(data)
    if errors:
        raise ValueError(_format_errors("Catalog validation failed", errors))
    currencies = tuple(parse_currency(entry) for entry in data.get("currencies", []))
    cards = tuple(parse_card(entry) for entry in data.get("cards", []))
    packs = tuple(parse_pack(entry) for entry in data.get("packs", []))
    return CatalogDefinition(cards=cards, packs=packs, currencies=currencies)


def parse_currency(entry: dict[str, Any]) -> Currency:
    return Currency(
        code=entry["code"],
        name=entry.get("name", entry["code"].title()),
        precision=int(entry.get("precision", 0)),
        description=entry.get("description", ""),
    )


def parse_card(entry: dict[str, Any]) -> Card:
    reward_data = entry.get("reward", {})
    currencies = reward_data.get("currencies", {})
    reward = CardReward(
        currencies={str(k): int(v) for k, v in currencies.items()},
        experience=int(reward_data.get("experience", 0)),
    )
    rarity_value = entry.get("rarity", Rarity.COMMON.value)
    image_data = entry.get("image", {})
    tags = entry.get("tags", [])

    image_url = image_data.get("url")
    image_local = image_data.get("local")
    image_caption = image_data.get("caption")

    return Card(
        card_id=entry["id"],
        name=entry["name"],
        description=entry.get("description", ""),
        rarity=Rarity(rarity_value),
        max_copies=entry.get("maxCopies"),
        reward=reward,
        tags=tuple(map(str, tags)),
        image_url=image_url,
        image_caption=image_caption,
        image_path=image_local,
        drop_weight=(
            float(entry["weight"])
            if "weight" in entry and float(entry["weight"]) > 0
            else None
        ),
    )


def parse_pack(entry: dict[str, Any]) -> CardPack:
    card_weights = entry.get("cardWeights")
    rarity_weights = entry.get("rarityWeights")
    return CardPack(
        pack_id=entry["id"],
        name=entry.get("name", entry["id"]),
        cards=tuple(entry.get("cards", ())),
        allow_duplicates=entry.get("allowDuplicates", True),
        max_per_roll=int(entry.get("maxPerRoll", 1)),
        card_weights={k: float(v) for k, v in card_weights.items()} if card_weights else None,
        rarity_weights={str(k): float(v) for k, v in rarity_weights.items()} if rarity_weights else None,
    )


def validate_catalog_file(path: str | Path) -> list[str]:
    """Validate catalog JSON file and return a list of errors."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_catalog_dict(data)


def validate_catalog_dict(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    currencies_raw = data.get("currencies")
    if not isinstance(currencies_raw, list) or not currencies_raw:
        errors.append("Catalog must contain non-empty 'currencies' array.")
        currency_codes: set[str] = set()
    else:
        currency_codes = set()
        for idx, entry in enumerate(currencies_raw, start=1):
            if not isinstance(entry, dict):
                errors.append(f"Currency #{idx} must be an object.")
                continue
            code = entry.get("code")
            if not isinstance(code, str) or not code.strip():
                errors.append(f"Currency #{idx} must define non-empty 'code'.")
                continue
            if code in currency_codes:
                errors.append(f"Currency code '{code}' defined multiple times.")
            currency_codes.add(code)
        if "coins" not in currency_codes:
            errors.append("Currency 'coins' must be defined in catalog.")

    cards_raw = data.get("cards")
    if not isinstance(cards_raw, list) or not cards_raw:
        errors.append("Catalog must contain non-empty 'cards' array.")
        card_ids: set[str] = set()
    else:
        card_ids = set()
        for idx, entry in enumerate(cards_raw, start=1):
            if not isinstance(entry, dict):
                errors.append(f"Card #{idx} must be an object.")
                continue
            card_id = entry.get("id")
            if not isinstance(card_id, str) or not card_id.strip():
                errors.append(f"Card #{idx} must define non-empty 'id'.")
                continue
            if card_id in card_ids:
                errors.append(f"Card id '{card_id}' defined multiple times.")
            card_ids.add(card_id)

            for field_name in ("name", "description", "rarity"):
                if not isinstance(entry.get(field_name), str) or not entry.get(field_name).strip():
                    errors.append(f"Card '{card_id}' must define non-empty '{field_name}'.")

            rarity_value = entry.get("rarity")
            try:
                Rarity(rarity_value)
            except Exception:
                errors.append(f"Card '{card_id}' has invalid rarity '{rarity_value}'.")

            max_copies = entry.get("maxCopies")
            if max_copies is not None and (not isinstance(max_copies, int) or max_copies <= 0):
                errors.append(f"Card '{card_id}' has invalid 'maxCopies' value '{max_copies}'.")

            weight = entry.get("weight")
            if weight is not None and (not isinstance(weight, (int, float)) or float(weight) <= 0):
                errors.append(f"Card '{card_id}' has invalid 'weight' value '{weight}'.")

            reward = entry.get("reward")
            if not isinstance(reward, dict):
                errors.append(f"Card '{card_id}' must define 'reward' object.")
                continue
            if "experience" not in reward:
                errors.append(f"Card '{card_id}' reward must include 'experience'.")
            else:
                exp = reward["experience"]
                if not isinstance(exp, int) or exp < 0:
                    errors.append(f"Card '{card_id}' reward 'experience' must be non-negative integer.")

            reward_currencies = reward.get("currencies")
            if not isinstance(reward_currencies, dict) or not reward_currencies:
                errors.append(f"Card '{card_id}' reward must include 'currencies' dictionary.")
            else:
                if currency_codes:
                    for currency_code, amount in reward_currencies.items():
                        if currency_code not in currency_codes:
                            errors.append(
                                f"Card '{card_id}' reward references unknown currency '{currency_code}'."
                            )
                        if not isinstance(amount, int) or amount < 0:
                            errors.append(
                                f"Card '{card_id}' reward currency '{currency_code}' amount must be non-negative integer."
                            )
                if "coins" not in reward_currencies:
                    errors.append(f"Card '{card_id}' reward must include 'coins' currency.")

            image_data = entry.get("image")
            if image_data is not None:
                if not isinstance(image_data, dict):
                    errors.append(f"Card '{card_id}' image must be an object.")
                else:
                    image_url = image_data.get("url")
                    image_local = image_data.get("local")
                    if image_url is not None and (not isinstance(image_url, str) or not image_url.strip()):
                        errors.append(f"Card '{card_id}' image.url must be a non-empty string.")
                    if image_local is not None and (not isinstance(image_local, str) or not image_local.strip()):
                        errors.append(f"Card '{card_id}' image.local must be a non-empty string.")
                    if image_url is None and image_local is None:
                        errors.append(f"Card '{card_id}' image must define either 'url' or 'local'.")

    packs_raw = data.get("packs")
    if not isinstance(packs_raw, list) or not packs_raw:
        errors.append("Catalog must contain non-empty 'packs' array.")
    else:
        for idx, entry in enumerate(packs_raw, start=1):
            if not isinstance(entry, dict):
                errors.append(f"Pack #{idx} must be an object.")
                continue
            pack_id = entry.get("id")
            if not isinstance(pack_id, str) or not pack_id.strip():
                errors.append(f"Pack #{idx} must define non-empty 'id'.")
                continue
            cards = entry.get("cards")
            if not isinstance(cards, list) or not cards:
                errors.append(f"Pack '{pack_id}' must define non-empty 'cards' array.")
            else:
                for card_id in cards:
                    if card_ids and card_id not in card_ids:
                        errors.append(f"Pack '{pack_id}' references unknown card '{card_id}'.")

            max_per_roll = entry.get("maxPerRoll", 1)
            if not isinstance(max_per_roll, int) or max_per_roll <= 0:
                errors.append(f"Pack '{pack_id}' has invalid 'maxPerRoll' value '{max_per_roll}'.")

            card_weights = entry.get("cardWeights")
            if card_weights is not None:
                if not isinstance(card_weights, dict) or not card_weights:
                    errors.append(f"Pack '{pack_id}' has invalid 'cardWeights' definition.")
                else:
                    for card_id, weight in card_weights.items():
                        if card_ids and card_id not in card_ids:
                            errors.append(f"Pack '{pack_id}' cardWeights reference unknown card '{card_id}'.")
                        if not isinstance(weight, (int, float)) or float(weight) <= 0:
                            errors.append(
                                f"Pack '{pack_id}' cardWeights for '{card_id}' must be positive number."
                            )

            rarity_weights = entry.get("rarityWeights")
            if rarity_weights is not None:
                if not isinstance(rarity_weights, dict) or not rarity_weights:
                    errors.append(f"Pack '{pack_id}' has invalid 'rarityWeights' definition.")
                else:
                    for rarity_code, weight in rarity_weights.items():
                        try:
                            Rarity(rarity_code)
                        except Exception:
                            errors.append(
                                f"Pack '{pack_id}' rarityWeights contains invalid rarity '{rarity_code}'."
                            )
                        if not isinstance(weight, (int, float)) or float(weight) <= 0:
                            errors.append(
                                f"Pack '{pack_id}' rarityWeights for '{rarity_code}' must be positive number."
                            )

    return errors


def _format_errors(prefix: str, errors: Iterable[str]) -> str:
    formatted = "\n".join(f"- {err}" for err in errors)
    return f"{prefix}:\n{formatted}"
