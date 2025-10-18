"""Interactive studio for building CardForge prototypes."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt
from rich.table import Table

from ..loaders import validate_catalog_dict


@dataclass
class StudioCurrency:
    code: str
    name: str
    precision: int = 0
    description: str = ""

    def to_dict(self) -> dict:
        data = {"code": self.code, "name": self.name}
        if self.precision:
            data["precision"] = self.precision
        if self.description:
            data["description"] = self.description
        return data


@dataclass
class StudioCard:
    card_id: str
    name: str
    description: str
    rarity: str
    reward_currencies: Dict[str, int]
    reward_experience: int
    tags: List[str] = field(default_factory=list)
    max_copies: Optional[int] = None
    weight: Optional[float] = None
    image_url: Optional[str] = None
    image_path: Optional[str] = None
    image_caption: Optional[str] = None
    local_image_source: Optional[str] = None


@dataclass
class StudioPack:
    pack_id: str
    name: Optional[str]
    card_ids: List[str]
    allow_duplicates: bool = True
    max_per_roll: int = 1
    card_weights: Dict[str, float] = field(default_factory=dict)
    rarity_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class DropSettings:
    base_cooldown_seconds: int = 3600
    allow_duplicates: bool = True
    duplicate_penalty: float = 0.0
    max_cards_per_drop: int = 1
    rarity_weights: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = {
            "base_cooldown_seconds": self.base_cooldown_seconds,
            "allow_duplicates": self.allow_duplicates,
            "duplicate_penalty": self.duplicate_penalty,
            "max_cards_per_drop": self.max_cards_per_drop,
        }
        if self.rarity_weights:
            data["rarity_weights"] = self.rarity_weights
        return data


@dataclass
class AdminSettings:
    admin_ids: List[int] = field(default_factory=list)
    commands: Dict[str, str] = field(
        default_factory=lambda: {
            "ban": "ban",
            "unban": "unban",
            "grant_card": "grantcard",
            "grant_currency": "grantcurrency",
        }
    )

    def to_dict(self) -> dict:
        return {"admin_ids": self.admin_ids, "commands": self.commands}


@dataclass
class StudioState:
    currencies: Dict[str, StudioCurrency] = field(default_factory=dict)
    cards: Dict[str, StudioCard] = field(default_factory=dict)
    packs: Dict[str, StudioPack] = field(default_factory=dict)
    drop: DropSettings = field(default_factory=DropSettings)
    admin: AdminSettings = field(default_factory=AdminSettings)
    default_currencies: List[str] = field(default_factory=lambda: ["coins", "gems"])

    @classmethod
    def create_default(cls) -> "StudioState":
        state = cls()
        state.currencies = {
            "coins": StudioCurrency(code="coins", name="Coins"),
            "gems": StudioCurrency(code="gems", name="Gems"),
        }
        state.default_currencies = ["coins", "gems"]
        return state

    def to_catalog(self) -> dict:
        return {
            "currencies": [currency.to_dict() for currency in self.currencies.values()],
            "cards": [card_to_payload(card) for card in self.cards.values()],
            "packs": [pack_to_payload(pack) for pack in self.packs.values()],
        }

    def to_settings(self) -> dict:
        return {
            "drop": self.drop.to_dict(),
            "admin": self.admin.to_dict(),
            "default_currencies": self.default_currencies,
        }


def card_to_payload(card: StudioCard) -> dict:
    payload: Dict[str, object] = {
        "id": card.card_id,
        "name": card.name,
        "description": card.description,
        "rarity": card.rarity,
        "reward": {
            "currencies": {code: int(amount) for code, amount in card.reward_currencies.items()},
            "experience": int(card.reward_experience),
        },
    }
    if card.tags:
        payload["tags"] = card.tags
    if card.max_copies is not None:
        payload["maxCopies"] = card.max_copies
    if card.weight is not None:
        payload["weight"] = card.weight
    image: Dict[str, str] = {}
    if card.image_url:
        image["url"] = card.image_url
    if card.image_path:
        image["local"] = card.image_path
    if card.image_caption:
        image["caption"] = card.image_caption
    if image:
        payload["image"] = image
    return payload


def pack_to_payload(pack: StudioPack) -> dict:
    payload: Dict[str, object] = {
        "id": pack.pack_id,
        "cards": pack.card_ids,
        "allowDuplicates": pack.allow_duplicates,
        "maxPerRoll": pack.max_per_roll,
    }
    if pack.name:
        payload["name"] = pack.name
    if pack.card_weights:
        payload["cardWeights"] = pack.card_weights
    if pack.rarity_weights:
        payload["rarityWeights"] = pack.rarity_weights
    return payload


RARITY_OPTIONS = [
    ("common", "Обычная"),
    ("uncommon", "Необычная"),
    ("rare", "Редкая"),
    ("epic", "Эпическая"),
    ("legendary", "Легендарная"),
]


class StudioApp:
    def __init__(self, console: Console) -> None:
        self.console = console
        self.state = StudioState.create_default()

    # ---------------------------------------------------------------- main UI
    def run(self) -> None:
        while True:
            self.console.print("[bold]CardForge Studio[/bold]")
            self.console.print(
                "1) Валюты  2) Карты  3) Паки  4) Дроп  5) Админы  6) Валидация  7) Сохранить  8) Загрузить  0) Выход"
            )
            choice = Prompt.ask("Выбор", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8"], default="1")
            if choice == "0":
                return
            if choice == "1":
                self.manage_currencies()
            elif choice == "2":
                self.manage_cards()
            elif choice == "3":
                self.manage_packs()
            elif choice == "4":
                self.configure_drop()
            elif choice == "5":
                self.configure_admin()
            elif choice == "6":
                self.validate()
            elif choice == "7":
                self.save_project()
            elif choice == "8":
                self.load_catalog()

    def pause(self) -> None:
        input("Нажмите Enter для продолжения…")

    # ------------------------------------------------------------- currencies
    def manage_currencies(self) -> None:
        while True:
            self.console.print(
                "[bold]Валюты[/bold]\n1) Список  2) Добавить  3) Изменить  4) Удалить  5) По умолчанию  0) Назад"
            )
            choice = Prompt.ask("Выбор", choices=["0", "1", "2", "3", "4", "5"], default="1")
            if choice == "0":
                return
            if choice == "1":
                self.list_currencies()
            elif choice == "2":
                self.add_currency()
            elif choice == "3":
                self.edit_currency()
            elif choice == "4":
                self.remove_currency()
            elif choice == "5":
                self.set_default_currencies()

    def list_currencies(self) -> None:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Code")
        table.add_column("Name")
        table.add_column("Precision")
        table.add_column("Description")
        for currency in self.state.currencies.values():
            table.add_row(currency.code, currency.name, str(currency.precision), currency.description or "")
        self.console.print(table)
        self.pause()

    def add_currency(self) -> None:
        code = Prompt.ask("Код валюты").strip().lower()
        if not code:
            return
        if code in self.state.currencies:
            self.console.print("Валюта уже существует.", style="red")
            self.pause()
            return
        name = Prompt.ask("Название", default=code.title())
        precision = IntPrompt.ask("Точность (количество знаков)", default=0, show_default=True)
        description = Prompt.ask("Описание (опционально)", default="")
        self.state.currencies[code] = StudioCurrency(code=code, name=name, precision=precision, description=description)
        if code not in self.state.default_currencies:
            self.state.default_currencies.append(code)

    def edit_currency(self) -> None:
        code = Prompt.ask("Код валюты").strip().lower()
        currency = self.state.currencies.get(code)
        if not currency:
            self.console.print("Валюта не найдена.", style="red")
            self.pause()
            return
        currency.name = Prompt.ask("Название", default=currency.name)
        currency.precision = IntPrompt.ask(
            "Точность (количество знаков)",
            default=currency.precision,
            show_default=True,
        )
        currency.description = Prompt.ask("Описание (опционально)", default=currency.description)

    def remove_currency(self) -> None:
        code = Prompt.ask("Код валюты").strip().lower()
        if code == "coins":
            self.console.print("Валюту 'coins' удалять нельзя.", style="red")
            self.pause()
            return
        currency = self.state.currencies.pop(code, None)
        if not currency:
            self.console.print("Валюта не найдена.", style="red")
            self.pause()
            return
        if code in self.state.default_currencies:
            self.state.default_currencies.remove(code)
        for card in self.state.cards.values():
            card.reward_currencies.pop(code, None)

    def set_default_currencies(self) -> None:
        value = Prompt.ask(
            "Введите коды валют по умолчанию через запятую",
            default=",".join(self.state.default_currencies),
        )
        codes = [item.strip().lower() for item in value.split(",") if item.strip()]
        filtered = [code for code in codes if code in self.state.currencies]
        if "coins" not in filtered:
            filtered.insert(0, "coins")
        self.state.default_currencies = filtered

    # ------------------------------------------------------------------- cards
    def manage_cards(self) -> None:
        while True:
            self.console.print("[bold]Карты[/bold]\n1) Список  2) Добавить  3) Изменить  4) Удалить  0) Назад")
            choice = Prompt.ask("Выбор", choices=["0", "1", "2", "3", "4"], default="1")
            if choice == "0":
                return
            if choice == "1":
                self.list_cards()
            elif choice == "2":
                self.add_card()
            elif choice == "3":
                self.edit_card()
            elif choice == "4":
                self.remove_card()

    def list_cards(self) -> None:
        table = Table(show_header=True, header_style="bold")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Rarity")
        table.add_column("Max")
        table.add_column("Weight")
        table.add_column("Currencies")
        for card in self.state.cards.values():
            max_copies = "-" if card.max_copies is None else str(card.max_copies)
            weight = "-" if card.weight is None else f"{card.weight:.2f}"
            currencies = ", ".join(f"{code}:{amount}" for code, amount in card.reward_currencies.items())
            table.add_row(card.card_id, card.name, card.rarity, max_copies, weight, currencies)
        self.console.print(table)
        self.pause()

    def add_card(self) -> None:
        card_id = Prompt.ask("ID карты").strip()
        if not card_id:
            return
        if card_id in self.state.cards:
            self.console.print("Карта уже существует.", style="red")
            self.pause()
            return
        name = Prompt.ask("Название", default=card_id.title())
        description = Prompt.ask("Описание", default="")
        rarity = self.select_rarity()
        max_copies = self.prompt_optional_int("Максимум копий (пусто = без лимита)")
        weight = self.prompt_optional_float("Вес выпадения (пусто = 1.0)")
        experience = IntPrompt.ask("Опыт за карту", default=0, show_default=True)
        reward_currencies: Dict[str, int] = {}
        for code in self.state.currencies:
            amount = IntPrompt.ask(f"Сколько {code} выдавать (целое число)", default=1 if code == "coins" else 0)
            reward_currencies[code] = amount
        tags_value = Prompt.ask("Теги (через запятую, опционально)", default="")
        tags = [item.strip() for item in tags_value.split(",") if item.strip()]
        image_url: Optional[str] = None
        image_path: Optional[str] = None
        image_caption: Optional[str] = None
        local_source: Optional[str] = None
        image_choice = Prompt.ask("Источник изображения (none/url/local)", choices=["none", "url", "local"], default="none")
        if image_choice == "url":
            image_url = Prompt.ask("Введите URL изображения").strip()
            image_caption = Prompt.ask("Подпись (опционально)", default="").strip() or None
        elif image_choice == "local":
            source_path = Prompt.ask("Путь к локальному файлу").strip()
            source = Path(source_path).expanduser()
            if not source.exists():
                self.console.print("Файл не найден.", style="red")
                self.pause()
                return
            target = Prompt.ask(
                "Путь назначения внутри проекта (например, assets/warrior.png)",
                default=f"assets/{source.name}",
            ).strip()
            image_path = target
            local_source = str(source)
            image_caption = Prompt.ask("Подпись (опционально)", default="").strip() or None
        card = StudioCard(
            card_id=card_id,
            name=name,
            description=description,
            rarity=rarity,
            reward_currencies=reward_currencies,
            reward_experience=experience,
            tags=tags,
            max_copies=max_copies,
            weight=weight,
            image_url=image_url,
            image_path=image_path,
            image_caption=image_caption,
            local_image_source=local_source,
        )
        self.state.cards[card_id] = card

    def edit_card(self) -> None:
        card_id = Prompt.ask("ID карты").strip()
        card = self.state.cards.get(card_id)
        if not card:
            self.console.print("Карта не найдена.", style="red")
            self.pause()
            return
        card.name = Prompt.ask("Название", default=card.name)
        card.description = Prompt.ask("Описание", default=card.description)
        card.rarity = self.select_rarity(default=card.rarity)
        card.max_copies = self.prompt_optional_int(
            "Максимум копий (пусто = без лимита)",
            default="" if card.max_copies is None else str(card.max_copies),
        )
        card.weight = self.prompt_optional_float(
            "Вес выпадения (пусто = 1.0)",
            default="" if card.weight is None else str(card.weight),
        )
        card.reward_experience = IntPrompt.ask("Опыт за карту", default=card.reward_experience, show_default=True)
        for code in list(self.state.currencies.keys()):
            default = card.reward_currencies.get(code, 0)
            amount = IntPrompt.ask(f"Сколько {code} выдавать (целое число)", default=default, show_default=True)
            card.reward_currencies[code] = amount
        tags_value = Prompt.ask("Теги (через запятую, опционально)", default=",".join(card.tags))
        card.tags = [item.strip() for item in tags_value.split(",") if item.strip()]
        image_choice = Prompt.ask(
            "Источник изображения (keep/none/url/local)",
            choices=["keep", "none", "url", "local"],
            default="keep",
        )
        if image_choice == "none":
            card.image_url = None
            card.image_path = None
            card.image_caption = None
            card.local_image_source = None
        elif image_choice == "url":
            card.image_url = Prompt.ask("Введите URL изображения", default=card.image_url or "").strip() or None
            card.image_caption = Prompt.ask("Подпись (опционально)", default=card.image_caption or "").strip() or None
            card.image_path = None
            card.local_image_source = None
        elif image_choice == "local":
            source_path = Prompt.ask("Путь к локальному файлу").strip()
            source = Path(source_path).expanduser()
            if not source.exists():
                self.console.print("Файл не найден.", style="red")
                self.pause()
                return
            target = Prompt.ask(
                "Путь назначения внутри проекта (например, assets/warrior.png)",
                default=card.image_path or f"assets/{source.name}",
            ).strip()
            card.image_url = None
            card.image_path = target
            card.image_caption = Prompt.ask("Подпись (опционально)", default=card.image_caption or "").strip() or None
            card.local_image_source = str(source)

    def remove_card(self) -> None:
        card_id = Prompt.ask("ID карты").strip()
        if card_id not in self.state.cards:
            self.console.print("Карта не найдена.", style="red")
            self.pause()
            return
        self.state.cards.pop(card_id)
        for pack in self.state.packs.values():
            if card_id in pack.card_ids:
                pack.card_ids = [cid for cid in pack.card_ids if cid != card_id]
                pack.card_weights.pop(card_id, None)

    # ------------------------------------------------------------------- packs
    def manage_packs(self) -> None:
        while True:
            self.console.print("[bold]Паки[/bold]\n1) Список  2) Добавить  3) Изменить  4) Удалить  0) Назад")
            choice = Prompt.ask("Выбор", choices=["0", "1", "2", "3", "4"], default="1")
            if choice == "0":
                return
            if choice == "1":
                self.list_packs()
            elif choice == "2":
                self.add_pack()
            elif choice == "3":
                self.edit_pack()
            elif choice == "4":
                self.remove_pack()

    def list_packs(self) -> None:
        table = Table(show_header=True, header_style="bold")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Cards")
        table.add_column("Duplicates")
        table.add_column("Per roll")
        for pack in self.state.packs.values():
            table.add_row(
                pack.pack_id,
                pack.name or "",
                ", ".join(pack.card_ids),
                "да" if pack.allow_duplicates else "нет",
                str(pack.max_per_roll),
            )
        self.console.print(table)
        self.pause()

    def add_pack(self) -> None:
        pack_id = Prompt.ask("ID пака").strip()
        if not pack_id:
            return
        if pack_id in self.state.packs:
            self.console.print("Пак уже существует.", style="red")
            self.pause()
            return
        name = Prompt.ask("Название (опционально)", default="")
        card_ids = self.prompt_card_list()
        if not card_ids:
            return
        allow_duplicates = Confirm.ask("Разрешить дубликаты?", default=True)
        max_per_roll = IntPrompt.ask("Сколько карт за дроп", default=1, show_default=True)
        card_weights: Dict[str, float] = {}
        if Confirm.ask("Настроить веса для отдельных карт?", default=False):
            for card_id in card_ids:
                weight = self.prompt_optional_float(f"Вес для {card_id}")
                if weight is not None:
                    card_weights[card_id] = weight
        rarity_weights: Dict[str, float] = {}
        if Confirm.ask("Настроить веса по редкостям?", default=False):
            for code, label in RARITY_OPTIONS:
                weight = self.prompt_optional_float(f"Вес для {label}")
                if weight is not None:
                    rarity_weights[code] = weight
        self.state.packs[pack_id] = StudioPack(
            pack_id=pack_id,
            name=name or None,
            card_ids=card_ids,
            allow_duplicates=allow_duplicates,
            max_per_roll=max_per_roll,
            card_weights=card_weights,
            rarity_weights=rarity_weights,
        )

    def edit_pack(self) -> None:
        pack_id = Prompt.ask("ID пака").strip()
        pack = self.state.packs.get(pack_id)
        if not pack:
            self.console.print("Пак не найден.", style="red")
            self.pause()
            return
        pack.name = Prompt.ask("Название (опционально)", default=pack.name or "")
        cards_value = ",".join(pack.card_ids)
        new_cards = self.prompt_card_list(default=cards_value)
        if new_cards:
            pack.card_ids = new_cards
        pack.allow_duplicates = Confirm.ask("Разрешить дубликаты?", default=pack.allow_duplicates)
        pack.max_per_roll = IntPrompt.ask(
            "Сколько карт за дроп",
            default=pack.max_per_roll,
            show_default=True,
        )
        if Confirm.ask("Настроить веса для отдельных карт?", default=bool(pack.card_weights)):
            card_weights: Dict[str, float] = {}
            for card_id in pack.card_ids:
                default_weight = pack.card_weights.get(card_id)
                weight = self.prompt_optional_float(
                    f"Вес для {card_id}",
                    default="" if default_weight is None else str(default_weight),
                )
                if weight is not None:
                    card_weights[card_id] = weight
            pack.card_weights = card_weights
        else:
            pack.card_weights = {}
        if Confirm.ask("Настроить веса по редкостям?", default=bool(pack.rarity_weights)):
            rarity_weights: Dict[str, float] = {}
            for code, label in RARITY_OPTIONS:
                default_weight = pack.rarity_weights.get(code)
                weight = self.prompt_optional_float(
                    f"Вес для {label}",
                    default="" if default_weight is None else str(default_weight),
                )
                if weight is not None:
                    rarity_weights[code] = weight
            pack.rarity_weights = rarity_weights
        else:
            pack.rarity_weights = {}

    def remove_pack(self) -> None:
        pack_id = Prompt.ask("ID пака").strip()
        if pack_id not in self.state.packs:
            self.console.print("Пак не найден.", style="red")
            self.pause()
            return
        self.state.packs.pop(pack_id)

    # --------------------------------------------------------------- drop/admin
    def configure_drop(self) -> None:
        self.console.print("[bold]Настройки дропа[/bold]")
        self.state.drop.base_cooldown_seconds = IntPrompt.ask(
            "Базовый кулдаун (сек)",
            default=self.state.drop.base_cooldown_seconds,
            show_default=True,
        )
        self.state.drop.allow_duplicates = Confirm.ask(
            "Разрешить дубликаты?",
            default=self.state.drop.allow_duplicates,
        )
        self.state.drop.duplicate_penalty = FloatPrompt.ask(
            "Пенальти за дубликат (0-1)",
            default=self.state.drop.duplicate_penalty,
            show_default=True,
        )
        self.state.drop.max_cards_per_drop = IntPrompt.ask(
            "Макс. карт за дроп",
            default=self.state.drop.max_cards_per_drop,
            show_default=True,
        )
        if Confirm.ask("Настроить веса редкостей?", default=bool(self.state.drop.rarity_weights)):
            weights: Dict[str, float] = {}
            for code, label in RARITY_OPTIONS:
                default_weight = self.state.drop.rarity_weights.get(code)
                weight = self.prompt_optional_float(
                    f"Вес для {label}",
                    default="" if default_weight is None else str(default_weight),
                )
                if weight is not None:
                    weights[code] = weight
            self.state.drop.rarity_weights = weights
        else:
            self.state.drop.rarity_weights = {}

    def configure_admin(self) -> None:
        self.console.print("[bold]Администрирование[/bold]")
        ids_value = Prompt.ask(
            "ID админов через запятую (опционально)",
            default=",".join(str(i) for i in self.state.admin.admin_ids),
        )
        admin_ids: List[int] = []
        for chunk in ids_value.split(","):
            chunk = chunk.strip()
            if chunk:
                try:
                    admin_ids.append(int(chunk))
                except ValueError:
                    continue
        self.state.admin.admin_ids = admin_ids
        for key, label in [
            ("ban", "Команда бана"),
            ("unban", "Команда разбана"),
            ("grant_card", "Команда выдачи карты"),
            ("grant_currency", "Команда выдачи валюты"),
        ]:
            self.state.admin.commands[key] = Prompt.ask(
                label,
                default=self.state.admin.commands.get(key, key),
            )

    # --------------------------------------------------------------- validation
    def validate(self) -> None:
        catalog_dict = self.state.to_catalog()
        errors = validate_catalog_dict(catalog_dict)
        if errors:
            self.console.print("Найдены ошибки:", style="red")
            for item in errors:
                self.console.print(f"- {item}", style="red")
        else:
            self.console.print("Ошибок не обнаружено.", style="green")
        self.pause()

    # -------------------------------------------------------------------- save
    def save_project(self) -> None:
        target_value = Prompt.ask("Каталог проекта", default="cardforge_project").strip()
        if not target_value:
            return
        target_dir = Path(target_value).expanduser()
        if target_dir.exists() and any(target_dir.iterdir()):
            if not Confirm.ask("Директория не пуста. Перезаписать?", default=False):
                return
        target_dir.mkdir(parents=True, exist_ok=True)
        catalog = self.state.to_catalog()
        errors = validate_catalog_dict(catalog)
        if errors:
            self.console.print("Каталог содержит ошибки:", style="red")
            for item in errors:
                self.console.print(f"- {item}", style="red")
            self.pause()
            return
        catalog_dir = target_dir / "catalog"
        catalog_dir.mkdir(parents=True, exist_ok=True)
        (catalog_dir / "cards.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

        settings_path = target_dir / "settings.json"
        settings_path.write_text(json.dumps(self.state.to_settings(), ensure_ascii=False, indent=2), encoding="utf-8")

        self.copy_assets(target_dir)
        self.write_main_stub(target_dir)
        (target_dir / ".env.example").write_text("CARDFORGE_BOT_TOKEN=\n", encoding="utf-8")
        self.console.print(f"Проект сохранён в {target_dir.resolve()}", style="green")
        self.pause()

    def copy_assets(self, target_dir: Path) -> None:
        for card in self.state.cards.values():
            if card.image_path and card.local_image_source:
                destination = target_dir / card.image_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(card.local_image_source, destination)
                except Exception:
                    self.console.print(f"Не удалось скопировать {card.local_image_source}", style="red")

    def write_main_stub(self, target_dir: Path) -> None:
        main_path = target_dir / "main.py"
        main_path.write_text(
            """import asyncio
