"""Factory helpers to wire CardForge services into aiogram."""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..app import BotApp
from ..domain import PlayerProfile
from ..domain.cards import Card
from ..domain.exceptions import CooldownActive, NoCardsAvailable, PlayerBanned
from ..registry import MiniGame
from ..telegram.keyboards import card_drop_keyboard, welcome_keyboard
from .minigames import TelegramMiniGameContext


def build_router(app: BotApp, *, default_pack: str | None = None) -> Router:
    resolved_pack = ensure_catalog_ready(app, default_pack)
    ensure_mini_game_commands(app)

    router = Router()
    inventory = app.inventory_service
    players = app.player_service

    @router.message(Command("start"))
    async def handle_start(message: Message) -> None:
        await message.answer(
            render_help_message(resolved_pack),
            reply_markup=welcome_keyboard(resolved_pack),
        )

    @router.message(Command("help"))
    async def handle_help(message: Message) -> None:
        await message.answer(
            render_help_message(resolved_pack),
            reply_markup=welcome_keyboard(resolved_pack),
        )

    @router.message(Command("packs"))
    async def handle_packs(message: Message) -> None:
        pack_lines = [
            f"• {pack.pack_id}: {pack.name} ({len(pack.cards)} карт)"
            for pack in app.cards.catalog.iter_packs()
        ]
        await message.answer("\n".join(pack_lines) or "Доступных паков пока нет.")

    @router.message(Command("drop"))
    async def handle_drop(message: Message) -> None:
        user = message.from_user
        if not user:
            return
        pack_id = extract_pack_id(message.text, resolved_pack, app.cards.catalog.iter_packs())
        if not pack_id:
            await message.answer("Пак не найден. Используй /packs, чтобы узнать доступные пакеты.")
            return
        try:
            outcome = await inventory.drop_from_pack(user.id, pack_id, username=user.username)
        except CooldownActive as cooldown:
            await message.answer(f"Подожди ещё {cooldown.seconds_remaining} сек. до следующего дропа.")
            return
        except PlayerBanned:
            await message.answer("Вы заблокированы и не можете получать карты.")
            return
        except NoCardsAvailable:
            await message.answer("В этом паке закончились доступные карты.")
            return
        await message.answer(
            format_drop_message(outcome.cards, outcome.reward, outcome.duplicates),
            reply_markup=card_drop_keyboard(pack_id),
        )

    @router.callback_query(lambda c: c.data and c.data.startswith("cardforge:roll:"))
    async def handle_roll_again(callback: CallbackQuery) -> None:
        user = callback.from_user
        if not user or not callback.data:
            return
        pack_id = callback.data.split(":")[-1]
        try:
            outcome = await inventory.drop_from_pack(user.id, pack_id, username=user.username)
        except CooldownActive as cooldown:
            await callback.answer(f"Подожди {cooldown.seconds_remaining} сек.", show_alert=True)
            return
        except PlayerBanned:
            await callback.answer("Вы заблокированы.", show_alert=True)
            return
        await callback.message.edit_text(
            format_drop_message(outcome.cards, outcome.reward, outcome.duplicates),
            reply_markup=card_drop_keyboard(pack_id),
        )
        await callback.answer()

    @router.message(Command("profile"))
    async def handle_profile(message: Message) -> None:
        user = message.from_user
        if not user:
            return
        profile = await players.fetch(user.id)
        cooldown = await inventory.cooldown_remaining(user.id)
        await message.answer(format_profile_message(profile, cooldown))

    @router.message(Command("collection"))
    async def handle_collection(message: Message) -> None:
        user = message.from_user
        if not user:
            return
        profile = await players.fetch(user.id)
        await message.answer(
            format_collection_message(profile.inventory, app.cards.catalog.iter_cards())
        )

    @router.callback_query(lambda c: c.data == "cardforge:collection")
    async def handle_collection_callback(callback: CallbackQuery) -> None:
        user = callback.from_user
        if not user:
            return
        profile = await players.fetch(user.id)
        await callback.answer()
        await callback.message.answer(
            format_collection_message(profile.inventory, app.cards.catalog.iter_cards())
        )

    @router.callback_query(lambda c: c.data == "cardforge:help")
    async def handle_help_callback(callback: CallbackQuery) -> None:
        await callback.answer()
        await callback.message.answer(
            render_help_message(resolved_pack),
            reply_markup=welcome_keyboard(resolved_pack),
        )

    @router.message(Command("cooldown"))
    async def handle_cooldown(message: Message) -> None:
        user = message.from_user
        if not user:
            return
        remaining = await inventory.cooldown_remaining(user.id)
        if remaining > 0:
            await message.answer(f"До следующего дропа осталось {remaining} сек.")
        else:
            await message.answer("Кулдаун не активен — можно открывать пак!")

    @router.message(Command("games"))
    async def handle_games(message: Message) -> None:
        await message.answer(render_games_list(app))

    @router.callback_query(lambda c: c.data == "cardforge:games")
    async def handle_games_callback(callback: CallbackQuery) -> None:
        await callback.answer()
        await callback.message.answer(render_games_list(app))

    _register_mini_game_handlers(router, app)

    return router


