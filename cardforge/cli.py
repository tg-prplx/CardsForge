"""Command line helpers for CardForge."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from .app import BotApp
from .config import CardForgeConfig
from .diagnostics.checklist import run_checklist as checklist_run
from .diagnostics.economy_simulator import EconomySimulator
from .loaders import validate_catalog_file
from .validators import validate_app


def run_simulator() -> None:
    parser = argparse.ArgumentParser(description="CardForge economy simulator")
    parser.add_argument("module", help="Python module with register(app) function")
    parser.add_argument("pack_id", help="Pack identifier to simulate")
    parser.add_argument("--pulls", type=int, default=1000, help="Количество дропов для симуляции")
    args = parser.parse_args()

    config = CardForgeConfig.from_env()
    app = BotApp(config)
    _load_module(args.module, app)

    simulator = EconomySimulator(app)
    result = simulator.simulate(args.pack_id, pulls=args.pulls)
    print(f"Симулировано {result.pulls} дропов.")
    print("Вознаграждения:")
    for currency, amount in result.rewards.items():
        print(f"  {currency}: {amount}")
    print(f"Опыт: {result.experience}")
    print(f"Уникальные карты: {result.uniques}, Дубликаты: {result.duplicates}")


def run_checklist() -> None:
    parser = argparse.ArgumentParser(description="CardForge sanity checks")
    parser.add_argument("module", help="Python module with register(app) function")
    args = parser.parse_args()

    config = CardForgeConfig.from_env()
    app = BotApp(config)
    _load_module(args.module, app)

    issues = checklist_run(app)
    if not issues:
        print("Проблем не обнаружено ✅")
        return
    for issue in issues:
        print(f"[{issue.severity.upper()}] {issue.message}")
    sys.exit(1)


def run_validate() -> None:
    parser = argparse.ArgumentParser(description="CardForge validator")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--catalog",
        help="Path to catalog JSON file for validation",
    )
    group.add_argument(
        "--module",
        help="Python module with register(app) function to validate",
    )
    args = parser.parse_args()

    if args.catalog:
        errors = validate_catalog_file(Path(args.catalog))
        if errors:
            print("Ошибки каталога:")
            for err in errors:
                print(f"- {err}")
            sys.exit(1)
        print("Каталог валиден ✅")
        return

    config = CardForgeConfig.from_env()
    app = BotApp(config)
    _load_module(args.module, app)
    issues = validate_app(app)
    if issues:
        print("Обнаружены ошибки конфигурации:")
        for issue in issues:
            print(f"- {issue}")
        sys.exit(1)
    print("Конфигурация бота валидна ✅")


def _load_module(path: str, app: BotApp) -> None:
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    module = importlib.import_module(path)
    if hasattr(module, "register"):
        module.register(app)
    else:
        raise RuntimeError(f"Модуль {path} не содержит функцию register(app).")
