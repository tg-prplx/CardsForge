"""Пример минимальной интеграции CardForge."""

from __future__ import annotations

import random
from pathlib import Path

from cardforge import BotApp, CardForgeConfig
from cardforge.diagnostics.economy_simulator import EconomySimulator
from cardforge.loaders import load_catalog_from_json
from cardforge.registry import MiniGame


async def coinflip_game(context) -> None:
    await context.send_message("🪙 Подбрасываю монетку...")
    if random.choice(["heads", "tails"]) == "heads":
        await context.send_message("Орёл! Получаешь 10 монет и 5 опыта.")
        await context.award_currency("coins", 10)
        await context.grant_experience(5)
    else:
        await context.send_message("Решка! Попробуй ещё раз позже.")


def register(app: BotApp) -> None:
    """Определяем карты, паки, кастомные команды и мини-игры."""
    catalog_path = Path(__file__).with_name("catalog") / "cards.json"
    load_catalog_from_json(app, catalog_path)

    app.config.admin.commands.grant_card = "giftcard"

    app.mini_games.register(
        MiniGame(
            game_id="coinflip",
            name="Монетка",
            description="Угадай исход броска монеты, чтобы получить награду.",
            command="coinflip",
            handler=coinflip_game,
        )
    )


def simulate() -> None:
    config = CardForgeConfig.from_env()
    app = BotApp(config)
    register(app)
    simulator = EconomySimulator(app)
    result = simulator.simulate("starters", pulls=100)
    print(f"Уникальных карт: {result.uniques}, дубликатов: {result.duplicates}")


if __name__ == "__main__":
    simulate()
