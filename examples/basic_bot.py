"""Пример интеграции CardForge с карточками, мини-играми и удалёнными изображениями."""

from __future__ import annotations

import asyncio
import random
from pathlib import Path

from cardforge import BotApp, CardForgeConfig
from cardforge.diagnostics.economy_simulator import EconomySimulator
from cardforge.loaders import load_catalog_from_json
from cardforge.registry import MiniGame


async def coinflip_game(context) -> None:
    await context.send_message("🪙 Подбрасываю монетку...")
    if random.choice(["heads", "tails"]) == "heads":
        await context.award_currency("coins", 10)
        await context.grant_experience(5)
        await context.send_message("Орёл! Ты получил 10 монет и 5 опыта.")
    else:
        await context.send_message("Решка! Попробуй ещё раз позже.")


async def dice_duel_game(context) -> None:
    await context.send_message("🎲 Испытываем удачу в дуэли!")
    roll = await context.roll_dice("🎲")
    if roll >= 5:
        reward = 12 if roll == 6 else 6
        await context.award_currency("coins", reward)
        await context.send_message(f"Выпало {roll}! Забирай {reward} монет.")
    else:
        await context.send_message(f"Выпало {roll}. Увы, награды нет — попробуй снова.")


def register(app: BotApp) -> None:
    """Регистрируем карточки, паки и мини-игры."""
    catalog_path = Path(__file__).with_name("catalog") / "cards.json"
    load_catalog_from_json(app, catalog_path)

    # Пример кастомизации команд администраторов.
    app.config.admin.commands.grant_card = "giftcard"

    app.mini_games.register(
        MiniGame(
            game_id="coinflip",
            name="Монетка",
            description="Угадай исход броска монеты и получи награду.",
            command="coinflip",
            handler=coinflip_game,
        )
    )
    app.mini_games.register(
        MiniGame(
            game_id="dice_duel",
            name="Кубиковая дуэль",
            description="Брось кубик и забери монеты, если выпадет 5 или 6.",
            command="diceduel",
            handler=dice_duel_game,
        )
    )


def simulate() -> None:
    config = CardForgeConfig.from_env()
    app = BotApp(config)
    register(app)
    simulator = EconomySimulator(app)
    result = simulator.simulate("starters", pulls=100)
    print(f"Уникальных карт: {result.uniques}, дубликатов: {result.duplicates}")


async def run_bot() -> None:
    from aiogram import Bot, Dispatcher
    from cardforge.telegram import build_router

    app = BotApp(CardForgeConfig.from_env())
    register(app)

    bot = Bot(app.config.bot_token)
    dp = Dispatcher()
    dp.include_router(build_router(app, default_pack="starters"))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run_bot())
