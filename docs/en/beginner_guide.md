# Beginner Guide

This guide walks you through launching a CardForge bot with minimal effort.

## 1. Preparation
1. Install Python 3.11+ (make sure it is available in PATH).
2. Clone the CardForge project or unpack the archive into a convenient folder.
3. Open a terminal in the project root and run:
   `ash
   python -m pip install -e .[dev]
   `

## 2. Token and configuration
1. Obtain a token from @BotFather and store it in .env:
   `
   CARDFORGE_BOT_TOKEN=123456:ABCDEF...
   `
2. Start the local demo bot:
   `ash
   python local_bot/run_bot.py
   `
   The script uses SQLite (local_bot/cardforge.db), so inventory and cooldown survive restarts.

## 3. Build your own catalog
1. Edit xamples/catalog/cards.json or launch the interactive studio:
   `ash
   cardforge-studio
   `
2. Follow on-screen prompts: add currencies, cards, packs, then save the project.

## 4. Ready-made example
xamples/basic_bot.py demonstrates:
- remote images for the cards;
- two mini-games (/coinflip, /diceduel);
- inline buttons for collection, mini-games, and help.

Run the demo bot:
`ash
python examples/basic_bot.py
`

## 5. Quick adaptation
1. Copy xamples/basic_bot.py and adjust the egister function (your cards/mini-games).
2. Use the simplified API when you do not want to manage async manually:
   `python
   from cardforge.abstractions import SimpleBotConfig, run_simple_bot_sync
   from pathlib import Path

   run_simple_bot_sync(
       SimpleBotConfig(
           bot_token="123:ABC...",
           catalog_path=Path("my_catalog/cards.json"),
           default_pack="starters",
           storage="my_bot/cardforge.db",
           admin_ids=(123456789,),
       )
   )
   `

## 6. Where to look for help
- /help in the bot prints quick tips and useful buttons.
- Documentation: docs/en/getting_started.md, docs/en/development_guide.md.
- CLI help: cardforge-validate --help, cardforge-sim --help.
