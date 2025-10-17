# CardForge Development Guide

This guide collects everything designers and developers need to stand up and grow a CardForge-powered Telegram bot.

---

## 1. Architectural Building Blocks

| Component                    | Purpose                                                                                |
|-----------------------------|----------------------------------------------------------------------------------------|
| `cardforge.app.BotApp`      | Wires configuration, stores, domain services, registries, and mini-games.              |
| `cardforge.domain`          | Domain models (cards, rewards, economy) and services (inventory, players, events).     |
| `cardforge.storage`         | Persistence layer (in-memory and SQLAlchemy implementations).                         |
| `cardforge.loaders`         | Declarative catalog loaders (JSON today, extendable to YAML/API).                      |
| `cardforge.telegram`        | Ready-made aiogram routers, filters, mini-game context.                                |
| `cardforge.admin`           | Admin command handlers and service layer.                                              |
| `cardforge.diagnostics`     | Economy simulations and balance checklists.                                            |
| `cardforge.testing`         | Factories, fixtures, and the scenario test client.                                     |

---

## 2. `CardForgeConfig` Overview

| Field                        | Type                     | Default            | Description                                                     |
|-----------------------------|--------------------------|--------------------|-----------------------------------------------------------------|
| `bot_token`                 | `str`                    | `""`               | Telegram bot token.                                             |
| `storage.backend`           | `"memory"` \| `"sqlalchemy"` | `"memory"`       | Storage backend selection.                                      |
| `storage.dsn`               | `str \| None`            | `None`             | DSN for SQLAlchemy backend.                                     |
| `admin.admin_ids`           | `set[int]`               | `set()`            | Authorised admin user IDs.                                      |
| `admin.commands`            | `AdminCommandConfig`     | default commands   | Rename `/ban`, `/unban`, `/grantcard`, `/grantcurrency`.         |
| `drop.base_cooldown_seconds`| `int`                    | `3600`             | Drop cooldown in seconds.                                       |
| `drop.allow_duplicates`     | `bool`                   | `True`             | Whether duplicates are allowed.                                 |
| `drop.duplicate_penalty`    | `float`                  | `0.0`              | Reward multiplier for duplicate strategy.                        |
| `drop.max_cards_per_drop`   | `int`                    | `1`                | Cards granted per drop.                                         |
| `drop.rarity_weights`       | `dict[str, float]`       | `{}`               | Global rarity weights.                                          |
| `default_currencies`        | `Sequence[str]`          | `("coins","gems")` | Currencies auto-registered by `BotApp`.                         |
| `rng_seed`                  | `int \| None`            | `None`             | RNG seed for reproducible behaviour.                            |

> Configure `CardForgeConfig` before instantiating `BotApp` to avoid rebuilding services.

---

## 3. JSON Schema Highlights

### 3.1 Cards (`cards[]`)

| Field          | Type          | Required | Notes                                                   |
|----------------|---------------|----------|--------------------------------------------------------|
| `id`           | `str`         | ✔        | Unique identifier.                                     |
| `name`         | `str`         | ✔        | Display name.                                          |
| `description`  | `str`         | ✔        | Lore/description.                                      |
| `rarity`       | `str`         | ✔        | `common`, `uncommon`, `rare`, `epic`, `legendary`.     |
| `maxCopies`    | `int`         | ✖        | Maximum copies per player.                             |
| `weight`       | `float`       | ✖        | Base drop weight (defaults to 1.0).                    |
| `reward`       | `object`      | ✖        | `currencies` plus `experience`.                        |
| `image.url`    | `str` (URL)   | ✖        | Optional image to send in chat.                        |
| `image.caption`| `str`         | ✖        | Optional caption.                                      |
| `tags`         | `array[str]`  | ✖        | Metadata for filtering/collections.                    |

### 3.2 Packs (`packs[]`)