def ensure_catalog_ready(app: BotApp, default_pack: str | None) -> str:
    packs = list(app.cards.catalog.iter_packs())
    if not packs:
        raise RuntimeError(
            "В каталоге нет паков. Используйте app.cards.pack(...) или load_catalog_from_json, чтобы зарегистрировать данные."
        )
    pack_ids = {pack.pack_id for pack in packs}
    if default_pack and default_pack not in pack_ids:
        raise RuntimeError(
            f"Пак '{default_pack}' не найден. Доступные паки: {', '.join(sorted(pack_ids))}."
        )
    for pack in packs:
        if not pack.cards:
            raise RuntimeError(f"Пак '{pack.pack_id}' не содержит карт.")
        for card_id in pack.cards:
            try:
                app.cards.catalog.get_card(card_id)
            except KeyError as exc:  # noqa: PERF203 - fail early
                raise RuntimeError(
                    f"Пак '{pack.pack_id}' ссылается на неизвестную карту '{card_id}'."
                ) from exc
    return default_pack or packs[0].pack_id


def ensure_mini_game_commands(app: BotApp) -> None:
    reserved = {"start", "help", "drop", "profile", "collection", "cooldown", "games"}
    seen: set[str] = set()

    def _check(command: str, game: MiniGame) -> None:
        cmd = command.lstrip("/").lower()
        if not cmd:
            raise RuntimeError(f"Мини-игра '{game.game_id}' содержит пустую команду.")
        if cmd in reserved:
            raise RuntimeError(f"Команда мини-игры '/{cmd}' конфликтует с системной командой.")
        if cmd in seen:
            raise RuntimeError(f"Команда '/{cmd}' используется несколькими мини-играми.")
        seen.add(cmd)

    for game in app.mini_games.all():
        if game.command:
            _check(game.command, game)
        for alias in game.aliases:
            _check(alias, game)


def render_games_list(app: BotApp) -> str:
    games = app.mini_games.all()
    if not games:
        return "Мини-игры пока недоступны."
    lines = ["🎮 Доступные мини-игры:"]
    for game in games:
        cmd = ""
        if game.command:
            cmd = f"/{game.command}"
            if game.aliases:
                alias_part = ", ".join(f"/{alias}" for alias in game.aliases)
                cmd = f"{cmd} ({alias_part})"
        lines.append(f"• {game.name}{' — ' + cmd if cmd else ''}")
        if game.description:
            lines.append(f"  {game.description}")
    lines.append("")
    lines.append("Запусти мини-игру командой или нажми на кнопку внизу.")
    return "\n".join(lines)


