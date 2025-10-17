"""Top level application object for CardForge bots."""

from __future__ import annotations

from random import Random
from typing import Any

from .config import CardForgeConfig
from .domain.events import EventBus
from .domain.inventory import InventoryService
from .domain.drop_strategies import DuplicateStrategy, PenaltyDuplicateStrategy
from .registry import CardRegistry, CurrencyRegistryFacade, MiniGameRegistry
from .domain.economy import Currency
from .domain.player import PlayerService
from .storage.base import AuditStore, DropHistoryStore, PlayerStore
from .storage.memory import InMemoryAuditStore, InMemoryDropHistoryStore, InMemoryPlayerStore
from .storage.sqlalchemy import AsyncSQLAlchemyStorage


class BotApp:
    """Central dependency container used by bots and extensions."""

    def __init__(
        self,
        config: CardForgeConfig,
        *,
        player_store: PlayerStore | None = None,
        history_store: DropHistoryStore | None = None,
        audit_store: AuditStore | None = None,
        event_bus: EventBus | None = None,
        rng: Random | None = None,
        duplicate_strategy: DuplicateStrategy | None = None,
    ) -> None:
        self.config = config
        self.event_bus = event_bus or EventBus()
        self.cards = CardRegistry()
        self.currencies = CurrencyRegistryFacade()
        self.mini_games = MiniGameRegistry()

        for code in self.config.default_currencies:
            self.currencies.currency(Currency(code=code, name=code.title()))

        self._rng = rng or (Random(config.rng_seed) if config.rng_seed is not None else Random())

        self._sqlalchemy_storage = None
        (
            self.player_store,
            self.history_store,
            self.audit_store,
        ) = self._wire_storage(player_store, history_store, audit_store)

        self.inventory_service = InventoryService(
            catalog=self.cards.catalog,
            player_store=self.player_store,
            history_store=self.history_store,
            currency_registry=self.currencies.registry,
            drop_config=self.config.drop,
            event_bus=self.event_bus,
            rng=self._rng,
            duplicate_strategy=duplicate_strategy or PenaltyDuplicateStrategy(),
        )
        self.player_service = PlayerService(self.player_store, catalog=self.cards.catalog)

    def _wire_storage(
        self,
        player_store: PlayerStore | None,
        history_store: DropHistoryStore | None,
        audit_store: AuditStore | None,
    ) -> tuple[PlayerStore, DropHistoryStore, AuditStore]:
        if player_store and history_store and audit_store:
            return player_store, history_store, audit_store

        backend = self.config.storage.backend
        if backend == "memory":
            return (
                player_store or InMemoryPlayerStore(),
                history_store or InMemoryDropHistoryStore(),
                audit_store or InMemoryAuditStore(),
            )
        if backend == "sqlalchemy":
            dsn = self.config.storage.resolve_dsn()
            if not dsn:
                raise ValueError("SQLAlchemy backend requires a DSN")
            storage = AsyncSQLAlchemyStorage(dsn, echo=self.config.storage.echo_sql)
            self._sqlalchemy_storage = storage
            return (
                player_store or storage.player_store(),
                history_store or storage.drop_history_store(),
                audit_store or storage.audit_store(),
            )
        raise ValueError(f"Unsupported storage backend {backend}")

    def snapshot(self) -> dict[str, Any]:
        """Export current configuration for debugging."""
        return {
            "storage": self.config.storage.backend,
            "cards": [card.card_id for card in self.cards.catalog.iter_cards()],
            "packs": [pack.pack_id for pack in self.cards.catalog.iter_packs()],
            "currencies": [currency.code for currency in self.currencies.registry.all()],
            "mini_games": [game.game_id for game in self.mini_games.all()],
        }

    async def init_backend(self) -> None:
        """Initialize storage backend resources (e.g., database tables)."""
        if self._sqlalchemy_storage:
            await self._sqlalchemy_storage.init_models()
