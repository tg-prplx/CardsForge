# Getting Started with CardForge

CardForge streamlines building card-collecting Telegram bots: describe content in JSON, configure the economy, and plug in ready-made aiogram routers, admin tooling, and mini-games.

---

## 1. Installation
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e .[dev]
```

---

## 2. Bootstrapping
```python
from pathlib import Path
from aiogram import Bot, Dispatcher
from cardforge import BotApp, CardForgeConfig
from cardforge.loaders import load_catalog_from_json
from cardforge.telegram import build_router
from cardforge.admin import build_admin_router

config = CardForgeConfig.from_env()
app = BotApp(config)
load_catalog_from_json(app, Path("catalog/cards.json"))

bot = Bot(app.config.bot_token)
dp = Dispatcher()
dp.include_router(build_router(app, default_pack="starters"))
dp.include_router(build_admin_router(app))
```

---

## 3. JSON Catalog Format

```json
{
  "currencies": [
    {"code": "coins", "name": "Coins"},
    {"code": "gems",  "name": "Gems"}
  ],
  "cards": [
    {
      "id": "warrior",
      "name": "Warrior",
      "description": "Classic melee hero.",
      "rarity": "common",
      "maxCopies": 5,
      "weight": 0.6,
      "tags": ["starter"],
      "image": {
        "url": "https://example.com/warrior.png",
        "caption": "Warrior artwork"
      },
      "reward": {
        "currencies": {"coins": 5},
        "experience": 3
      }
    }
  ],
  "packs": [
    {
      "id": "starters",
      "name": "Starter Pack",
      "cards": ["warrior", "mage"],
      "allowDuplicates": true,
      "maxPerRoll": 1,
      "cardWeights": {
        "warrior": 1.0,
        "mage": 2.0
      },
      "rarityWeights": {
        "rare": 4.0,
        "common": 0.5
      }
    }
  ]
}
```

| Field                 | Description                                                                 |
|-----------------------|-----------------------------------------------------------------------------|
| `weight`              | Base drop weight for the specific card (defaults to 1.0).                   |
| `cardWeights`         | Per-card overrides inside a pack.                                           |
| `rarityWeights`       | Rarity-level weights inside a pack.                                         |
| `maxCopies`           | Maximum copies per player (duplicates beyond this trigger duplicate strategy). |
| `image.url/caption`   | Optional media data (remote).                                               |
| `image.local`         | Path to a local image copied into the project during save.                 |

---

## 4. Drop Configuration

### 4.1 Global Settings
```python
from cardforge.config import CardForgeConfig, DropConfig

config = CardForgeConfig(
    bot_token="TOKEN",
    drop=DropConfig(
        base_cooldown_seconds=1800,
        allow_duplicates=True,
        duplicate_penalty=0.25,
        max_cards_per_drop=2,
        rarity_weights={
            "legendary": 0.2,
            "epic": 0.8,
            "rare": 1.5,
            "common": 1.0,
        },
    ),
)
app = BotApp(config)
```

Environment equivalents:
```
CARDFORGE_DROP_BASE_COOLDOWN=1800
CARDFORGE_DROP_ALLOW_DUPLICATES=true
CARDFORGE_DROP_DUPLICATE_PENALTY=0.25
CARDFORGE_DROP_MAX_CARDS=2
CARDFORGE_DROP_RARITY_WEIGHTS={"legendary":0.2,"epic":0.8,"rare":1.5,"common":1.0}
```

Card weight priority:
1. `pack.cardWeights`
2. `card.weight`
3. `pack.rarityWeights`
4. `config.drop.rarity_weights`
5. default 1.0

### 4.2 Duplicate Handling
CardForge uses duplicate strategies. The default `PenaltyDuplicateStrategy` multiplies the card reward by `duplicate_penalty`. Swap strategies as needed:

```python
from cardforge.domain import DustDuplicateStrategy
from cardforge.domain.economy import Currency

