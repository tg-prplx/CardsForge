"""SQLAlchemy storage backend for CardForge."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator, Sequence

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .base import AuditStore, DropHistoryRecord, DropHistoryStore, PlayerRecord, PlayerStore


class Base(DeclarativeBase):
    pass


class PlayerTable(Base):
    __tablename__ = "cardforge_players"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inventory: Mapped[dict] = mapped_column(JSON, default=dict)
    wallet: Mapped[dict] = mapped_column(JSON, default=dict)
    experience: Mapped[int] = mapped_column(Integer, default=0)
    last_drop_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)


class DropHistoryTable(Base):
    __tablename__ = "cardforge_drop_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    card_ids: Mapped[list[str]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rewards: Mapped[dict] = mapped_column(JSON)


class AuditTable(Base):
    __tablename__ = "cardforge_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    action: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSON)


class AsyncSQLAlchemyStorage:
    """Bundle of async stores backed by SQLAlchemy."""

    def __init__(self, dsn: str, *, echo: bool = False) -> None:
        self._engine = create_async_engine(dsn, echo=echo, future=True)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            yield session

    async def init_models(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def player_store(self) -> "AsyncSQLAlchemyPlayerStore":
        return AsyncSQLAlchemyPlayerStore(self._session_factory)

    def drop_history_store(self) -> "AsyncSQLAlchemyDropHistoryStore":
        return AsyncSQLAlchemyDropHistoryStore(self._session_factory)

    def audit_store(self) -> "AsyncSQLAlchemyAuditStore":
        return AsyncSQLAlchemyAuditStore(self._session_factory)


class AsyncSQLAlchemyPlayerStore(PlayerStore):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_or_create(self, user_id: int, username: str | None = None) -> PlayerRecord:
        async with self._session_factory() as session:
            record = await session.get(PlayerTable, user_id)
            if not record:
                record = PlayerTable(user_id=user_id, username=username)
                session.add(record)
                await session.commit()
            if username and record.username != username:
                record.username = username
                await session.commit()
            return PlayerRecord(
                user_id=record.user_id,
                username=record.username,
                inventory=dict(record.inventory or {}),
                wallet=dict(record.wallet or {}),
                experience=record.experience,
                last_drop_at=record.last_drop_at,
                is_banned=record.is_banned,
            )

    async def save(self, record: PlayerRecord) -> None:
        async with self._session_factory() as session:
            stmt = update(PlayerTable).where(PlayerTable.user_id == record.user_id).values(
                username=record.username,
                inventory=dict(record.inventory),
                wallet=dict(record.wallet),
                experience=record.experience,
                last_drop_at=record.last_drop_at,
                is_banned=record.is_banned,
            )
            result = await session.execute(stmt)
            if result.rowcount == 0:
                session.add(
                    PlayerTable(
                        user_id=record.user_id,
                        username=record.username,
                        inventory=dict(record.inventory),
                        wallet=dict(record.wallet),
                        experience=record.experience,
                        last_drop_at=record.last_drop_at,
                        is_banned=record.is_banned,
                    )
                )
            await session.commit()

    async def mark_banned(self, user_id: int, banned: bool) -> None:
        async with self._session_factory() as session:
            stmt = update(PlayerTable).where(PlayerTable.user_id == user_id).values(is_banned=banned)
            await session.execute(stmt)
            await session.commit()


class AsyncSQLAlchemyDropHistoryStore(DropHistoryStore):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add_record(self, record: DropHistoryRecord) -> None:
        async with self._session_factory() as session:
            session.add(
                DropHistoryTable(
                    user_id=record.user_id,
                    card_ids=list(record.card_ids),
                    timestamp=record.timestamp,
                    rewards=dict(record.rewards),
                )
            )
            await session.commit()

    async def recent_for_user(self, user_id: int, limit: int = 20) -> Sequence[DropHistoryRecord]:
        async with self._session_factory() as session:
            stmt = (
                select(DropHistoryTable)
                .where(DropHistoryTable.user_id == user_id)
                .order_by(DropHistoryTable.timestamp.desc())
                .limit(limit)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [
                DropHistoryRecord(
                    user_id=row.user_id,
                    card_ids=list(row.card_ids),
                    timestamp=row.timestamp,
                    rewards=dict(row.rewards),
                )
                for row in rows
            ]


class AsyncSQLAlchemyAuditStore(AuditStore):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add_entry(self, action: str, payload: dict) -> None:
        async with self._session_factory() as session:
            session.add(
                AuditTable(
                    created_at=datetime.now(timezone.utc),
                    action=action,
                    payload=dict(payload),
                )
            )
            await session.commit()