def render_help_message(default_pack: str | None) -> str:
    lines = [
        "Привет! Этот бот демонстрирует CardForge.",
        "",
        "Команды:",
        "• /drop — получить карту",
        "• /profile — посмотреть баланс и опыт",
        "• /collection — открыть коллекцию",
        "• /games — список мини-игр",
        "• /cooldown — узнать, когда доступен следующий дроп",
        "• /help — показать это сообщение",
    ]
    if default_pack:
        lines.append(f"• /drop {default_pack} — открыть пак {default_pack}")
    lines.append("")
    lines.append("Используй кнопки под сообщениями для быстрого доступа к действиям.")
    return "\n".join(lines)


def extract_pack_id(text: str | None, default_pack: str | None, packs: Iterable) -> str | None:
    if text and len(parts := text.strip().split()) > 1:
        return parts[1]
    if default_pack:
        return default_pack
    try:
        return next(iter(p.pack_id for p in packs))
    except StopIteration:
        return None


def format_drop_message(cards, reward, duplicates) -> str:
    lines = ["✨ Твои карты:"]
    for card in cards:
        lines.append(f"• {card.name} [{card.rarity.value}]")
    if reward.currencies:
        lines.append("")
        lines.append("💰 Награды:")
        for currency, amount in reward.currencies.items():
            lines.append(f"  {currency}: {amount}")
    if reward.experience:
        lines.append(f"📈 Опыт: {reward.experience}")
    if duplicates:
        lines.append("")
        lines.append("♻️ Дубликаты:")
        for card in duplicates:
            lines.append(f"  {card.name}")
    return "\n".join(lines)


def format_profile_message(profile: PlayerProfile, cooldown: int) -> str:
    lines = [f"👤 Профиль {profile.username or profile.user_id}", f"📈 Опыт: {profile.experience}"]
    if profile.wallet:
        lines.append("")
        lines.append("💰 Баланс:")
        for currency, amount in sorted(profile.wallet.items()):
            lines.append(f"  {currency}: {amount}")
    else:
        lines.append("")
        lines.append("💰 Баланс пуст.")

    lines.append("")
    lines.append("⏱️ Кулдаун: активен" if cooldown > 0 else "⏱️ Кулдаун отсутствует")
    if cooldown > 0:
        lines.append(f"   Осталось {cooldown} сек.")

    owned = sum(profile.inventory.values())
    lines.append("")
    lines.append(f"🗃️ Карточки: {owned}")
    return "\n".join(lines)


def format_collection_message(inventory: Mapping[str, int], cards: Iterable[Card]) -> str:
    catalog = {card.card_id: card for card in cards}
    if not inventory:
        return "Коллекция пуста. Получай карты командой /drop."

    lines = ["📚 Коллекция:"]
    for card_id, amount in sorted(inventory.items()):
        card = catalog.get(card_id)
        name = card.name if card else card_id
        rarity = f" [{card.rarity.value}]" if card else ""
        lines.append(f"• {name}{rarity}: {amount} шт.")
    return "\n".join(lines)


def _register_mini_game_handlers(router: Router, app: BotApp) -> None:
    def normalize_commands(game: MiniGame) -> list[str]:
        commands: list[str] = []
        if game.command:
            commands.append(game.command.lstrip("/"))
        commands.extend(alias.lstrip("/") for alias in game.aliases)
        return commands

    for game in app.mini_games.all():
        commands = normalize_commands(game)
        if not commands:
            continue

        async def handler(message: Message, *, _game: MiniGame = game) -> None:
            user = message.from_user
            if not user:
                return
            if await app.inventory_service.is_banned(user.id):
                await message.answer("Вы заблокированы и не можете использовать мини-игры.")
                return
            context = TelegramMiniGameContext(
                app,
                message,
                user_id=user.id,
                username=user.username,
            )
            await _game.handler(context)

        router.message.register(handler, Command(commands=commands))
