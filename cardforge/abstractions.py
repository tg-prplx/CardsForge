"""High-level helpers that simplify bootstrapping CardForge bots.

This module provides a straightforward, batteries-included API oriented towards
developers who do not want to dive into the full async/config ecosystem.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Iterable, Sequence

from aiogram import Bot, Dispatcher
from rich.console import Console

from . import BotApp, CardForgeConfig
from .diagnostics.economy_simulator import EconomySimulator
from .loaders import load_catalog_from_json, parse_catalog_dict, validate_catalog_dict
from .registry import MiniGame, MiniGameRegistry
from .telegram import build_router
from .admin import build_admin_router

console = Console()


@dataclass(slots=True)
class SimpleBotConfig:
    """Minimal settings required to run a CardForge bot."""

    bot_token: str
    catalog_path: Path
    default_pack: str | None = None
    storage: str = "memory"  # "memory" or path to SQLite file
    admin_ids: Sequence[int] = ()


async def run_simple_bot(config: SimpleBotConfig) -> None:
    """Spin up a ready-to-go aiogram bot with sensible defaults."""

    cardforge_config = CardForgeConfig.from_env()
    cardforge_config.bot_token = config.bot_token
    if config.storage != "memory":
        db_path = Path(config.storage).expanduser().resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        cardforge_config.storage.backend = "sqlalchemy"
        cardforge_config.storage.dsn = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    if config.admin_ids:
        cardforge_config.admin.admin_ids = set(config.admin_ids)

    app = BotApp(cardforge_config)
    await app.init_backend()
    load_catalog_from_json(app, config.catalog_path)

    bot = Bot(app.config.bot_token)
    dp = Dispatcher()
    dp.include_router(build_router(app, default_pack=config.default_pack))
    dp.include_router(build_admin_router(app))

    simulator = EconomySimulator(app)
    summary = simulator.simulate(config.default_pack or next(iter(app.cards.catalog._packs)), pulls=50)
    console.print(
        f"[bold green]CardForge ready![/bold green]\n"
        f"Unique cards: {summary.uniques}, duplicates: {summary.duplicates}",
    )

    await dp.start_polling(bot)


def run_simple_bot_sync(config: SimpleBotConfig) -> None:
    """Synchronous wrapper for run_simple_bot."""

    asyncio.run(run_simple_bot(config))


@dataclass(slots=True)
class SimpleMiniGame:
    game_id: str
    name: str
    description: str
    handler: Callable[[MiniGameRegistry], Awaitable[None]]


@dataclass(slots=True)
class CatalogBuilder:
    """Imperative builder that produces JSON catalogs."""

    cards: list[dict] = field(default_factory=list)
    packs: list[dict] = field(default_factory=list)
    currencies: list[dict] = field(
        default_factory=lambda: [{"code": "coins", "name": "Coins"}, {"code": "gems", "name": "Gems"}]
    )

    def add_card(
        self,
        card_id: str,
        name: str,
        description: str,
        *,
        rarity: str = "common",
        image_url: str | None = None,
        image_local: str | None = None,
        image_caption: str | None = None,
        reward_currencies: dict[str, int] | None = None,
        reward_experience: int = 0,
        tags: Iterable[str] = (),
        max_copies: int | None = None,
        drop_weight: float | None = None,
    ) -> "CatalogBuilder":
        card: dict = {
            "id": card_id,
            "name": name,
            "description": description,
            "rarity": rarity,
            "reward": {
                "currencies": reward_currencies or {"coins": 1},
                "experience": reward_experience,
            },
            "tags": list(tags),
        }
        if image_url or image_local or image_caption:
            image: dict = {}
            if image_url:
                image["url"] = image_url
            if image_local:
                image["local"] = image_local
            if image_caption:
                image["caption"] = image_caption
            card["image"] = image
        if max_copies is not None:
            card["maxCopies"] = max_copies
        if drop_weight is not None:
            card["weight"] = drop_weight
        self.cards.append(card)
        return self

    def add_pack(
        self,
        pack_id: str,
        name: str,
        *,
        cards: Sequence[str],
        allow_duplicates: bool = True,
        max_per_roll: int = 1,
        card_weights: dict[str, float] | None = None,
        rarity_weights: dict[str, float] | None = None,
    ) -> "CatalogBuilder":
        pack = {
            "id": pack_id,
            "name": name,
            "cards": list(cards),
            "allowDuplicates": allow_duplicates,
            "maxPerRoll": max_per_roll,
        }
        if card_weights:
            pack["cardWeights"] = card_weights
        if rarity_weights:
            pack["rarityWeights"] = rarity_weights
        self.packs.append(pack)
        return self

    def build(self) -> dict:
        catalog = {
            "currencies": self.currencies,
            "cards": self.cards,
            "packs": self.packs,
        }
        errors = validate_catalog_dict(catalog)
        if errors:
            raise ValueError("Catalog validation failed:\n" + "\n".join(f"- {err}" for err in errors))
        return catalog

    def save(self, path: Path) -> None:
        catalog = self.build()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")


__all__ = [
    "SimpleBotConfig",
    "SimpleMiniGame",
    "CatalogBuilder",
    "run_simple_bot",
    "run_simple_bot_sync",
]
