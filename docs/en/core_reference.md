# CardForge Core Reference

Detailed reference for core classes, services, and customisation hooks. Pair it with `getting_started.md` and `development_guide.md`.

---

## 1. Configuration & Application

### `cardforge.config.CardForgeConfig`
- `bot_token`: Telegram bot token.
- `storage`: `StorageConfig` (`backend`, `dsn`, `echo_sql`).
- `admin`: `AdminConfig` (admin IDs, audit toggles, `AdminCommandConfig`).
- `drop`: `DropConfig` (cooldowns, duplicates, `rarity_weights`).
- `default_currencies`: currencies registered during `BotApp` initialisation.
- `rng_seed`: locks RNG for reproducible behaviour.

`from_env()` reads `CARDFORGE_*` variables (see tables in the guides).

### `cardforge.app.BotApp`
- Accepts `CardForgeConfig` plus optional stores (`player_store`, `history_store`, `audit_store`), `EventBus`, `rng`, and `duplicate_strategy`.
- Key attributes:
  - `cards`: `CardRegistry`
  - `currencies`: `CurrencyRegistryFacade`
  - `mini_games`: `MiniGameRegistry`
  - `inventory_service`: `InventoryService`
  - `player_service`: `PlayerService`
  - `event_bus`
- Methods:
  - `init_backend()` — initialises SQLAlchemy schema.
  - `snapshot()` — returns a summary of registered resources.

---

## 2. Domain

### Cards & Packs (`cardforge.domain.cards`)
- `Card`: fields such as `card_id`, `name`, `description`, `rarity`, `max_copies`, `reward`, `tags`, `image_*`, `drop_weight`.
- `CardPack`: `pack_id`, `name`, `cards`, `allow_duplicates`, `max_per_roll`, `card_weights`, `rarity_weights`.
- `CardReward`: `currencies`, `experience`, with `merge` helper.

### Inventory (`cardforge.domain.inventory.InventoryService`)
- Configurable via `duplicate_strategy`, `rng`, and `DropConfig`.
- Public methods:
  - `drop_from_pack(user_id, pack_id, username=None)` → `DropOutcome`.
  - `is_banned(user_id)` / `cooldown_remaining(user_id)`.
- Internal mechanics:
  - Weighted selection (`_card_weight`, `_weighted_choice`).
  - Duplicate rewards delegated to `DuplicateStrategy`.

### Duplicate Strategies (`cardforge.domain.drop_strategies`)
- `DuplicateStrategy` protocol.
- `PenaltyDuplicateStrategy` (uses `duplicate_penalty`).
+- `DustDuplicateStrategy(currency, amount)`.
- Build custom strategies and pass them to `BotApp`.

### Player (`cardforge.domain.player.PlayerService`)
- `fetch`, `spend`, `credit`, `add_card`, `grant_experience`, `clear_cooldown`.
- Used by mini-games and admin tooling to mutate player state.

### Economy (`cardforge.domain.economy`)
- `CurrencyRegistry` tracks available currencies.
- `Wallet` provides `credit`/`debit`.

### Events (`cardforge.domain.events`)
- `EventBus` pub/sub; subscribe to `player.drop.completed`, `admin.*`, etc.

---

## 3. Storage (`cardforge.storage`)

| Class                         | Purpose                                                        |
|------------------------------|----------------------------------------------------------------|
| `InMemoryPlayerStore`        | In-memory `PlayerStore`.                                       |
| `InMemoryDropHistoryStore`   | Keeps drop history in memory.                                  |
| `InMemoryAuditStore`         | In-memory audit log (UTC timestamps).                          |
| `AsyncSQLAlchemyStorage`     | Async SQL bundle (`player_store()`, `drop_history_store()`, `audit_store()`). |
| `PlayerRecord`, `DropHistoryRecord` | DTOs representing persisted state.                            |

Implement your own stores by satisfying `PlayerStore`, `DropHistoryStore`, or `AuditStore`.

---

## 4. Loaders & Validation

### `cardforge.loaders`
- `load_catalog_from_json(app, path)` — validates then registers a catalog.
- `parse_catalog_dict(data)` — parses (and validates) a dict payload.
- `validate_catalog_file(path)` / `validate_catalog_dict(data)` — returns error lists without registering.
- Checks include: currencies (must contain `coins`), reward structure, pack references, positive weights, `maxPerRoll`, `maxCopies`.

### `cardforge.validators.validate_app(app)`
- Validates a fully assembled application:
  - currencies/cards/packs are consistent,
  - `DropConfig` settings are sane,
  - references are resolvable.
- Returns a list of issues (empty list means success).

---

## 5. Telegram Integration (`cardforge.telegram`)

- `build_router(app, default_pack=None)` wires:
  - `/start`, `/drop`, `/packs`, `/profile`, `/collection`, `/cooldown`, `/games`
  - callback handler `"cardforge:roll:<pack>"`,
  - mini-game commands via `MiniGame.command`/`aliases`.
- `TelegramMiniGameContext` — runtime context for mini-games featuring:
  - messaging and reward helpers (`send_message`, `award_currency`, `spend_currency`, `grant_card`, `grant_experience`, `get_profile`);
  - dice helpers: `send_dice` to post a Telegram dice, `roll_dice` to post and read its value.
- `AdminFilter`, `NotBannedFilter`, `DropCooldownFilter`.
- `card_drop_keyboard`, `admin_panel_keyboard` for inline interactions.

---

## 6. Administration (`cardforge.admin`)

- `AdminService`:
  - `ban_user`, `unban_user`
  - `grant_currency`, `grant_card`
  - `adjust_experience`, `set_cooldown`
- `build_admin_router(app)` — aiogram router honouring `AdminCommandConfig`.

---

## 7. CLI

| Command                                       | Description                                                 |
|-----------------------------------------------|-------------------------------------------------------------|
| `cardforge-sim module pack_id --pulls 1000`   | Drop simulation for economic insights.                     |
| `cardforge-check module`                      | Balance checklist based on diagnostics.                     |
| `cardforge-validate --catalog catalog.json`   | Strict JSON validation without registering content.         |
| `cardforge-validate --module package.module`  | Validates a constructed app via `validate_app`.             |

---

## 8. Testing (`cardforge.testing`)

- `CardFactory`, `PlayerFactory`.
- `memory_app` pytest fixture.
- `TestClient` for scripted drop/spend flows without Telegram.

---

## 9. Extension Cheatsheet

- Supply custom stores to `BotApp`.
- Swap `duplicate_strategy`.
- Extend CLI with additional validators.
- Subscribe to `EventBus`.
- Inject middleware/filters into aiogram routers.
- Register bespoke mini-games.

Use this reference as a map of modules and classes you can tailor to match your bot’s mechanics.
