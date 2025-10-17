# Справочник по ядру CardForge

Детальный справочник по ключевым классам, сервисам и точкам расширения. Используйте его совместно с `getting_started.md` и `development_guide.md`.

---

## 1. Конфигурация и приложение

### `cardforge.config.CardForgeConfig`
- `bot_token`: токен Telegram-бота.
- `storage`: `StorageConfig` (`backend`, `dsn`, `echo_sql`).
- `admin`: `AdminConfig` (ID админов, аудит, `AdminCommandConfig`).
- `drop`: `DropConfig` (кулдауны, дубликаты, `rarity_weights`).
- `default_currencies`: валюты, регистрируемые при создании `BotApp`.
- `rng_seed`: фиксирует генератор случайных чисел.

`from_env()` считывает переменные `CARDFORGE_*` (см. таблицы в руководствах).

### `cardforge.app.BotApp`
- Принимает `CardForgeConfig` и опционально сторы (`player_store`, `history_store`, `audit_store`), `EventBus`, `rng`, `duplicate_strategy`.
- Основные атрибуты:
  - `cards`: `CardRegistry`
  - `currencies`: `CurrencyRegistryFacade`
  - `mini_games`: `MiniGameRegistry`
  - `inventory_service`: `InventoryService`
  - `player_service`: `PlayerService`
  - `event_bus`
- Методы:
  - `init_backend()` — инициализация схемы SQLAlchemy.
  - `snapshot()` — краткая сводка зарегистрированных ресурсов.

---

## 2. Домен

### Карты и паки (`cardforge.domain.cards`)
- `Card`: `card_id`, `name`, `description`, `rarity`, `max_copies`, `reward`, `tags`, `image_*`, `drop_weight`.
- `CardPack`: `pack_id`, `name`, `cards`, `allow_duplicates`, `max_per_roll`, `card_weights`, `rarity_weights`.
- `CardReward`: `currencies`, `experience`, метод `merge`.

### Инвентарь (`cardforge.domain.inventory.InventoryService`)
- Настраивается через `duplicate_strategy`, `rng`, `DropConfig`.
- Основные методы:
  - `drop_from_pack(user_id, pack_id, username=None)` → `DropOutcome`.
  - `is_banned(user_id)` / `cooldown_remaining(user_id)`.
- Внутренние механизмы:
  - Взвешенный выбор (`_card_weight`, `_weighted_choice`).
  - Награды за дубликаты делегируются `DuplicateStrategy`.

### Стратегии дубликатов (`cardforge.domain.drop_strategies`)
- `DuplicateStrategy` — протокол.
- `PenaltyDuplicateStrategy` — использует `duplicate_penalty`.
- `DustDuplicateStrategy(currency, amount)` — выдаёт фиксированную валюту.
- Свои стратегии можно передать в `BotApp`.

### Игрок (`cardforge.domain.player.PlayerService`)
- Методы `fetch`, `spend`, `credit`, `add_card`, `grant_experience`, `clear_cooldown`.
- Используется мини-играми и админами для изменения состояния игрока.

### Экономика (`cardforge.domain.economy`)
- `CurrencyRegistry` содержит доступные валюты.
- `Wallet` реализует операции `credit`/`debit`.

### События (`cardforge.domain.events`)
- `EventBus` — pub/sub, подписка на события (`player.drop.completed`, `admin.*` и т.д.).

---

## 3. Хранилища (`cardforge.storage`)

| Класс                         | Назначение                                                     |
|-------------------------------|----------------------------------------------------------------|
| `InMemoryPlayerStore`         | In-memory реализация `PlayerStore`.                            |
| `InMemoryDropHistoryStore`    | In-memory журнал дропов.                                       |
| `InMemoryAuditStore`          | In-memory аудит (UTC отметки времени).                         |
| `AsyncSQLAlchemyStorage`      | Асинхронный SQL-бандл (`player_store()`, `drop_history_store()`, `audit_store()`). |
| `PlayerRecord`, `DropHistoryRecord` | DTO для сохраняемого состояния.                                 |

Чтобы использовать свои сторы, реализуйте соответствующие протоколы.

---

## 4. Загрузчики и проверки

### `cardforge.loaders`
- `load_catalog_from_json` — валидирует и регистрирует каталог.
- `parse_catalog_dict` — парсит (и валидирует) словарь.
- `validate_catalog_file/dict` — возвращает список ошибок без регистрации.
- Проверяет наличие валют (`coins` обязательно), структуру наград, ссылки паков, положительные веса и лимиты.

### `cardforge.validators.validate_app`
- Проверяет собранное приложение на валидность:
  - корректность валют, карт и паков,
  - настройки `DropConfig`,
  - разрешимость ссылок.
- Возвращает список проблем (пустой список — всё в порядке).

---

## 5. Интеграция с Telegram (`cardforge.telegram`)

- `build_router` подключает команды `/start`, `/drop`, `/packs`, `/profile`, `/collection`, `/cooldown`, `/games`, обработчик `"cardforge:roll:<pack>"` и команды мини-игр.
- `TelegramMiniGameContext` — контекст мини-игр с методами:
  - `send_message`, `award_currency`, `spend_currency`, `grant_card`, `grant_experience`, `get_profile`;
  - `send_dice` — отправить Telegram dice с нужным emoji;
  - `roll_dice` — отправить dice и получить число на грани.
- Фильтры: `AdminFilter`, `NotBannedFilter`, `DropCooldownFilter`.
- Клавиатуры: `card_drop_keyboard`, `admin_panel_keyboard`.

---

## 6. Администрирование (`cardforge.admin`)

- `AdminService`: `ban_user`, `unban_user`, `grant_currency`, `grant_card`, `adjust_experience`, `set_cooldown`.
- `build_admin_router` — aiogram-роутер с учётом `AdminCommandConfig`.

---

## 7. CLI

| Команда                                      | Назначение                                      |
|----------------------------------------------|-------------------------------------------------|
| `cardforge-sim module pack_id --pulls 1000`  | Симуляция экономики.                            |
| `cardforge-check module`                     | Чек-лист баланса.                               |
| `cardforge-validate --catalog catalog.json`  | Проверка JSON-каталога.                         |
| `cardforge-validate --module package.module` | Проверка готового приложения (`validate_app`).  |

---

## 8. Тестирование (`cardforge.testing`)

- `CardFactory`, `PlayerFactory`.
- Фикстура `memory_app`.
- `TestClient` для сценарных тестов без Telegram.

---

## 9. Быстрые точки расширения

- Передайте свои сторы в `BotApp`.
- Замените `duplicate_strategy`.
- Расширьте CLI через `cardforge.validators`.
- Подпишитесь на события `EventBus`.
- Добавьте middleware/filters в aiogram-роутер.
- Зарегистрируйте собственные мини-игры.

Этот справочник поможет ориентироваться в модульности CardForge и применять нужные расширения.
