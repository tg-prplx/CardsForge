"""Configuration models for CardForge."""

from __future__ import annotations

import os
import json
from dataclasses import dataclass, field
from typing import Literal, Mapping, Sequence


StorageBackend = Literal["memory", "sqlalchemy"]


@dataclass(slots=True)
class StorageConfig:
    """Configure how player state and catalogs are persisted."""

    backend: StorageBackend = "memory"
    dsn: str | None = None
    echo_sql: bool = False

    def resolve_dsn(self) -> str | None:
        if self.dsn:
            return self.dsn
        if self.backend == "sqlalchemy":
            return "sqlite+aiosqlite:///./cardforge.db"
        return None


@dataclass(slots=True)
class AdminCommandConfig:
    """Allows renaming admin bot commands."""

    ban: str = "ban"
    unban: str = "unban"
    grant_card: str = "grantcard"
    grant_currency: str = "grantcurrency"


@dataclass(slots=True)
class AdminConfig:
    """Feature switches for admin tooling."""

    admin_ids: set[int] = field(default_factory=set)
    enable_audit_logs: bool = True
    audit_channel_id: int | None = None
    enable_ban: bool = True
    commands: AdminCommandConfig = field(default_factory=AdminCommandConfig)


@dataclass(slots=True)
class DropConfig:
    """Rules controlling how players receive cards."""

    base_cooldown_seconds: int = 3600
    allow_duplicates: bool = True
    duplicate_penalty: float = 0.0
    max_cards_per_drop: int = 1
    rarity_weights: Mapping[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class CardForgeConfig:
    """Top-level configuration container."""

    bot_token: str = ""
    storage: StorageConfig = field(default_factory=StorageConfig)
    admin: AdminConfig = field(default_factory=AdminConfig)
    drop: DropConfig = field(default_factory=DropConfig)
    default_currencies: Sequence[str] = field(default_factory=lambda: ("coins", "gems"))
    rng_seed: int | None = None

    @classmethod
    def from_env(cls) -> "CardForgeConfig":
        """Create config from environment variables prefixed with CARDFORGE_."""
        prefix = "CARDFORGE_"
        storage_backend = os.getenv(f"{prefix}STORAGE_BACKEND", "memory")
        dsn = os.getenv(f"{prefix}STORAGE_DSN")
        echo_sql = os.getenv(f"{prefix}STORAGE_ECHO_SQL", "false").lower() in {"1", "true", "yes"}

        admin_ids = {
            int(_id.strip())
            for ids in [os.getenv(f"{prefix}ADMIN_IDS", "")]
            for _id in ids.split(",")
            if _id.strip()
        }

        admin_config = AdminConfig(
            admin_ids=admin_ids,
            enable_audit_logs=os.getenv(f"{prefix}ADMIN_ENABLE_AUDIT_LOGS", "true").lower()
            in {"1", "true", "yes"},
            audit_channel_id=(
                int(os.getenv(f"{prefix}ADMIN_AUDIT_CHANNEL", "0")) or None
            ),
            enable_ban=os.getenv(f"{prefix}ADMIN_ENABLE_BAN", "true").lower() in {"1", "true", "yes"},
            commands=AdminCommandConfig(
                ban=os.getenv(f"{prefix}ADMIN_CMD_BAN", "ban") or "ban",
                unban=os.getenv(f"{prefix}ADMIN_CMD_UNBAN", "unban") or "unban",
                grant_card=os.getenv(f"{prefix}ADMIN_CMD_GRANT_CARD", "grantcard") or "grantcard",
                grant_currency=os.getenv(
                    f"{prefix}ADMIN_CMD_GRANT_CURRENCY", "grantcurrency"
                )
                or "grantcurrency",
            ),
        )

        drop_config = DropConfig(
            base_cooldown_seconds=int(os.getenv(f"{prefix}DROP_BASE_COOLDOWN", "3600")),
            allow_duplicates=os.getenv(f"{prefix}DROP_ALLOW_DUPLICATES", "true").lower()
            in {"1", "true", "yes"},
            duplicate_penalty=float(os.getenv(f"{prefix}DROP_DUPLICATE_PENALTY", "0.0")),
            max_cards_per_drop=int(os.getenv(f"{prefix}DROP_MAX_CARDS", "1")),
            rarity_weights=_parse_rarity_weights(os.getenv(f"{prefix}DROP_RARITY_WEIGHTS")),
        )

        currencies = tuple(
            cur.strip()
            for cur in os.getenv(f"{prefix}DEFAULT_CURRENCIES", "coins,gems").split(",")
            if cur.strip()
        )

        return cls(
            bot_token=os.getenv(f"{prefix}BOT_TOKEN", ""),
            storage=StorageConfig(
                backend=storage_backend, dsn=dsn, echo_sql=echo_sql
            ),
            admin=admin_config,
            drop=drop_config,
            default_currencies=currencies,
            rng_seed=(
                int(os.getenv(f"{prefix}RNG_SEED")) if os.getenv(f"{prefix}RNG_SEED") else None
            ),
        )


def _parse_rarity_weights(raw: str | None) -> Mapping[str, float]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON for CARDFORGE_DROP_RARITY_WEIGHTS") from exc
    if not isinstance(data, dict):
        raise ValueError("CARDFORGE_DROP_RARITY_WEIGHTS must be a JSON object")
    return {str(k): float(v) for k, v in data.items()}
