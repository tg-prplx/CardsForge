"""Runtime registries for cards, currencies, and mini-games."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Protocol

from .domain.cards import Card, CardCatalog, CardPack
from .domain.economy import Currency, CurrencyRegistry


class MiniGameContext(Protocol):
    user_id: int
    username: str | None

    async def send_message(self, text: str) -> None: ...
    async def award_currency(self, currency: str, amount: int) -> None: ...
    async def spend_currency(self, currency: str, amount: int) -> None: ...
    async def grant_card(self, card_id: str, quantity: int = 1) -> None: ...
    async def grant_experience(self, amount: int) -> None: ...


MiniGameHandler = Callable[[MiniGameContext], Awaitable[None]]


@dataclass(slots=True)
class MiniGame:
    game_id: str
    name: str
    handler: MiniGameHandler
    description: str = ""
    command: str | None = None
    aliases: tuple[str, ...] = ()


class MiniGameRegistry:
    """Register and look up mini-games."""

    def __init__(self) -> None:
        self._games: Dict[str, MiniGame] = {}
        self._commands: Dict[str, str] = {}

    def register(self, game: MiniGame) -> None:
        if game.game_id in self._games:
            raise ValueError(f"Mini-game {game.game_id} already registered")
        for name in self._iter_command_keys(game):
            if name in self._commands:
                other = self._commands[name]
                raise ValueError(
                    f"Command '{name}' already used by mini-game {other}"
                )
            self._commands[name] = game.game_id
        self._games[game.game_id] = game

    def get(self, game_id: str) -> MiniGame:
        try:
            return self._games[game_id]
        except KeyError as exc:
            raise KeyError(f"Mini-game {game_id} not found") from exc

    def all(self) -> list[MiniGame]:
        return list(self._games.values())

    def find_by_command(self, command: str) -> MiniGame | None:
        key = command.lstrip("/").lower()
        game_id = self._commands.get(key)
        return self._games.get(game_id) if game_id else None

    def _iter_command_keys(self, game: MiniGame):
        if game.command:
            key = game.command.lstrip("/").lower()
            if key:
                yield key
        for alias in game.aliases:
            key = alias.lstrip("/").lower()
            if key:
                yield key


class CardRegistry:
    """Facade around CardCatalog with chainable API."""

    def __init__(self) -> None:
        self.catalog = CardCatalog()

    def card(self, card: Card) -> "CardRegistry":
        self.catalog.register_card(card)
        return self

    def pack(self, pack: CardPack) -> "CardRegistry":
        self.catalog.register_pack(pack)
        return self


class CurrencyRegistryFacade:
    """Provide a convenient registration facade."""

    def __init__(self) -> None:
        self.registry = CurrencyRegistry()

    def currency(self, currency: Currency) -> "CurrencyRegistryFacade":
        self.registry.register(currency)
        return self


__all__ = [
    "CardRegistry",
    "CurrencyRegistryFacade",
    "MiniGame",
    "MiniGameRegistry",
]
