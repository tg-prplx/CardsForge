"""In-memory storage backend for CardForge."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Deque, Sequence

from .base import AuditStore, DropHistoryRecord, DropHistoryStore, PlayerRecord, PlayerStore


class InMemoryPlayerStore(PlayerStore):
    def __init__(self) -> None:
        self._records: dict[int, PlayerRecord] = {}

    async def get_or_create(self, user_id: int, username: str | None = None) -> PlayerRecord:
        if user_id not in self._records:
            self._records[user_id] = PlayerRecord(user_id=user_id, username=username)
        record = self._records[user_id]
        if username and record.username != username:
            record.username = username
        return record

    async def save(self, record: PlayerRecord) -> None:
        self._records[record.user_id] = record

    async def mark_banned(self, user_id: int, banned: bool) -> None:
        record = await self.get_or_create(user_id)
        record.is_banned = banned


class InMemoryDropHistoryStore(DropHistoryStore):
    def __init__(self, *, maxlen: int = 5000) -> None:
        self._history: Deque[DropHistoryRecord] = deque(maxlen=maxlen)

    async def add_record(self, record: DropHistoryRecord) -> None:
        self._history.append(record)

    async def recent_for_user(self, user_id: int, limit: int = 20) -> Sequence[DropHistoryRecord]:
        filtered = [rec for rec in reversed(self._history) if rec.user_id == user_id]
        return filtered[:limit]


class InMemoryAuditStore(AuditStore):
    def __init__(self, *, maxlen: int = 1000) -> None:
        self._entries: Deque[tuple[datetime, str, dict]] = deque(maxlen=maxlen)

    async def add_entry(self, action: str, payload: dict) -> None:
        self._entries.append((datetime.now(timezone.utc), action, payload))

    def dump(self) -> list[tuple[datetime, str, dict]]:
        return list(self._entries)