| Field             | Type            | Required | Notes                                                   |
|-------------------|-----------------|----------|--------------------------------------------------------|
| `id`              | `str`           | ✔        | Unique pack identifier.                                |
| `name`            | `str`           | ✖        | Display name.                                          |
| `cards`           | `array[str]`    | ✔        | List of card IDs.                                      |
| `allowDuplicates` | `bool`          | ✖        | Allow multiple copies per roll.                        |
| `maxPerRoll`      | `int`           | ✖        | Cards granted per roll.                                |
| `cardWeights`     | `object`        | ✖        | Per-card weight overrides.                             |
| `rarityWeights`   | `object`        | ✖        | Rarity weight overrides.                               |

---

## 4. Drop Algorithm

1. Fetch pack cards.
2. Filter according to duplication rules and `maxCopies`.
3. Compute weights (card override → pack override → global config).
4. Draw cards with weighted choice (allowing duplicates if permitted).
5. Apply rewards or duplicate strategy output.

---

## 5. Duplicate Strategies

- `PenaltyDuplicateStrategy` — multiplies rewards by `duplicate_penalty`.
- `DustDuplicateStrategy(currency, amount)` — grants a fixed currency.
- Custom strategies — implement `DuplicateStrategy.handle()` and pass to `BotApp`.

---

## 6. Mini-Games

`TelegramMiniGameContext` exposes:
- `send_message`
- `award_currency`
- `spend_currency`
- `grant_card`
- `grant_experience`
- `get_profile`
- `send_dice` — send a Telegram dice with a given emoji.
- `roll_dice` — send a dice and return its rolled value.

Mini-game commands are auto-registered via `MiniGame.command` and `aliases`. `MiniGameRegistry` ensures command uniqueness.

---

## 7. Administration

`AdminService` capabilities:
- `ban_user`, `unban_user`
- `grant_currency`, `grant_card`
- `adjust_experience`, `set_cooldown`

Rename commands through `AdminCommandConfig` or environment variables (`CARDFORGE_ADMIN_CMD_*`). Actions are persisted through `AuditStore`.

---

## 8. Testing

- `tests/test_inventory.py`: drops, cooldowns, duplicate handling.
- `tests/test_json_loader.py`: catalog validation.
- `tests/test_player_service.py`: player operations.
- Fixtures and factories: `cardforge.testing`.
- Scenario testing: `TestClient`.

---

## 9. Diagnostics & Analytics

| Tool                              | Purpose                                        |
|-----------------------------------|------------------------------------------------|
| `cardforge-sim`                   | Economy simulation (drop frequency/sinks).     |
| `cardforge-check`                 | Balance checklist.                             |
| `cardforge-validate --catalog`    | Validate JSON catalogs.                        |
| `cardforge-validate --module`     | Validate assembled app configuration.         |
| `EventBus`                        | Handle events like `player.drop.completed`.    |

---

## 10. Extending the Framework

- Invent new duplicate strategies.
- Supply custom stores (implement `PlayerStore`, `DropHistoryStore`, `AuditStore`).
- Add alternative transport adapters (Pyrogram, Telethon, etc.).
- Build additional CLI tooling and diagnostics.

---

## 11. Delivery Checklist

1. Define content (cards, currencies, mini-games).
2. Tune economy and duplicate strategies.
3. Configure storage and routers.
4. Run simulations and validators.
5. Write and execute tests.
6. Prepare deployment (polling or webhook).

---

## 12. Extension Map

| Extension Point                    | Customisation Ideas                                                                |
|-----------------------------------|------------------------------------------------------------------------------------|
| `BotApp(duplicate_strategy=…)`    | Inject bespoke duplicate handling logic.                                           |
| `CardForgeConfig.drop`            | Control cooldowns, rarity weights, per-drop limits.                                |
| `cardforge.loaders.validate_*`    | Add extra data quality gates before registration.                                  |
| `MiniGameRegistry.register`       | Plug in any interactive experience with custom context.                            |
| `AdminCommandConfig`              | Localise or rename admin commands.                                                 |
| `EventBus.subscribe(...)`         | Emit analytics, logging, achievements.                                             |
| `PlayerService`                   | Extend wallet/experience/collection operations.                                    |
| `InventoryService`                | Provide a custom RNG or specialised drop behaviour.                                |
| `cardforge.testing`               | Build factories and scenario utilities for automated tests.                        |

Use these hooks to shape the core to your economy and gameplay requirements.