import json
import os
from pathlib import Path

from aiogram import Bot, Dispatcher

from cardforge import BotApp
from cardforge.config import AdminCommandConfig, AdminConfig, CardForgeConfig, DropConfig
from cardforge.loaders import load_catalog_from_json
from cardforge.telegram import build_router
from cardforge.admin import build_admin_router


def create_app() -> BotApp:
    project_dir = Path(__file__).parent
    settings = json.loads((project_dir / "settings.json").read_text(encoding="utf-8"))
    drop_cfg = DropConfig(**settings["drop"])
    admin_cfg = AdminConfig(
        admin_ids=set(settings["admin"]["admin_ids"]),
        commands=AdminCommandConfig(**settings["admin"]["commands"]),
    )
    config = CardForgeConfig(
        bot_token=os.getenv("CARDFORGE_BOT_TOKEN", ""),
        drop=drop_cfg,
        admin=admin_cfg,
        default_currencies=settings["default_currencies"],
    )
    app = BotApp(config)
    load_catalog_from_json(app, project_dir / "catalog" / "cards.json")
    return app


async def main() -> None:
    app = create_app()
    bot = Bot(app.config.bot_token)
    dp = Dispatcher()
    dp.include_router(build_router(app))
    dp.include_router(build_admin_router(app))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
