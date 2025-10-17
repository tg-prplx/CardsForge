"""Validation utilities for CardForge applications."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from .app import BotApp
from .domain.cards import Rarity


def validate_app(app: BotApp) -> list[str]:
    """Return list of validation errors discovered in configured app."""
    errors: list[str] = []

    currency_codes = {currency.code for currency in app.currencies.registry.all()}
    if not currency_codes:
        errors.append("No currencies registered in application.")
    if "coins" not in currency_codes:
        errors.append("Currency 'coins' must be registered in application.")

    card_ids = set()
    for card in app.cards.catalog.iter_cards():
        card_ids.add(card.card_id)
        if card.reward.experience is None or card.reward.experience < 0:
            errors.append(f"Card '{card.card_id}' has invalid experience reward '{card.reward.experience}'.")

        for currency, amount in card.reward.currencies.items():
            if currency not in currency_codes:
                errors.append(f"Card '{card.card_id}' references unknown currency '{currency}'.")
            if amount is None or amount < 0:
                errors.append(f"Card '{card.card_id}' has invalid amount '{amount}' for currency '{currency}'.")

        if card.max_copies is not None and card.max_copies <= 0:
            errors.append(f"Card '{card.card_id}' has non-positive maxCopies value '{card.max_copies}'.")

        if card.drop_weight is not None and card.drop_weight <= 0:
            errors.append(f"Card '{card.card_id}' has non-positive weight '{card.drop_weight}'.")
        if card.image_path:
            resolved = Path(card.image_path)
            if not resolved.is_absolute():
                resolved = Path.cwd() / resolved
            if not resolved.exists():
                errors.append(f"Card '{card.card_id}' local image '{card.image_path}' not found.")

    for pack in app.cards.catalog.iter_packs():
        if not pack.cards:
            errors.append(f"Pack '{pack.pack_id}' does not contain any cards.")
        for card_id in pack.cards:
            if card_id not in card_ids:
                errors.append(f"Pack '{pack.pack_id}' references unknown card '{card_id}'.")

        if pack.max_per_roll <= 0:
            errors.append(f"Pack '{pack.pack_id}' has non-positive maxPerRoll '{pack.max_per_roll}'.")

        if pack.card_weights:
            for card_id, weight in pack.card_weights.items():
                if card_id not in card_ids:
                    errors.append(f"Pack '{pack.pack_id}' cardWeights references unknown card '{card_id}'.")
                if weight is None or weight <= 0:
                    errors.append(f"Pack '{pack.pack_id}' cardWeight for '{card_id}' must be positive.")

        if pack.rarity_weights:
            for rarity_code, weight in pack.rarity_weights.items():
                try:
                    Rarity(rarity_code)
                except Exception:
                    errors.append(
                        f"Pack '{pack.pack_id}' rarityWeights references invalid rarity '{rarity_code}'."
                    )
                if weight is None or weight <= 0:
                    errors.append(
                        f"Pack '{pack.pack_id}' rarityWeight for '{rarity_code}' must be positive."
                    )

    drop = app.config.drop
    if drop.base_cooldown_seconds < 0:
        errors.append("Drop configuration 'base_cooldown_seconds' cannot be negative.")
    if drop.max_cards_per_drop <= 0:
        errors.append("Drop configuration 'max_cards_per_drop' must be positive.")

    for rarity_code, weight in drop.rarity_weights.items():
        try:
            Rarity(rarity_code)
        except Exception:
            errors.append(f"Drop configuration rarity weight contains invalid rarity '{rarity_code}'.")
        if weight is None or weight <= 0:
            errors.append(f"Drop configuration rarity weight for '{rarity_code}' must be positive.")

    return errors


__all__ = ["validate_app"]
