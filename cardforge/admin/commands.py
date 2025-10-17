"""Admin command wiring for aiogram."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..app import BotApp
from ..telegram.filters import AdminFilter


def build_admin_router(app: BotApp) -> Router:
    router = Router()
    router.message.filter(AdminFilter(app.config))
    service = app_admin_service(app)
    commands = app.config.admin.commands

    @router.message(Command(commands.ban))
    async def handle_ban(message: Message) -> None:
        user = message.text.split()
        if len(user) < 2:
            await message.answer(f"Использование: /{commands.ban} <user_id>")
            return
        target = int(user[1])
        await service.ban_user(target, reason=f"by {message.from_user.id}")
        await message.answer(f"Пользователь {target} заблокирован.")

    @router.message(Command(commands.unban))
    async def handle_unban(message: Message) -> None:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer(f"Использование: /{commands.unban} <user_id>")
            return
        target = int(parts[1])
        await service.unban_user(target)
        await message.answer(f"Пользователь {target} разблокирован.")

    @router.message(Command(commands.grant_card))
    async def handle_grant_card(message: Message) -> None:
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer(
                f"Использование: /{commands.grant_card} <user_id> <card_id> [кол-во]"
            )
            return
        target = int(parts[1])
        card_id = parts[2]
        quantity = int(parts[3]) if len(parts) > 3 else 1
        await service.grant_card(target, card_id, quantity)
        await message.answer(f"Выдано {quantity}x {card_id} пользователю {target}.")

    @router.message(Command(commands.grant_currency))
    async def handle_grant_currency(message: Message) -> None:
        parts = message.text.split()
        if len(parts) < 4:
            await message.answer(
                f"Использование: /{commands.grant_currency} <user_id> <currency> <amount>"
            )
            return
        target = int(parts[1])
        currency = parts[2]
        amount = int(parts[3])
        await service.grant_currency(target, currency, amount)
        await message.answer(f"Выдано {amount} {currency} пользователю {target}.")

    return router


def app_admin_service(app: BotApp):
    from .service import AdminService

    return AdminService(
        player_store=app.player_store,
        audit_store=app.audit_store,
        catalog=app.cards.catalog,
        currencies=app.currencies.registry,
        event_bus=app.event_bus,
    )