""",
            encoding="utf-8",
        )

    # -------------------------------------------------------------------- load
    def load_catalog(self) -> None:
        path_value = Prompt.ask("Путь к catalog/cards.json").strip()
        if not path_value:
            return
        catalog_path = Path(path_value).expanduser()
        if not catalog_path.exists():
            self.console.print("Файл не найден.", style="red")
            self.pause()
            return
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        errors = validate_catalog_dict(data)
        if errors:
            self.console.print("Каталог содержит ошибки:", style="red")
            for item in errors:
                self.console.print(f"- {item}", style="red")
            self.pause()
            return
        new_state = StudioState.create_default()
        new_state.currencies = {}
        for entry in data.get("currencies", []):
            currency = StudioCurrency(
                code=entry["code"],
                name=entry.get("name", entry["code"]),
                precision=int(entry.get("precision", 0)),
                description=entry.get("description", ""),
            )
            new_state.currencies[currency.code] = currency
        new_state.cards = {}
        for entry in data.get("cards", []):
            reward = entry.get("reward", {})
            image = entry.get("image", {})
            card = StudioCard(
                card_id=entry["id"],
                name=entry.get("name", entry["id"]),
                description=entry.get("description", ""),
                rarity=entry.get("rarity", "common"),
                reward_currencies={code: int(amount) for code, amount in reward.get("currencies", {}).items()},
                reward_experience=int(reward.get("experience", 0)),
                tags=[tag for tag in entry.get("tags", []) if isinstance(tag, str)],
                max_copies=entry.get("maxCopies"),
                weight=entry.get("weight"),
                image_url=image.get("url"),
                image_path=image.get("local"),
                image_caption=image.get("caption"),
            )
            new_state.cards[card.card_id] = card
        new_state.packs = {}
        for entry in data.get("packs", []):
            pack = StudioPack(
                pack_id=entry["id"],
                name=entry.get("name"),
                card_ids=[cid for cid in entry.get("cards", []) if cid in new_state.cards],
                allow_duplicates=entry.get("allowDuplicates", True),
                max_per_roll=int(entry.get("maxPerRoll", 1)),
                card_weights={k: float(v) for k, v in entry.get("cardWeights", {}).items()},
                rarity_weights={k: float(v) for k, v in entry.get("rarityWeights", {}).items()},
            )
            new_state.packs[pack.pack_id] = pack
        settings_path = catalog_path.parent.parent / "settings.json"
        if settings_path.exists():
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            drop = settings.get("drop", {})
            new_state.drop = DropSettings(
                base_cooldown_seconds=int(drop.get("base_cooldown_seconds", 3600)),
                allow_duplicates=bool(drop.get("allow_duplicates", True)),
                duplicate_penalty=float(drop.get("duplicate_penalty", 0.0)),
                max_cards_per_drop=int(drop.get("max_cards_per_drop", 1)),
                rarity_weights={k: float(v) for k, v in drop.get("rarity_weights", {}).items()},
            )
            admin = settings.get("admin", {})
            commands = admin.get("commands", {})
            new_state.admin = AdminSettings(
                admin_ids=[int(value) for value in admin.get("admin_ids", [])],
                commands={
                    "ban": commands.get("ban", "ban"),
                    "unban": commands.get("unban", "unban"),
                    "grant_card": commands.get("grant_card", "grantcard"),
                    "grant_currency": commands.get("grant_currency", "grantcurrency"),
                },
            )
            new_state.default_currencies = [
                code for code in settings.get("default_currencies", []) if code in new_state.currencies
            ] or ["coins"]
        else:
            new_state.default_currencies = list(new_state.currencies.keys())
        self.state = new_state
        self.console.print("Каталог загружен.", style="green")
        self.pause()

    # ----------------------------------------------------------------- helpers
    def select_rarity(self, default: Optional[str] = None) -> str:
        options = {str(index): code for index, (code, _) in enumerate(RARITY_OPTIONS, start=1)}
        labels = ", ".join(f"{idx}) {label}" for idx, (_, label) in enumerate(RARITY_OPTIONS, start=1))
        self.console.print(f"Раритет: {labels}")
        default_choice = next((key for key, code in options.items() if code == default), "1")
        choice = Prompt.ask("Выбор редкости", choices=list(options.keys()), default=default_choice)
        return options[choice]

    def prompt_optional_int(self, message: str, default: str = "") -> Optional[int]:
        value = Prompt.ask(message, default=default).strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            self.console.print("Некорректное число, игнорируется.", style="yellow")
            return None

    def prompt_optional_float(self, message: str, default: str = "") -> Optional[float]:
        value = Prompt.ask(message, default=default).strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            self.console.print("Некорректное число, игнорируется.", style="yellow")
            return None

    def prompt_card_list(self, default: str = "") -> List[str]:
        if not self.state.cards:
            self.console.print("Сначала добавьте карты.", style="yellow")
            self.pause()
            return []
        value = Prompt.ask("ID карт через запятую", default=default).strip()
        ids = [item.strip() for item in value.split(",") if item.strip()]
        valid = [card_id for card_id in ids if card_id in self.state.cards]
        if not valid:
            self.console.print("Необходимо указать существующие карты.", style="red")
            self.pause()
        return valid


def run_studio() -> None:
    console = Console()
    StudioApp(console).run()


__all__ = ["run_studio"]
