# CardForge Architecture Overview

## Goals
- Accelerate prototyping of Telegram card-collecting bots.
- Provide flexible domain primitives (cards, currencies, mini-games) that can be extended or replaced.
- Offer tooling for economy sanity checks, admin operations, and automated testing.
- Support multiple storage backends so teams can plug in existing data stores.

## Top-Level Layout
```
cardforge/
├── app.py             # High level bot orchestration & lifecycle hooks
├── config.py          # Typed runtime configuration and dependency wiring
├── registry.py        # Declarative registries for cards, currencies, mini-games
├── loaders/           # Declarative catalog loaders (JSON, etc.)
├── storage/           # Persistence abstractions (base + built-in backends)
├── domain/            # Core domain models and services
├── telegram/          # Transport layer integrations (aiogram adapter)
├── admin/             # Admin command handlers & utilities
├── diagnostics/       # Economy validator & simulation helpers
└── testing/           # Fixtures and test client
```

### Core Domain
- `domain/cards.py`: Card definitions, rarity, rewards, duplication policy.
- `domain/economy.py`: Currency abstractions, resource transactions, balance rules.
- `domain/inventory.py`: Player inventory handling, cooldown rules, reward distribution.
- `domain/events.py`: Event bus to observe lifecycle events (drops, trades, bans).
- `domain/drop_strategies.py`: Duplicate handling strategies (penalty, dust, custom).
- `domain/player.py`: Wallet helpers plus direct grants/spends for admin tools and mini-games.

### Storage Layer
- `storage/base.py`: Interfaces for player state, card catalog, and economy ledgers.
- `storage/memory.py`: In-memory backend for prototyping & tests.
- `storage/sqlalchemy.py`: SQLAlchemy-powered backend (SQLite by default) with migration hooks.

### Telegram Integration
- `telegram/aiogram_router.py`: Wires domain services into aiogram routers.
- `telegram/filters.py`: Reusable filters (cooldowns, admin guard, ban checks).
- `telegram/keyboards.py`: Helpers to render card previews and admin panels.
- `telegram/minigames.py`: Telegram-oriented `MiniGameContext` implementation.

### Admin Toolkit
- `admin/service.py`: Core admin operations (ban/unban, grant cards/resources, adjust cooldowns).
- `admin/commands.py`: Telegram command handlers for admin actions.
- `admin/audit.py`: Audit trail utilities that plug into the selected storage backend.

### Diagnostics & Testing
- `diagnostics/economy_simulator.py`: Monte Carlo simulator for drop rates & resource sinks.
- `diagnostics/checklist.py`: High-level economy sanity checks (inflation, progression pacing).
- `testing/factory.py`: Factories for cards, players, and inventories.
- `testing/test_client.py`: Lightweight bot client for scenario testing without Telegram.

## Extensibility Points
- Declarative registries for cards, currencies, mini-games; register via code or data-driven loaders.
- JSON loader allows content teams to iterate on catalogs without touching Python code.
- Service interfaces (`CardService`, `EconomyService`, `MiniGame`) encourage dependency injection.
- Middleware hooks for Telegram updates to support logging, analytics, or security guards.
- Configuration system supports environment variables, `.env`, or constructed objects (including custom admin commands).

## Workflow Highlights
1. Define cards, currencies, and mini-games using registries or JSON catalogs.
2. Choose or implement a storage backend.
3. Instantiate `BotApp` with adapters and start polling/webhook via aiogram.
4. Use diagnostics before launch to stress test the economy.
5. Rely on admin toolkit for live operations (bans, grants, balance tweaks).

## Testing Strategy
- Provide pytest fixtures for in-memory storage and deterministic random seeds.
- Ship sample tests covering drop generation, duplicate handling, and economy balance.
- Encourage scenario-driven tests via testing client to ensure Telegram flows behave as expected.