config = CardForgeConfig(bot_token="TOKEN")
app = BotApp(
    config,
    duplicate_strategy=DustDuplicateStrategy(currency="dust", amount=5),
)
app.currencies.currency(Currency(code="dust", name="Dust"))
```

Built-in strategies:
- `PenaltyDuplicateStrategy` — scale reward by `duplicate_penalty`.
- `DustDuplicateStrategy(currency, amount)` — convert duplicates into a fixed currency.
Implement your own by subclassing `DuplicateStrategy`.

---

## 5. Mini-Games

`MiniGameRegistry` registers interactive games. Command `/games` lists available games. `TelegramMiniGameContext` exposes:
- `send_message(text)`
- `award_currency(currency, amount)`
- `spend_currency(currency, amount)`
- `grant_card(card_id, quantity)`
- `grant_experience(amount)`
- `get_profile()`
- `send_dice(emoji="🎲")` / `roll_dice(emoji="🎲")` to interact with Telegram dice animations.

```python
from cardforge.registry import MiniGame
from cardforge.telegram import TelegramMiniGameContext

async def coinflip(context: TelegramMiniGameContext):
    await context.send_message("🪙 Flipping a coin…")
    if random.random() < 0.5:
        await context.award_currency("coins", 10)
        await context.grant_experience(5)
        await context.send_message("Heads! Rewards delivered.")
    else:
        await context.send_message("Tails! Try again later.")

app.mini_games.register(
    MiniGame(
        game_id="coinflip",
        name="Coin Flip",
        description="Test your luck to earn rewards.",
        command="coinflip",
        aliases=("cf",),
        handler=coinflip,
    )
)
```

---

## 6. Admin Command Customization
`AdminCommandConfig` lets you rename commands without rewriting handlers:

```python
config = CardForgeConfig.from_env()
config.admin.commands = config.admin.commands.__class__(
    ban="block",
    unban="unblock",
    grant_card="giftcard",
    grant_currency="boost",
)
app = BotApp(config)
```

You can also configure command names via environment variables (`CARDFORGE_ADMIN_CMD_*`).

---

## 7. Diagnostics & Tooling

| Tool                                     | Purpose                                                      |
|------------------------------------------|--------------------------------------------------------------|
| `cardforge-sim`                          | Monte Carlo drop simulation for economy evaluation.          |
| `cardforge-check`                        | Balance checklist (empty packs, reward spikes, etc.).        |
| `cardforge-validate --catalog catalog/cards.json` | Strict JSON validation before loading.         |
| `cardforge-validate --module examples.basic_bot` | Validates the assembled bot configuration.    |
| `pytest`                                 | Run tests (the project ships with useful samples).           |
| `cardforge.testing`                      | Factories and test client for scenario testing.             |

Example test:
```python
async def test_weighted_drop_prefers_rare(app):
    outcome = await app.inventory_service.drop_from_pack(1, "weighted")
    assert outcome.cards[0].rarity == Rarity.RARE
```

---

## 8. Useful Environment Variables

| Variable                         | Description                                                  |
|----------------------------------|--------------------------------------------------------------|
| `CARDFORGE_BOT_TOKEN`            | Telegram bot token.                                          |
| `CARDFORGE_STORAGE_BACKEND`      | `memory` or `sqlalchemy`.                                    |
| `CARDFORGE_STORAGE_DSN`          | DSN for SQLAlchemy backend.                                  |
| `CARDFORGE_ADMIN_IDS`            | Comma-separated list of admin IDs.                           |
| `CARDFORGE_ADMIN_CMD_*`          | Custom names for `/ban`, `/unban`, `/grantcard`, `/grantcurrency`. |
| `CARDFORGE_DROP_*`               | Drop settings (cooldown, duplicates, weights).               |
| `CARDFORGE_RNG_SEED`             | Fixed RNG seed for reproducible drops.                       |

---

## 9. Next Steps
1. Prepare a JSON catalog (or register content via code).
2. Tune drop weights and duplicate strategy.
3. Wire up `build_router` and `build_admin_router`.
4. Add mini-games and custom commands.
5. Run `pytest` and `cardforge-validate` to ensure data and economy are sound.

CardForge is now ready for flexible bot development—happy building!
