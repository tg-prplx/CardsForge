"""Storage abstractions used by the CardForge services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Protocol, Sequence


@dataclass(slots=True)
class PlayerRecord:
    user_id: int
    username: str | None = None
    inventory: dict[str, int] = field(default_factory=dict)
    wallet: dict[str, int] = field(default_factory=dict)
    experience: int = 0
    last_drop_at: datetime | None = None
    is_banned: bool = False


@dataclass(slots=True)
class DropHistoryRecord:
    user_id: int
    card_ids: Sequence[str]
    timestamp: datetime
    rewards: Mapping[str, int]


class PlayerStore(Protocol):
    async def get_or_create(self, user_id: int, username: str | None = None) -> PlayerRecord:
        ...

    async def save(self, record: PlayerRecord) -> None:
        ...

    async def mark_banned(self, user_id: int, banned: bool) -> None:
        ...


class DropHistoryStore(Protocol):
    async def add_record(self, record: DropHistoryRecord) -> None:
        ...

    async def recent_for_user(self, user_id: int, limit: int = 20) -> Sequence[DropHistoryRecord]:
        ...


class AuditStore(Protocol):
    async def add_entry(self, action: str, payload: dict) -> None:
        ...
